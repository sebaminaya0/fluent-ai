#!/usr/bin/env python3
"""
Hilo 1 - Continuous Audio Capture Thread with VAD and Circular Buffer

This module implements the first thread in the audio processing pipeline:
• Circular buffer of 1 second
• Voice Activity Detection (VAD) triggers recording after 200ms of voice
• Records until 400ms of silence is detected
• Pushes WAV data to ASR queue
• Ensures maximum 50ms blocking to prevent audio loss

Features:
- Real-time audio capture with minimal latency
- WebRTC VAD for voice activity detection
- Circular buffer implementation for continuous audio
- Non-blocking queue operations
- Automatic gain control and audio normalization
- Configurable VAD parameters and thresholds
"""

import io
import logging
import queue
import threading
import time
import wave
from collections import deque
from typing import Any

import numpy as np
import sounddevice as sd
import webrtcvad

from fluentai.database_logger import db_logger, get_device_name

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircularAudioBuffer:
    """Circular buffer for continuous audio capture with 1-second capacity."""

    def __init__(self, sample_rate: int = 16000, buffer_duration: float = 1.0):
        """
        Initialize circular buffer.
        
        Args:
            sample_rate: Audio sample rate in Hz
            buffer_duration: Buffer duration in seconds
        """
        self.sample_rate = sample_rate
        self.buffer_duration = buffer_duration
        self.buffer_size = int(sample_rate * buffer_duration)

        # Use deque for efficient circular buffer operations
        self.buffer = deque(maxlen=self.buffer_size)
        self.timestamps = deque(maxlen=self.buffer_size)
        self.lock = threading.Lock()

        logger.info(f"Circular buffer initialized: {buffer_duration}s @ {sample_rate}Hz ({self.buffer_size} samples)")

    def add_samples(self, samples: np.ndarray, timestamp: float):
        """Add audio samples to the circular buffer."""
        with self.lock:
            for sample in samples:
                self.buffer.append(sample)
                self.timestamps.append(timestamp)

    def get_samples(self, num_samples: int) -> tuple[np.ndarray, list]:
        """Get the most recent samples from the buffer."""
        with self.lock:
            if len(self.buffer) < num_samples:
                # Return all available samples
                samples = np.array(list(self.buffer))
                timestamps = list(self.timestamps)
            else:
                # Return last num_samples
                samples = np.array(list(self.buffer)[-num_samples:])
                timestamps = list(self.timestamps)[-num_samples:]

            return samples, timestamps

    def get_duration_samples(self, duration: float) -> tuple[np.ndarray, list]:
        """Get samples for a specific duration from the end of the buffer."""
        num_samples = int(self.sample_rate * duration)
        return self.get_samples(num_samples)

    def get_all_samples(self) -> tuple[np.ndarray, list]:
        """Get all samples from the buffer."""
        with self.lock:
            return np.array(list(self.buffer)), list(self.timestamps)

    def clear(self):
        """Clear the buffer."""
        with self.lock:
            self.buffer.clear()
            self.timestamps.clear()


class VADProcessor:
    """Voice Activity Detection processor using WebRTC VAD."""

    def __init__(self,
                 sample_rate: int = 16000,
                 frame_duration: int = 30,  # ms
                 aggressiveness: int = 2,
                 voice_threshold_ms: int = 200,
                 silence_threshold_ms: int = 400):
        """
        Initialize VAD processor.
        
        Args:
            sample_rate: Audio sample rate (8000, 16000, 32000, or 48000)
            frame_duration: Frame duration in ms (10, 20, or 30)
            aggressiveness: VAD aggressiveness (0-3)
            voice_threshold_ms: Minimum voice duration to start recording
            silence_threshold_ms: Minimum silence duration to stop recording
        """
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration
        self.aggressiveness = aggressiveness
        self.voice_threshold_ms = voice_threshold_ms
        self.silence_threshold_ms = silence_threshold_ms

        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad(aggressiveness)

        # Calculate frame size in samples
        self.frame_size = int(sample_rate * frame_duration / 1000)

        # State tracking
        self.consecutive_voice_frames = 0
        self.consecutive_silence_frames = 0
        self.is_recording = False
        self.recording_start_time = None

        # Calculate frames needed for thresholds
        self.voice_frames_threshold = int(voice_threshold_ms / frame_duration)
        self.silence_frames_threshold = int(silence_threshold_ms / frame_duration)

        logger.info(f"VAD initialized: {sample_rate}Hz, {frame_duration}ms frames, aggressiveness={aggressiveness}")
        logger.info(f"Voice threshold: {voice_threshold_ms}ms ({self.voice_frames_threshold} frames)")
        logger.info(f"Silence threshold: {silence_threshold_ms}ms ({self.silence_frames_threshold} frames)")

    def process_frame(self, frame: np.ndarray) -> dict[str, Any]:
        """
        Process a single audio frame for VAD.
        
        Args:
            frame: Audio frame as numpy array (int16)
            
        Returns:
            Dictionary with VAD results and state changes
        """
        if len(frame) != self.frame_size:
            logger.warning(f"Frame size mismatch: expected {self.frame_size}, got {len(frame)}")
            return {"error": "frame_size_mismatch"}

        # Convert to bytes for WebRTC VAD
        frame_bytes = frame.astype(np.int16).tobytes()

        # Detect voice activity
        is_voice = self.vad.is_speech(frame_bytes, self.sample_rate)

        result = {
            "is_voice": is_voice,
            "is_recording": self.is_recording,
            "should_start_recording": False,
            "should_stop_recording": False,
            "consecutive_voice_frames": self.consecutive_voice_frames,
            "consecutive_silence_frames": self.consecutive_silence_frames,
            "timestamp": time.time()
        }

        if is_voice:
            self.consecutive_voice_frames += 1
            self.consecutive_silence_frames = 0

            # Check if we should start recording
            if not self.is_recording and self.consecutive_voice_frames >= self.voice_frames_threshold:
                self.is_recording = True
                self.recording_start_time = time.time()
                result["should_start_recording"] = True
                logger.info(f"Started recording after {self.consecutive_voice_frames} voice frames")

        else:  # Silence
            self.consecutive_silence_frames += 1
            self.consecutive_voice_frames = 0

            # Check if we should stop recording
            if self.is_recording and self.consecutive_silence_frames >= self.silence_frames_threshold:
                self.is_recording = False
                recording_duration = time.time() - self.recording_start_time if self.recording_start_time else 0
                result["should_stop_recording"] = True
                result["recording_duration"] = recording_duration
                logger.info(f"Stopped recording after {self.consecutive_silence_frames} silence frames (duration: {recording_duration:.2f}s)")

        return result

    def reset_state(self):
        """Reset VAD state."""
        self.consecutive_voice_frames = 0
        self.consecutive_silence_frames = 0
        self.is_recording = False
        self.recording_start_time = None
        logger.info("VAD state reset")


class AudioCaptureThread:
    """
    Main audio capture thread implementing Hilo 1 functionality.
    
    This thread:
    1. Continuously captures audio into a circular buffer
    2. Uses VAD to detect voice activity
    3. Starts recording after 200ms of voice
    4. Stops recording after 400ms of silence
    5. Pushes complete audio segments to ASR queue
    6. Ensures max 50ms blocking to prevent audio loss
    """

    def __init__(self,
                 asr_queue: queue.Queue,
                 sample_rate: int = 16000,
                 channels: int = 1,
                 device: int | None = None,
                 chunk_size: int = 480,  # 30ms at 16kHz
                 vad_aggressiveness: int = 2,
                 voice_threshold_ms: int = 200,
                 silence_threshold_ms: int = 400,
                 buffer_duration: float = 1.0,
                 max_blocking_ms: int = 50):
        """
        Initialize audio capture thread.
        
        Args:
            asr_queue: Queue to send captured audio segments for ASR
            sample_rate: Audio sample rate
            channels: Number of audio channels
            device: Audio device ID (None for default)
            chunk_size: Audio chunk size in samples
            vad_aggressiveness: VAD aggressiveness level (0-3)
            voice_threshold_ms: Voice detection threshold in ms
            silence_threshold_ms: Silence detection threshold in ms
            buffer_duration: Circular buffer duration in seconds
            max_blocking_ms: Maximum blocking time in ms
        """
        self.asr_queue = asr_queue
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.chunk_size = chunk_size
        self.max_blocking_ms = max_blocking_ms

        # Initialize circular buffer
        self.buffer = CircularAudioBuffer(sample_rate, buffer_duration)

        # Initialize VAD processor
        self.vad = VADProcessor(
            sample_rate=sample_rate,
            frame_duration=30,  # 30ms frames
            aggressiveness=vad_aggressiveness,
            voice_threshold_ms=voice_threshold_ms,
            silence_threshold_ms=silence_threshold_ms
        )

        # Recording state
        self.current_recording = None
        self.recording_start_time = None

        # Thread control
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        
        # Database logging
        self.session_id = None
        self.input_channel = get_device_name(device) if device is not None else "Default"

        # Statistics
        self.stats = {
            "total_frames": 0,
            "voice_frames": 0,
            "recordings_created": 0,
            "queue_timeouts": 0,
            "processing_errors": 0
        }

        logger.info(f"AudioCaptureThread initialized: {sample_rate}Hz, {channels}ch, chunk_size={chunk_size}")

    def set_session_id(self, session_id: str):
        """Set the session ID for database logging."""
        self.session_id = session_id
        logger.info(f"Session ID set to: {session_id}")

    def _create_wav_bytes(self, audio_data: np.ndarray) -> bytes:
        """Create WAV file bytes from audio data."""
        try:
            # Create BytesIO buffer
            wav_buffer = io.BytesIO()

            # Write WAV file
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data.astype(np.int16).tobytes())

            # Get bytes
            wav_bytes = wav_buffer.getvalue()
            wav_buffer.close()

            return wav_bytes

        except Exception as e:
            logger.error(f"Error creating WAV bytes: {e}")
            return b""

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Audio callback function for sounddevice."""
        if status:
            logger.warning(f"Audio callback status: {status}")

        try:
            # Convert to int16 and flatten if multichannel
            if self.channels == 1:
                audio_data = (indata[:, 0] * 32767).astype(np.int16)
            else:
                audio_data = (indata.flatten() * 32767).astype(np.int16)

            # Add to circular buffer
            timestamp = time.time()
            self.buffer.add_samples(audio_data, timestamp)

            # Process audio in 30ms frames for VAD
            frame_size = self.vad.frame_size

            for i in range(0, len(audio_data), frame_size):
                frame = audio_data[i:i+frame_size]

                # Pad frame if necessary
                if len(frame) < frame_size:
                    frame = np.pad(frame, (0, frame_size - len(frame)), 'constant')

                # Process frame with VAD
                vad_result = self.vad.process_frame(frame)

                if "error" in vad_result:
                    continue

                # Update statistics
                self.stats["total_frames"] += 1
                if vad_result["is_voice"]:
                    self.stats["voice_frames"] += 1

                # Handle recording state changes
                if vad_result["should_start_recording"]:
                    self._start_recording()
                elif vad_result["should_stop_recording"]:
                    self._stop_recording()

                # Add frame to current recording if active
                if self.current_recording is not None:
                    self.current_recording.extend(frame)

        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
            self.stats["processing_errors"] += 1

    def _start_recording(self):
        """Start a new recording session."""
        if self.current_recording is not None:
            logger.warning("Starting new recording while previous one is active")

        # Get pre-voice samples from circular buffer (e.g., 200ms)
        pre_voice_samples, _ = self.buffer.get_duration_samples(0.2)

        # Initialize recording with pre-voice samples
        self.current_recording = list(pre_voice_samples)
        self.recording_start_time = time.time()

        logger.info(f"Started recording with {len(pre_voice_samples)} pre-voice samples")

    def _stop_recording(self):
        """Stop current recording and send to ASR queue."""
        if self.current_recording is None:
            logger.warning("Stop recording called but no recording is active")
            return

        try:
            # Convert recording to numpy array
            recording_array = np.array(self.current_recording)

            # Create WAV bytes
            wav_bytes = self._create_wav_bytes(recording_array)

            if wav_bytes:
                # Create audio segment info
                recording_info = {
                    "wav_data": wav_bytes,
                    "sample_rate": self.sample_rate,
                    "channels": self.channels,
                    "duration": len(recording_array) / self.sample_rate,
                    "timestamp": self.recording_start_time,
                    "samples": len(recording_array)
                }

                # Send to ASR queue with timeout to prevent blocking
                timeout_seconds = self.max_blocking_ms / 1000.0

                try:
                    self.asr_queue.put(recording_info, timeout=timeout_seconds)
                    self.stats["recordings_created"] += 1
                    logger.info(f"Sent recording to ASR queue: {recording_info['duration']:.2f}s, {recording_info['samples']} samples")
                    
                    # Log audio capture to database
                    if self.session_id:
                        processing_time = (time.time() - self.recording_start_time) * 1000  # Convert to ms
                        db_logger.log_audio_capture(
                            session_id=self.session_id,
                            channel=self.input_channel,
                            message=f"Captured {recording_info['duration']:.2f}s audio ({recording_info['samples']} samples)",
                            latency_ms=processing_time,
                            metadata={
                                "duration": recording_info['duration'],
                                "samples": recording_info['samples'],
                                "sample_rate": self.sample_rate,
                                "wav_size": len(wav_bytes)
                            }
                        )

                except queue.Full:
                    logger.warning(f"ASR queue full, dropping recording (timeout: {timeout_seconds}s)")
                    self.stats["queue_timeouts"] += 1
                    
                    # Log error to database
                    if self.session_id:
                        db_logger.log_audio_capture(
                            session_id=self.session_id,
                            channel=self.input_channel,
                            message=f"Queue full, dropped recording",
                            latency_ms=0,
                            errors=["Queue full - recording dropped"]
                        )

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.stats["processing_errors"] += 1

        finally:
            # Clear recording state
            self.current_recording = None
            self.recording_start_time = None

    def start(self):
        """Start the audio capture thread."""
        if self.is_running:
            logger.warning("Audio capture thread already running")
            return

        self.is_running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        logger.info("Audio capture thread started")

    def stop(self):
        """Stop the audio capture thread."""
        if not self.is_running:
            logger.warning("Audio capture thread not running")
            return

        self.is_running = False
        self.stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning("Audio capture thread did not stop gracefully")

        logger.info("Audio capture thread stopped")

    def _run(self):
        """Main thread execution."""
        try:
            logger.info(f"Starting audio stream: device={self.device}, sr={self.sample_rate}Hz")

            with sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                dtype=np.float32,
                callback=self._audio_callback
            ) as stream:

                logger.info("Audio stream started successfully")

                # Keep thread alive until stop is requested
                while not self.stop_event.is_set():
                    time.sleep(0.1)  # Small sleep to prevent busy waiting

                logger.info("Audio stream stopping...")

        except Exception as e:
            logger.error(f"Error in audio capture thread: {e}")
            self.stats["processing_errors"] += 1

        finally:
            # Clean up any active recording
            if self.current_recording is not None:
                logger.info("Cleaning up active recording on thread exit")
                self._stop_recording()

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return {
            **self.stats,
            "is_running": self.is_running,
            "is_recording": self.current_recording is not None,
            "vad_state": {
                "consecutive_voice_frames": self.vad.consecutive_voice_frames,
                "consecutive_silence_frames": self.vad.consecutive_silence_frames,
                "is_recording": self.vad.is_recording
            },
            "buffer_size": len(self.buffer.buffer),
            "queue_size": self.asr_queue.qsize() if hasattr(self.asr_queue, 'qsize') else -1
        }

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_frames": 0,
            "voice_frames": 0,
            "recordings_created": 0,
            "queue_timeouts": 0,
            "processing_errors": 0
        }
        logger.info("Statistics reset")


def create_audio_capture_thread(asr_queue: queue.Queue, **kwargs) -> AudioCaptureThread:
    """
    Factory function to create an AudioCaptureThread with default parameters.
    
    Args:
        asr_queue: Queue for sending audio segments to ASR
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured AudioCaptureThread instance
    """
    return AudioCaptureThread(asr_queue, **kwargs)


# Example usage and testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Audio Capture Thread (Hilo 1)")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--device", type=int, default=None, help="Audio device ID")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Sample rate")
    parser.add_argument("--vad-aggressiveness", type=int, default=2, choices=[0,1,2,3],
                       help="VAD aggressiveness level")
    parser.add_argument("--voice-threshold", type=int, default=200,
                       help="Voice detection threshold in ms")
    parser.add_argument("--silence-threshold", type=int, default=400,
                       help="Silence detection threshold in ms")

    args = parser.parse_args()

    # Create ASR queue
    asr_queue = queue.Queue(maxsize=10)

    # Create and start audio capture thread
    capture_thread = create_audio_capture_thread(
        asr_queue=asr_queue,
        sample_rate=args.sample_rate,
        device=args.device,
        vad_aggressiveness=args.vad_aggressiveness,
        voice_threshold_ms=args.voice_threshold,
        silence_threshold_ms=args.silence_threshold
    )

    print(f"Starting audio capture test for {args.duration} seconds...")
    print("Speak into the microphone to test voice detection and recording")
    print("Press Ctrl+C to stop early")

    try:
        capture_thread.start()

        # Monitor the queue and display captured audio info
        start_time = time.time()
        recordings_processed = 0

        while time.time() - start_time < args.duration:
            try:
                # Check for new recordings (non-blocking)
                recording_info = asr_queue.get(timeout=0.1)
                recordings_processed += 1

                print(f"Recording {recordings_processed}: {recording_info['duration']:.2f}s, "
                      f"{recording_info['samples']} samples, "
                      f"WAV size: {len(recording_info['wav_data'])} bytes")

                # In a real application, this would be sent to ASR
                # For testing, we just acknowledge the recording

            except queue.Empty:
                continue

        # Show final statistics
        stats = capture_thread.get_stats()
        print("\nFinal Statistics:")
        print(f"  Total frames: {stats['total_frames']}")
        print(f"  Voice frames: {stats['voice_frames']}")
        print(f"  Recordings created: {stats['recordings_created']}")
        print(f"  Queue timeouts: {stats['queue_timeouts']}")
        print(f"  Processing errors: {stats['processing_errors']}")

        if stats['total_frames'] > 0:
            voice_percentage = (stats['voice_frames'] / stats['total_frames']) * 100
            print(f"  Voice activity: {voice_percentage:.1f}%")

    except KeyboardInterrupt:
        print("\nTest interrupted by user")

    finally:
        capture_thread.stop()
        print("Audio capture thread stopped")
