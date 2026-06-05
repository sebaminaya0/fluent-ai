"""Unit tests for the shared audio preprocessing utilities."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai.audio_utils import (  # noqa: E402
    apply_automatic_gain_control,
    normalize_audio_rms,
)


def _pcm_bytes(samples: np.ndarray) -> bytes:
    return samples.astype(np.int16).tobytes()


def test_normalize_silence_is_unchanged():
    silence = _pcm_bytes(np.zeros(1000))
    assert normalize_audio_rms(silence) == silence


def test_normalize_preserves_length_and_dtype():
    quiet = _pcm_bytes(np.random.rand(2000) * 200 - 100)
    out = normalize_audio_rms(quiet)
    arr = np.frombuffer(out, dtype=np.int16)
    assert arr.size == 2000


def test_normalize_amplifies_quiet_signal_toward_target():
    quiet = _pcm_bytes(np.full(4000, 50))  # very low amplitude tone
    out = np.frombuffer(normalize_audio_rms(quiet, target_rms=0.2), dtype=np.int16)
    out_rms = np.sqrt(np.mean(out.astype(np.float32) ** 2))
    # Target RMS of 0.2 maps to ~0.2 * 32767 in int16 scale.
    assert out_rms > 50  # louder than the input
    assert out_rms <= 32767


def test_normalize_clips_to_int16_range():
    loud = _pcm_bytes(np.full(1000, 30000))
    out = np.frombuffer(normalize_audio_rms(loud, target_rms=0.99), dtype=np.int16)
    assert out.max() <= 32767
    assert out.min() >= -32767


def test_agc_silence_is_unchanged():
    silence = _pcm_bytes(np.zeros(1000))
    assert apply_automatic_gain_control(silence) == silence


def test_agc_preserves_length_and_stays_in_range():
    signal = _pcm_bytes(np.sin(np.linspace(0, 50, 3000)) * 8000)
    out = np.frombuffer(apply_automatic_gain_control(signal), dtype=np.int16)
    assert out.size == 3000
    assert out.max() <= 32767
    assert out.min() >= -32767


def test_empty_input_is_handled():
    assert normalize_audio_rms(b"") == b""
    assert apply_automatic_gain_control(b"") == b""
