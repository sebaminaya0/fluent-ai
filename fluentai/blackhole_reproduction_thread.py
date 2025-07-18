import queue
import threading
import time

import numpy as np
import sounddevice as sd

from fluentai.database_logger import db_logger, get_device_name


class JitterBuffer:
    """
    Buffer to handle jitter in streaming audio, storing up to a fixed duration of audio data.
    """

    def __init__(self, sample_rate: int, duration: float = 0.25):
        self.buffer = queue.Queue()
        self.sample_rate = sample_rate
        self.duration = duration
        self.chunk_size = int(self.sample_rate * self.duration)

    def add_chunk(self, chunk: np.ndarray):
        self.buffer.put(chunk)

    def get_next_chunk(self) -> np.ndarray:
        return self.buffer.get() if not self.buffer.empty() else np.array([])

    def flush(self):
        while not self.buffer.empty():
            self.buffer.get()

class BlackHoleReproductionThread(threading.Thread):
    """
    Thread to manage audio playback via BlackHole, buffering audio to handle jitter.
    """

    def __init__(self, output_device: int, input_queue: queue.Queue, sample_rate: int = 44100):
        super().__init__()
        self.jitter_buffer = JitterBuffer(sample_rate)
        self.input_queue = input_queue
        self.output_device = output_device
        self.sample_rate = sample_rate
        self.stop_event = threading.Event()
        self.daemon = True
        
        # Database logging
        self.session_id = None
        self.output_channel = get_device_name(output_device)
        
    def set_session_id(self, session_id: str):
        """Set the session ID for database logging."""
        self.session_id = session_id
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Session ID set to: {session_id}")

    def run(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting BlackHole playback thread on device {self.output_device}")
        
        try:
            with sd.OutputStream(device=self.output_device, samplerate=self.sample_rate, channels=1, latency="low") as stream:
                logger.info("BlackHole audio stream started")
                
                while not self.stop_event.is_set():
                    try:
                        # Get audio from input queue (non-blocking)
                        audio_chunk = self.input_queue.get(timeout=0.1)
                        logger.info(f"Got audio chunk from queue: {len(audio_chunk)} samples")
                        
                        # Track playback timing
                        start_time = time.time()
                        playback_errors = []
                        
                        try:
                            # Process large audio chunks in smaller pieces
                            chunk_size = 1024  # Process in 1024 sample chunks
                            
                            # Ensure audio is in correct format for sounddevice
                            if audio_chunk.dtype != np.float32:
                                audio_chunk = audio_chunk.astype(np.float32)
                            
                            # Reshape for mono output if needed
                            if len(audio_chunk.shape) == 1:
                                audio_chunk = audio_chunk.reshape(-1, 1)
                            
                            # Play audio in chunks to avoid buffer issues
                            for i in range(0, len(audio_chunk), chunk_size):
                                chunk = audio_chunk[i:i+chunk_size]
                                if chunk.size > 0:
                                    stream.write(chunk)
                                    time.sleep(0.001)  # Small delay to avoid overwhelming the buffer
                            
                            logger.info(f"Played audio chunk: {len(audio_chunk)} samples")
                            
                        except Exception as e:
                            playback_errors.append(f"Audio playback error: {e}")
                            logger.error(f"Error playing audio: {e}")
                        
                        # Log playback to database
                        if self.session_id:
                            playback_time = (time.time() - start_time) * 1000  # Convert to ms
                            db_logger.log_audio_playback(
                                session_id=self.session_id,
                                output_channel=self.output_channel,
                                message=f"Played {len(audio_chunk)} samples",
                                latency_ms=playback_time,
                                errors=playback_errors,
                                metadata={
                                    "sample_rate": self.sample_rate,
                                    "audio_samples": len(audio_chunk),
                                    "chunk_size": chunk_size
                                }
                            )
                        
                    except queue.Empty:
                        # No audio available, play from jitter buffer if available
                        next_chunk = self.jitter_buffer.get_next_chunk()
                        if next_chunk.size > 0:
                            if next_chunk.dtype != np.float32:
                                next_chunk = next_chunk.astype(np.float32)
                            if len(next_chunk.shape) == 1:
                                next_chunk = next_chunk.reshape(-1, 1)
                            stream.write(next_chunk)
                        else:
                            time.sleep(0.01)  # Avoid busy waiting
                            
        except Exception as e:
            logger.error(f"Error in BlackHole playback thread: {e}")
            
        logger.info("BlackHole playback thread stopped")

    def add_audio_chunk(self, chunk: np.ndarray):
        self.jitter_buffer.add_chunk(chunk)

    def flush_buffer(self):
        self.jitter_buffer.flush()

    def stop(self):
        self.stop_event.set()
        self.flush_buffer()

