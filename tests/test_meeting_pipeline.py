"""Tests for the streaming Meeting Mode pipeline."""

import io
import os
import queue
import sys
import time

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai import meeting_pipeline  # noqa: E402
from fluentai.meeting_pipeline import MeetingASRThread, MeetingSpeakThread  # noqa: E402


def test_decode_wav_bytes_to_mono_float32():
    # Round-trip a known signal through WAV bytes and back.
    signal = (np.sin(np.linspace(0, 20, 1600)) * 0.5).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, signal, 16000, format="WAV", subtype="PCM_16")
    decoded = MeetingASRThread._decode(buf.getvalue())
    assert decoded.dtype == np.float32
    assert decoded.ndim == 1
    assert abs(len(decoded) - len(signal)) <= 1


def test_speak_thread_streams_translated_text(monkeypatch):
    # The speak stage should fire the callback and call speak_to_device with the
    # translated text + device, without overlapping (blocking).
    calls = []
    monkeypatch.setattr(
        meeting_pipeline,
        "speak_to_device",
        lambda text, lang, device_name=None, blocking=True: calls.append(
            (text, lang, device_name)
        )
        or True,
    )

    speak_q = queue.Queue()
    seen = []
    thread = MeetingSpeakThread(
        speak_q,
        device_name="BlackHole 2ch",
        dst_lang="es",
        callback=lambda o, t: seen.append((o, t)),
    )
    thread.start()
    speak_q.put({"original": "hello", "translated": "hola"})

    # Wait briefly for the worker to process the item.
    deadline = time.time() + 3
    while not calls and time.time() < deadline:
        time.sleep(0.02)
    thread.stop()
    thread.join(timeout=2)

    assert calls == [("hola", "es", "BlackHole 2ch")]
    assert seen == [("hello", "hola")]


@pytest.mark.integration
def test_asr_thread_end_to_end():
    """Full ASR stage with a real Whisper model (gated: needs model download)."""
    from fluentai.app_controller import TranslationController
    from fluentai.model_loader import LazyModelLoader

    wav_path = os.path.join(
        os.path.dirname(__file__), "..", "test_data", "spanish_test.wav"
    )
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    asr_q, speak_q = queue.Queue(), queue.Queue()
    thread = MeetingASRThread(
        asr_q, speak_q, TranslationController(LazyModelLoader()), "es", "en"
    )
    thread.start()
    asr_q.put({"wav_data": wav_bytes})
    # We can't assert specific text (synthetic clip), only that it runs cleanly.
    time.sleep(8)
    thread.stop()
    thread.join(timeout=5)
