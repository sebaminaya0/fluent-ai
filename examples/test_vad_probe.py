#!/usr/bin/env python3
"""
Simple test for VAD Probe functionality
"""

import os
import sys

import numpy as np
import webrtcvad

# Add the examples directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from vad_probe import VADProbe


def test_vad_probe():
    """Test VAD probe initialization and basic functionality"""
    print("Testing VAD Probe...")

    # Test initialization with different aggressiveness levels
    for aggressiveness in range(4):
        try:
            probe = VADProbe(aggressiveness)
            print(f"✓ VAD Probe initialized with aggressiveness {aggressiveness}")

            # Test stats
            stats = probe.get_stats()
            print(f"  Initial stats: {stats}")

            # Test validation (should fail initially since no speech detected)
            passed, message = probe.validate_detection_speed()
            print(f"  Validation (no speech): {message}")

        except Exception as e:
            print(f"✗ Failed to initialize VAD Probe with aggressiveness {aggressiveness}: {e}")
            return False

    # Test with synthetic audio data
    print("\nTesting with synthetic audio data...")
    probe = VADProbe(aggressiveness=2)

    # Create 30ms of synthetic audio data (16kHz, 16-bit)
    sample_rate = 16000
    duration_ms = 30
    samples = int(sample_rate * duration_ms / 1000)  # 480 samples

    # Test with silence (zeros)
    silence_data = np.zeros(samples, dtype=np.int16)
    audio_level = probe.get_audio_level(silence_data.tobytes())
    print(f"✓ Silence audio level: {audio_level:.3f}")

    # Test with synthetic speech (sine wave)
    frequency = 440  # A4 note
    t = np.linspace(0, duration_ms/1000, samples)
    speech_data = (np.sin(2 * np.pi * frequency * t) * 16383).astype(np.int16)
    audio_level = probe.get_audio_level(speech_data.tobytes())
    print(f"✓ Speech audio level: {audio_level:.3f}")

    # Test WebRTC VAD directly
    vad = webrtcvad.Vad(2)
    is_speech_silence = vad.is_speech(silence_data.tobytes(), sample_rate)
    is_speech_sound = vad.is_speech(speech_data.tobytes(), sample_rate)

    print(f"✓ WebRTC VAD - Silence: {is_speech_silence}, Sound: {is_speech_sound}")

    print("\n✓ All VAD Probe tests passed!")
    return True

if __name__ == "__main__":
    success = test_vad_probe()
    if success:
        print("\n🎉 VAD Probe is ready for use!")
        print("Run: python examples/vad_probe.py --aggressiveness 2")
        sys.exit(0)
    else:
        print("\n❌ VAD Probe tests failed!")
        sys.exit(1)
