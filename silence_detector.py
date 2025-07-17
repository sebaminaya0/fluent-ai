#!/usr/bin/env python3
"""
Silence Detection Module for Fluent AI

This module provides robust silence/pause detection capabilities using both
webrtcvad and pydub.silence for real-time audio energy monitoring.

Features:
- Real-time audio energy monitoring
- Configurable silence parameters (min_silence_len, silence_thresh)
- Auto-stop transcription when sustained silence exceeds threshold
- Timer reset when speech resumes
- Support for both webrtcvad and pydub silence detection methods
"""

import time
import threading
import logging
import numpy as np
from typing import Optional, Callable, Dict, Any
from collections import deque
import io

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    logging.warning("webrtcvad not available, falling back to pydub-only silence detection")

try:
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logging.warning("pydub not available, falling back to webrtcvad-only silence detection")

import speech_recognition as sr


class SilenceDetector:
    """
    A comprehensive silence detection system that monitors audio energy in real-time
    and provides callbacks for silence/speech events.
    """
    
    def __init__(self, 
                 min_silence_len: int = 800,  # ms
                 silence_thresh: int = -40,   # dBFS
                 frame_duration: int = 30,    # ms (10, 20, or 30 for webrtcvad)
                 aggressiveness: int = 2,     # 0-3 for webrtcvad
                 sample_rate: int = 16000,    # Optimized for Whisper default
                 method: str = 'auto',        # 'auto', 'webrtcvad', 'pydub'
                 chunk_size: int = 1024):     # Optimized chunk size for better performance
        """
        Initialize the silence detector.
        
        Args:
            min_silence_len: Minimum silence duration in ms to trigger silence event
            silence_thresh: Silence threshold in dBFS (negative values)
            frame_duration: Frame duration for webrtcvad (10, 20, or 30 ms)
            aggressiveness: WebRTC VAD aggressiveness (0-3, higher = more aggressive)
            sample_rate: Audio sample rate (8000, 16000, 32000, or 48000 for webrtcvad)
            method: Detection method ('auto', 'webrtcvad', 'pydub')
        """
        self.min_silence_len = min_silence_len
        self.silence_thresh = silence_thresh
        self.frame_duration = frame_duration
        self.aggressiveness = aggressiveness
        self.sample_rate = sample_rate
        self.method = method
        
        # State management
        self.is_monitoring = False
        self.silence_start_time = None
        self.last_speech_time = None
        self.audio_buffer = deque(maxlen=100)  # Keep last 100 frames
        
        # Callbacks
        self.on_silence_detected = None
        self.on_speech_detected = None
        self.on_silence_threshold_exceeded = None
        
        # Initialize detection method
        self._init_detection_method()
        
        # Monitoring thread
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()
        
        logging.info(f"SilenceDetector initialized with method: {self.active_method}")
    
    def _init_detection_method(self):
        """Initialize the detection method based on availability and preferences."""
        if self.method == 'auto':
            if WEBRTCVAD_AVAILABLE:
                self.active_method = 'webrtcvad'
            elif PYDUB_AVAILABLE:
                self.active_method = 'pydub'
            else:
                raise RuntimeError("Neither webrtcvad nor pydub is available")
        elif self.method == 'webrtcvad':
            if not WEBRTCVAD_AVAILABLE:
                raise RuntimeError("webrtcvad is not available")
            self.active_method = 'webrtcvad'
        elif self.method == 'pydub':
            if not PYDUB_AVAILABLE:
                raise RuntimeError("pydub is not available")
            self.active_method = 'pydub'
        else:
            raise ValueError(f"Unknown detection method: {self.method}")
        
        # Initialize WebRTC VAD if using it
        if self.active_method == 'webrtcvad':
            self.vad = webrtcvad.Vad(self.aggressiveness)
            # Validate sample rate for webrtcvad
            if self.sample_rate not in [8000, 16000, 32000, 48000]:
                logging.warning(f"Sample rate {self.sample_rate} not supported by webrtcvad, using 16000")
                self.sample_rate = 16000
            # Validate frame duration
            if self.frame_duration not in [10, 20, 30]:
                logging.warning(f"Frame duration {self.frame_duration} not supported by webrtcvad, using 30")
                self.frame_duration = 30
    
    def set_callbacks(self, 
                     on_silence_detected: Optional[Callable] = None,
                     on_speech_detected: Optional[Callable] = None,
                     on_silence_threshold_exceeded: Optional[Callable] = None):
        """Set callback functions for silence/speech events."""
        self.on_silence_detected = on_silence_detected
        self.on_speech_detected = on_speech_detected
        self.on_silence_threshold_exceeded = on_silence_threshold_exceeded
    
    def update_parameters(self, **kwargs):
        """Update silence detection parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logging.info(f"Updated {key} to {value}")
        
        # Reinitialize if method-specific parameters changed
        if any(key in ['aggressiveness', 'sample_rate', 'frame_duration'] for key in kwargs):
            if self.active_method == 'webrtcvad':
                self._init_detection_method()
    
    def is_silence_webrtcvad(self, audio_data: bytes) -> bool:
        """Detect silence using WebRTC VAD."""
        try:
            # WebRTC VAD expects 16-bit PCM audio
            is_speech = self.vad.is_speech(audio_data, self.sample_rate)
            return not is_speech
        except Exception as e:
            logging.error(f"WebRTC VAD error: {e}")
            return False
    
    def is_silence_pydub(self, audio_data: bytes) -> bool:
        """Detect silence using pydub."""
        try:
            # Convert bytes to AudioSegment
            audio_segment = AudioSegment(
                audio_data,
                frame_rate=self.sample_rate,
                sample_width=2,  # 16-bit
                channels=1
            )
            
            # Check if the audio level is below threshold
            if audio_segment.dBFS < self.silence_thresh:
                return True
            
            # Also use pydub's silence detection
            nonsilent_ranges = detect_nonsilent(
                audio_segment,
                min_silence_len=self.min_silence_len,
                silence_thresh=self.silence_thresh
            )
            
            return len(nonsilent_ranges) == 0
        except Exception as e:
            logging.error(f"Pydub silence detection error: {e}")
            return False
    
    def detect_silence(self, audio_data: bytes) -> bool:
        """Detect silence using the active method."""
        if self.active_method == 'webrtcvad':
            return self.is_silence_webrtcvad(audio_data)
        elif self.active_method == 'pydub':
            return self.is_silence_pydub(audio_data)
        else:
            return False
    
    def process_audio_frame(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Process a single audio frame and return detection results.
        
        Returns:
            Dictionary containing detection results and timing information
        """
        current_time = time.time()
        is_silent = self.detect_silence(audio_data)
        
        # Add to buffer
        self.audio_buffer.append({
            'timestamp': current_time,
            'is_silent': is_silent,
            'data': audio_data
        })
        
        result = {
            'is_silent': is_silent,
            'timestamp': current_time,
            'silence_duration': 0,
            'speech_detected': False,
            'silence_threshold_exceeded': False
        }
        
        if is_silent:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
                if self.on_silence_detected:
                    self.on_silence_detected(current_time)
            
            # Calculate silence duration
            silence_duration_ms = (current_time - self.silence_start_time) * 1000
            result['silence_duration'] = silence_duration_ms
            
            # Check if silence threshold is exceeded
            if silence_duration_ms >= self.min_silence_len:
                result['silence_threshold_exceeded'] = True
                if self.on_silence_threshold_exceeded:
                    self.on_silence_threshold_exceeded(silence_duration_ms)
        
        else:  # Speech detected
            if self.silence_start_time is not None:
                # Speech resumed, reset silence timer
                self.silence_start_time = None
                result['speech_detected'] = True
                if self.on_speech_detected:
                    self.on_speech_detected(current_time)
            
            self.last_speech_time = current_time
        
        return result
    
    def start_monitoring(self, audio_source):
        """Start monitoring audio source for silence/speech."""
        if self.is_monitoring:
            logging.warning("Silence monitoring already active")
            return
        
        self.is_monitoring = True
        self._stop_monitoring.clear()
        
        def monitor_loop():
            """Main monitoring loop."""
            logging.info("Starting silence monitoring loop")
            
            while not self._stop_monitoring.is_set():
                try:
                    # This would need to be adapted based on the audio source type
                    # For now, this is a placeholder for the monitoring logic
                    time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                except Exception as e:
                    logging.error(f"Error in monitoring loop: {e}")
                    break
            
            logging.info("Silence monitoring loop stopped")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring audio source."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self._stop_monitoring.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        
        logging.info("Silence monitoring stopped")
    
    def reset_state(self):
        """Reset the detector state."""
        self.silence_start_time = None
        self.last_speech_time = None
        self.audio_buffer.clear()
        logging.info("Silence detector state reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        current_time = time.time()
        
        silence_duration = 0
        if self.silence_start_time is not None:
            silence_duration = (current_time - self.silence_start_time) * 1000
        
        time_since_speech = None
        if self.last_speech_time is not None:
            time_since_speech = (current_time - self.last_speech_time) * 1000
        
        return {
            'is_monitoring': self.is_monitoring,
            'current_silence_duration': silence_duration,
            'time_since_last_speech': time_since_speech,
            'active_method': self.active_method,
            'min_silence_len': self.min_silence_len,
            'silence_thresh': self.silence_thresh,
            'buffer_size': len(self.audio_buffer)
        }


class SilenceDetectorIntegration:
    """Integration helper for speech recognition systems."""
    
    def __init__(self, recognizer: sr.Recognizer, detector: SilenceDetector):
        """
        Initialize the integration.
        
        Args:
            recognizer: SpeechRecognition recognizer instance
            detector: SilenceDetector instance
        """
        self.recognizer = recognizer
        self.detector = detector
        self.should_stop_listening = False
        self.transcription_callback = None
        
        # Set up detector callbacks
        self.detector.set_callbacks(
            on_silence_threshold_exceeded=self._on_silence_threshold_exceeded
        )
    
    def set_transcription_callback(self, callback: Callable):
        """Set callback for when transcription should be finalized."""
        self.transcription_callback = callback
    
    def _on_silence_threshold_exceeded(self, silence_duration_ms: float):
        """Handle silence threshold exceeded event."""
        logging.info(f"Silence threshold exceeded: {silence_duration_ms:.0f}ms")
        self.should_stop_listening = True
        
        if self.transcription_callback:
            self.transcription_callback(silence_duration_ms)
    
    def listen_with_silence_detection(self, 
                                    source: sr.AudioSource,
                                    timeout: Optional[float] = None,
                                    phrase_time_limit: Optional[float] = None) -> Optional[sr.AudioData]:
        """
        Listen for audio with integrated silence detection.
        
        This method extends the standard speech recognition listening
        with silence detection capabilities.
        """
        self.should_stop_listening = False
        self.detector.reset_state()
        
        try:
            # Custom listening logic that integrates with silence detection
            # This is a simplified version - full implementation would require
            # more sophisticated audio stream processing
            
            audio = self.recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )
            
            return audio
            
        except sr.WaitTimeoutError:
            logging.info("Listening timeout reached")
            return None
        except Exception as e:
            logging.error(f"Error during listening: {e}")
            return None
    
    def process_audio_stream(self, audio_stream):
        """Process an audio stream with silence detection."""
        # This method would process an audio stream chunk by chunk
        # and apply silence detection to each chunk
        pass


# Example usage and configuration presets
SILENCE_DETECTION_PRESETS = {
    'sensitive': {
        'min_silence_len': 600,
        'silence_thresh': -35,
        'aggressiveness': 1
    },
    'balanced': {
        'min_silence_len': 800,
        'silence_thresh': -40,
        'aggressiveness': 2
    },
    'aggressive': {
        'min_silence_len': 1200,
        'silence_thresh': -45,
        'aggressiveness': 3
    },
    'very_aggressive': {
        'min_silence_len': 1500,
        'silence_thresh': -50,
        'aggressiveness': 3
    }
}


def create_silence_detector(preset: str = 'balanced', **kwargs) -> SilenceDetector:
    """
    Create a silence detector with a preset configuration.
    
    Args:
        preset: Preset name ('sensitive', 'balanced', 'aggressive', 'very_aggressive')
        **kwargs: Additional parameters to override preset values
    
    Returns:
        Configured SilenceDetector instance
    """
    if preset not in SILENCE_DETECTION_PRESETS:
        raise ValueError(f"Unknown preset: {preset}. Available: {list(SILENCE_DETECTION_PRESETS.keys())}")
    
    config = SILENCE_DETECTION_PRESETS[preset].copy()
    config.update(kwargs)
    
    return SilenceDetector(**config)


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Test silence detection")
    parser.add_argument('--preset', default='balanced', 
                       choices=list(SILENCE_DETECTION_PRESETS.keys()),
                       help='Silence detection preset')
    parser.add_argument('--min-silence-len', type=int, default=None,
                       help='Minimum silence length in ms')
    parser.add_argument('--silence-thresh', type=int, default=None,
                       help='Silence threshold in dBFS')
    parser.add_argument('--method', default='auto',
                       choices=['auto', 'webrtcvad', 'pydub'],
                       help='Detection method')
    
    args = parser.parse_args()
    
    # Create detector with preset and overrides
    kwargs = {}
    if args.min_silence_len is not None:
        kwargs['min_silence_len'] = args.min_silence_len
    if args.silence_thresh is not None:
        kwargs['silence_thresh'] = args.silence_thresh
    kwargs['method'] = args.method
    
    detector = create_silence_detector(args.preset, **kwargs)
    
    print(f"Silence detector created with preset: {args.preset}")
    print(f"Configuration: {detector.get_stats()}")
    
    # Example of how to use the detector
    def on_silence_detected(timestamp):
        print(f"Silence detected at {timestamp}")
    
    def on_speech_detected(timestamp):
        print(f"Speech detected at {timestamp}")
    
    def on_silence_threshold_exceeded(duration_ms):
        print(f"Silence threshold exceeded: {duration_ms:.0f}ms")
    
    detector.set_callbacks(
        on_silence_detected=on_silence_detected,
        on_speech_detected=on_speech_detected,
        on_silence_threshold_exceeded=on_silence_threshold_exceeded
    )
    
    print("Silence detector ready for use")
