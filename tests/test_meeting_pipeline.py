"""Tests for the streaming Meeting Mode pipeline."""

import io
import os
import queue
import sys
import threading
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
        callback=lambda o, t, lat: seen.append((o, t, lat)),
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
    assert seen == [("hello", "hola", None)]


def test_speak_thread_mutes_mic_during_playback(monkeypatch):
    # The half-duplex gate must be held while speaking and released afterward,
    # so the capture thread ignores our own TTS output (no feedback loop).
    mute = threading.Event()
    observed = {}

    def fake_speak(text, lang, device_name=None, blocking=True):
        observed["muted_while_speaking"] = mute.is_set()
        return True

    monkeypatch.setattr(meeting_pipeline, "speak_to_device", fake_speak)

    speak_q = queue.Queue()
    thread = MeetingSpeakThread(
        speak_q, None, "es", mute_event=mute, echo_cooldown_s=0.0
    )
    thread.start()
    speak_q.put({"original": "hi", "translated": "hola"})

    deadline = time.time() + 3
    while "muted_while_speaking" not in observed and time.time() < deadline:
        time.sleep(0.02)
    time.sleep(0.1)  # let the cooldown clear the gate
    thread.stop()
    thread.join(timeout=2)

    assert observed["muted_while_speaking"] is True
    assert not mute.is_set()  # released after playback


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
