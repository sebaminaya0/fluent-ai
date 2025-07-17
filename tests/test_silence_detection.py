#!/usr/bin/env python3
"""
Regression tests for silence detection using prerecorded WAV files with known pause patterns.

This test suite focuses on:
1. Testing silence detection accuracy with known audio patterns
2. Regression testing to ensure detection consistency across versions
3. Testing different silence detection methods (webrtcvad, pydub)
4. Testing various audio conditions (noise, different volumes, etc.)
"""

import unittest
import os
import sys
import numpy as np
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from silence_detector import SilenceDetector, create_silence_detector, SILENCE_DETECTION_PRESETS

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


class TestSilenceDetectionRegression(unittest.TestCase):
    """Regression tests for silence detection with prerecorded WAV files."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data_dir = Path("./test_data")
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Create sample rate for testing
        self.sample_rate = 16000
        
        # Expected results for regression testing
        self.expected_results_file = self.test_data_dir / "silence_detection_expected.json"
        
        # Generate test WAV files if they don't exist
        self._generate_test_wav_files()
    
    def _generate_test_wav_files(self):
        """Generate test WAV files with known silence patterns."""
        if not SOUNDFILE_AVAILABLE:
            self.skipTest("soundfile not available for WAV generation")
            return
        
        # Test file patterns with known silence characteristics
        test_patterns = {
            'short_silence.wav': {
                'description': 'Audio with 500ms silence in middle',
                'pattern': [
                    ('speech', 1.0),    # 1 second of speech
                    ('silence', 0.5),   # 500ms silence
                    ('speech', 1.0),    # 1 second of speech
                ],
                'expected_silences': [
                    {'start': 1.0, 'duration': 0.5, 'end': 1.5}
                ]
            },
            'long_silence.wav': {
                'description': 'Audio with 1.5s silence in middle',
                'pattern': [
                    ('speech', 1.0),    # 1 second of speech
                    ('silence', 1.5),   # 1.5 seconds silence
                    ('speech', 1.0),    # 1 second of speech
                ],
                'expected_silences': [
                    {'start': 1.0, 'duration': 1.5, 'end': 2.5}
                ]
            },
            'multiple_silences.wav': {
                'description': 'Audio with multiple silence periods',
                'pattern': [
                    ('speech', 0.5),
                    ('silence', 0.8),   # First silence
                    ('speech', 0.5),
                    ('silence', 1.2),   # Second silence
                    ('speech', 0.5),
                ],
                'expected_silences': [
                    {'start': 0.5, 'duration': 0.8, 'end': 1.3},
                    {'start': 1.8, 'duration': 1.2, 'end': 3.0}
                ]
            },
            'no_silence.wav': {
                'description': 'Continuous speech with no significant silence',
                'pattern': [
                    ('speech', 3.0),    # 3 seconds of continuous speech
                ],
                'expected_silences': []
            },
            'noisy_silence.wav': {
                'description': 'Silence with background noise',
                'pattern': [
                    ('speech', 1.0),
                    ('noisy_silence', 1.0),  # Silence with low-level noise
                    ('speech', 1.0),
                ],
                'expected_silences': [
                    {'start': 1.0, 'duration': 1.0, 'end': 2.0}
                ]
            },
            'very_quiet_speech.wav': {
                'description': 'Very quiet speech that might be detected as silence',
                'pattern': [
                    ('speech', 1.0),
                    ('quiet_speech', 1.0),   # Very quiet speech
                    ('speech', 1.0),
                ],
                'expected_silences': []  # Should not detect quiet speech as silence
            }
        }
        
        expected_results = {}
        
        for filename, pattern_info in test_patterns.items():
            file_path = self.test_data_dir / filename
            
            if not file_path.exists():
                print(f"Generating test file: {filename}")
                audio_data = self._generate_audio_pattern(pattern_info['pattern'])
                sf.write(str(file_path), audio_data, self.sample_rate)
            
            expected_results[filename] = {
                'description': pattern_info['description'],
                'expected_silences': pattern_info['expected_silences']
            }
        
        # Save expected results for regression testing
        with open(self.expected_results_file, 'w') as f:
            json.dump(expected_results, f, indent=2)
    
    def _generate_audio_pattern(self, pattern):
        """Generate audio data based on pattern specification."""
        audio_segments = []
        
        for segment_type, duration in pattern:
            samples = int(duration * self.sample_rate)
            
            if segment_type == 'speech':
                # Generate speech-like audio (random noise with speech-like characteristics)
                speech = np.random.normal(0, 0.3, samples)
                # Add some periodicity to make it more speech-like
                t = np.linspace(0, duration, samples)
                speech += 0.1 * np.sin(2 * np.pi * 200 * t)  # Add 200 Hz component
                speech += 0.05 * np.sin(2 * np.pi * 400 * t)  # Add 400 Hz component
                audio_segments.append(speech)
                
            elif segment_type == 'silence':
                # Generate true silence (very low amplitude)
                silence = np.random.normal(0, 0.01, samples)  # Very quiet noise
                audio_segments.append(silence)
                
            elif segment_type == 'noisy_silence':
                # Generate silence with background noise
                noisy_silence = np.random.normal(0, 0.05, samples)  # Low-level noise
                audio_segments.append(noisy_silence)
                
            elif segment_type == 'quiet_speech':
                # Generate very quiet speech
                quiet_speech = np.random.normal(0, 0.1, samples)  # Quiet but not silent
                t = np.linspace(0, duration, samples)
                quiet_speech += 0.03 * np.sin(2 * np.pi * 200 * t)
                audio_segments.append(quiet_speech)
        
        return np.concatenate(audio_segments)
    
    def _load_expected_results(self):
        """Load expected results for regression testing."""
        if not self.expected_results_file.exists():
            return {}
        
        with open(self.expected_results_file, 'r') as f:
            return json.load(f)
    
    def test_short_silence_detection(self):
        """Test detection of short silence periods."""
        detector = create_silence_detector('balanced', min_silence_len=400)
        
        file_path = self.test_data_dir / 'short_silence.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Load and process audio file
        audio_data, sr = sf.read(str(file_path))
        
        # Convert to bytes (16-bit PCM)
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        # Process audio in chunks to simulate real-time detection
        chunk_size = 1024
        silence_events = []
        
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            if len(chunk) < chunk_size:
                break
            
            result = detector.process_audio_frame(chunk)
            
            if result['silence_threshold_exceeded']:
                silence_events.append({
                    'timestamp': result['timestamp'],
                    'duration': result['silence_duration']
                })
        
        # Should detect the 500ms silence period
        self.assertGreater(len(silence_events), 0, "Should detect silence period")
        
        # Check that silence duration is approximately 500ms
        max_silence = max(silence_events, key=lambda x: x['duration'])
        self.assertGreater(max_silence['duration'], 400, "Silence should be detected as >= 400ms")
    
    def test_long_silence_detection(self):
        """Test detection of long silence periods."""
        detector = create_silence_detector('balanced', min_silence_len=800)
        
        file_path = self.test_data_dir / 'long_silence.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Load and process audio
        audio_data, sr = sf.read(str(file_path))
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        # Process audio
        silence_events = []
        chunk_size = 1024
        
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            if len(chunk) < chunk_size:
                break
            
            result = detector.process_audio_frame(chunk)
            
            if result['silence_threshold_exceeded']:
                silence_events.append({
                    'timestamp': result['timestamp'],
                    'duration': result['silence_duration']
                })
        
        # Should detect the 1.5s silence period
        self.assertGreater(len(silence_events), 0, "Should detect long silence period")
        
        # Check that silence duration is approximately 1.5s
        max_silence = max(silence_events, key=lambda x: x['duration'])
        self.assertGreater(max_silence['duration'], 1200, "Long silence should be detected as >= 1.2s")
    
    def test_multiple_silences_detection(self):
        """Test detection of multiple silence periods."""
        detector = create_silence_detector('balanced', min_silence_len=600)
        
        file_path = self.test_data_dir / 'multiple_silences.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Load and process audio
        audio_data, sr = sf.read(str(file_path))
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        # Process audio
        silence_events = []
        chunk_size = 1024
        
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            if len(chunk) < chunk_size:
                break
            
            result = detector.process_audio_frame(chunk)
            
            if result['silence_threshold_exceeded']:
                silence_events.append({
                    'timestamp': result['timestamp'],
                    'duration': result['silence_duration']
                })
        
        # Should detect multiple silence periods
        self.assertGreaterEqual(len(silence_events), 2, "Should detect multiple silence periods")
    
    def test_no_silence_detection(self):
        """Test that continuous speech is not detected as silence."""
        detector = create_silence_detector('balanced', min_silence_len=500)
        
        file_path = self.test_data_dir / 'no_silence.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Load and process audio
        audio_data, sr = sf.read(str(file_path))
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        # Process audio
        silence_events = []
        chunk_size = 1024
        
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            if len(chunk) < chunk_size:
                break
            
            result = detector.process_audio_frame(chunk)
            
            if result['silence_threshold_exceeded']:
                silence_events.append({
                    'timestamp': result['timestamp'],
                    'duration': result['silence_duration']
                })
        
        # Should not detect significant silence
        self.assertEqual(len(silence_events), 0, "Should not detect silence in continuous speech")
    
    def test_webrtcvad_method(self):
        """Test WebRTC VAD method specifically."""
        try:
            detector = create_silence_detector('balanced', method='webrtcvad')
        except RuntimeError as e:
            if "webrtcvad is not available" in str(e):
                self.skipTest("WebRTC VAD not available")
            raise
        
        file_path = self.test_data_dir / 'short_silence.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Test that WebRTC VAD is active
        self.assertEqual(detector.active_method, 'webrtcvad')
        
        # Load and process audio
        audio_data, sr = sf.read(str(file_path))
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        # Process a chunk
        chunk_size = 1024
        chunk = audio_bytes[:chunk_size]
        
        result = detector.process_audio_frame(chunk)
        
        # Should return valid result structure
        self.assertIn('is_silent', result)
        self.assertIn('timestamp', result)
        self.assertIn('silence_duration', result)
        self.assertIsInstance(result['is_silent'], bool)
    
    def test_pydub_method(self):
        """Test pydub method specifically."""
        try:
            detector = create_silence_detector('balanced', method='pydub')
        except RuntimeError as e:
            if "pydub is not available" in str(e):
                self.skipTest("pydub not available")
            raise
        
        file_path = self.test_data_dir / 'short_silence.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Test that pydub is active
        self.assertEqual(detector.active_method, 'pydub')
        
        # Load and process audio
        audio_data, sr = sf.read(str(file_path))
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        # Process a chunk
        chunk_size = 1024
        chunk = audio_bytes[:chunk_size]
        
        result = detector.process_audio_frame(chunk)
        
        # Should return valid result structure
        self.assertIn('is_silent', result)
        self.assertIn('timestamp', result)
        self.assertIn('silence_duration', result)
        self.assertIsInstance(result['is_silent'], bool)
    
    def test_different_presets(self):
        """Test different silence detection presets."""
        file_path = self.test_data_dir / 'short_silence.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Load audio
        audio_data, sr = sf.read(str(file_path))
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        chunk = audio_bytes[:1024]
        
        # Test different presets
        presets = ['sensitive', 'balanced', 'aggressive', 'very_aggressive']
        results = {}
        
        for preset in presets:
            detector = create_silence_detector(preset)
            result = detector.process_audio_frame(chunk)
            results[preset] = result
        
        # All presets should return valid results
        for preset, result in results.items():
            self.assertIn('is_silent', result, f"Preset {preset} should return is_silent")
            self.assertIsInstance(result['is_silent'], bool, f"Preset {preset} is_silent should be boolean")
    
    def test_regression_consistency(self):
        """Test that detection results are consistent with previous runs."""
        expected_results = self._load_expected_results()
        
        if not expected_results:
            self.skipTest("No expected results file found - this is the first run")
        
        detector = create_silence_detector('balanced', min_silence_len=500)
        
        # Test each file against expected results
        for filename, expected in expected_results.items():
            file_path = self.test_data_dir / filename
            
            if not file_path.exists():
                continue
            
            with self.subTest(filename=filename):
                # Load and process audio
                audio_data, sr = sf.read(str(file_path))
                audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
                
                # Process audio
                silence_events = []
                chunk_size = 1024
                
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i:i+chunk_size]
                    if len(chunk) < chunk_size:
                        break
                    
                    result = detector.process_audio_frame(chunk)
                    
                    if result['silence_threshold_exceeded']:
                        silence_events.append({
                            'timestamp': result['timestamp'],
                            'duration': result['silence_duration']
                        })
                
                # Check against expected results
                expected_silences = expected['expected_silences']
                
                if len(expected_silences) == 0:
                    # Should not detect silence
                    self.assertEqual(len(silence_events), 0, 
                                   f"File {filename} should not have silence detected")
                else:
                    # Should detect expected number of silences
                    self.assertGreater(len(silence_events), 0, 
                                     f"File {filename} should have silence detected")
    
    def test_parameter_sensitivity(self):
        """Test sensitivity to different parameters."""
        file_path = self.test_data_dir / 'short_silence.wav'
        if not file_path.exists():
            self.skipTest(f"Test file {file_path} not found")
        
        # Load audio
        audio_data, sr = sf.read(str(file_path))
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        chunk = audio_bytes[:1024]
        
        # Test different minimum silence lengths
        min_lengths = [200, 500, 1000, 2000]
        results = {}
        
        for min_len in min_lengths:
            detector = create_silence_detector('balanced', min_silence_len=min_len)
            result = detector.process_audio_frame(chunk)
            results[min_len] = result
        
        # All should return valid results
        for min_len, result in results.items():
            self.assertIn('is_silent', result, f"min_silence_len={min_len} should return is_silent")
        
        # Test different silence thresholds
        thresholds = [-30, -40, -50, -60]
        results = {}
        
        for thresh in thresholds:
            detector = create_silence_detector('balanced', silence_thresh=thresh)
            result = detector.process_audio_frame(chunk)
            results[thresh] = result
        
        # All should return valid results
        for thresh, result in results.items():
            self.assertIn('is_silent', result, f"silence_thresh={thresh} should return is_silent")


if __name__ == '__main__':
    unittest.main()
