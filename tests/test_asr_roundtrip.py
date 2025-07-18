#!/usr/bin/env python3
"""
ASR Round-trip tests for Spanish to English translation.

This test suite validates the complete ASR -> Translation -> TTS pipeline
for Spanish to English translation to ensure the system works end-to-end.
"""

import os
import queue
import sys
import time
import unittest
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fluentai.asr_translation_synthesis_thread import ASRTranslationSynthesisThread
    ASR_THREAD_AVAILABLE = True
except ImportError:
    ASR_THREAD_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


class TestASRRoundTrip(unittest.TestCase):
    """Test ASR to TTS round-trip functionality for Spanish to English."""

    def setUp(self):
        """Set up test fixtures."""
        if not ASR_THREAD_AVAILABLE:
            self.skipTest("ASR thread not available")
        if not SOUNDFILE_AVAILABLE:
            self.skipTest("soundfile not available")
        if not WHISPER_AVAILABLE:
            self.skipTest("whisper not available")

        self.test_data_dir = Path("./test_data")
        self.test_data_dir.mkdir(exist_ok=True)

        # Create test audio files if needed
        self._create_test_audio_files()

    def _create_test_audio_files(self):
        """Create test audio files for ASR testing."""
        # Generate a simple test audio file with Spanish-like characteristics
        sample_rate = 16000
        duration = 2.0  # 2 seconds

        # Create test audio that simulates Spanish speech patterns
        test_audio_path = self.test_data_dir / "spanish_test.wav"
        if not test_audio_path.exists():
            # Generate synthetic audio with speech-like characteristics
            samples = int(duration * sample_rate)
            t = np.linspace(0, duration, samples)

            # Create a synthetic speech-like signal
            audio = np.zeros(samples)

            # Add fundamental frequency around 150 Hz (typical for Spanish)
            audio += 0.3 * np.sin(2 * np.pi * 150 * t)

            # Add harmonics
            audio += 0.2 * np.sin(2 * np.pi * 300 * t)
            audio += 0.1 * np.sin(2 * np.pi * 450 * t)

            # Add some noise to make it more realistic
            audio += 0.05 * np.random.normal(0, 1, samples)

            # Add amplitude modulation to simulate speech patterns
            envelope = 0.5 * (1 + np.sin(2 * np.pi * 5 * t))  # 5 Hz modulation
            audio *= envelope

            # Normalize
            audio = audio / np.max(np.abs(audio)) * 0.8

            # Save as WAV file
            sf.write(str(test_audio_path), audio, sample_rate)

    def _create_wav_bytes(self, audio_path):
        """Convert audio file to WAV bytes for testing."""
        import io
        import wave

        # Read the audio file
        audio_data, sample_rate = sf.read(str(audio_path))

        # Convert to 16-bit PCM
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Create WAV bytes
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        return wav_buffer.getvalue()

    def test_spanish_to_english(self):
        """Test Spanish to English ASR round-trip."""
        # Create input and output queues
        q_in = queue.Queue()
        q_out = queue.Queue()

        # Initialize ASR thread
        thread = ASRTranslationSynthesisThread(
            q_in, q_out,
            src_lang='es',
            dst_lang='en',
            whisper_model='base'  # Use smaller model for testing
        )

        # Start the thread
        thread.start()

        try:
            # Load test audio file
            test_audio_path = self.test_data_dir / "spanish_test.wav"
            wav_bytes = self._create_wav_bytes(test_audio_path)

            # Put test audio in input queue
            q_in.put({
                'wav_data': wav_bytes,
                'timestamp': time.time()
            })

            # Wait for processing (give it up to 30 seconds)
            result = None
            for _ in range(30):
                try:
                    result = q_out.get(timeout=1)
                    break
                except queue.Empty:
                    continue

            # Verify result
            self.assertIsNotNone(result, "No result received from ASR thread")
            self.assertIsInstance(result, np.ndarray, "Result should be numpy array")
            self.assertGreater(len(result), 0, "Result should not be empty")

            # Verify audio characteristics
            self.assertTrue(np.isfinite(result).all(), "Result should contain finite values")
            self.assertLessEqual(np.max(np.abs(result)), 1.0, "Audio should be normalized")

        finally:
            # Clean up
            thread.stop()
            thread.join(timeout=5)

    def test_english_passthrough(self):
        """Test English to English passthrough (no translation)."""
        # Create input and output queues
        q_in = queue.Queue()
        q_out = queue.Queue()

        # Initialize ASR thread with English to English (no translation)
        thread = ASRTranslationSynthesisThread(
            q_in, q_out,
            src_lang='en',
            dst_lang='en',
            whisper_model='base'
        )

        # Start the thread
        thread.start()

        try:
            # Load test audio file
            test_audio_path = self.test_data_dir / "spanish_test.wav"
            wav_bytes = self._create_wav_bytes(test_audio_path)

            # Put test audio in input queue
            q_in.put({
                'wav_data': wav_bytes,
                'timestamp': time.time()
            })

            # Wait for processing
            result = None
            for _ in range(30):
                try:
                    result = q_out.get(timeout=1)
                    break
                except queue.Empty:
                    continue

            # Verify result
            self.assertIsNotNone(result, "No result received from ASR thread")
            self.assertIsInstance(result, np.ndarray, "Result should be numpy array")
            self.assertGreater(len(result), 0, "Result should not be empty")

        finally:
            # Clean up
            thread.stop()
            thread.join(timeout=5)

    def test_asr_thread_initialization(self):
        """Test ASR thread initialization with different language pairs."""
        # Test different language configurations
        test_configs = [
            {'src_lang': 'es', 'dst_lang': 'en'},
            {'src_lang': 'en', 'dst_lang': 'es'},
            {'src_lang': 'en', 'dst_lang': 'en'},
        ]

        for config in test_configs:
            with self.subTest(config=config):
                q_in = queue.Queue()
                q_out = queue.Queue()

                thread = ASRTranslationSynthesisThread(
                    q_in, q_out,
                    src_lang=config['src_lang'],
                    dst_lang=config['dst_lang'],
                    whisper_model='base'
                )

                # Test initialization
                self.assertEqual(thread.src_lang, config['src_lang'])
                self.assertEqual(thread.dst_lang, config['dst_lang'])
                self.assertEqual(thread.whisper_model_name, 'base')

                # Test thread can be started and stopped
                thread.start()
                time.sleep(0.1)  # Give it a moment to initialize
                thread.stop()
                thread.join(timeout=5)

                self.assertFalse(thread.is_alive(), "Thread should be stopped")


if __name__ == '__main__':
    unittest.main()

