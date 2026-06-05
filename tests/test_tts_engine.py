"""Unit tests for `say` voice resolution in the TTS engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai import tts_engine  # noqa: E402

SAMPLE_SAY_OUTPUT = """\
Albert              en_US    # Hello! My name is Albert.
Samantha            en_US    # Hello! My name is Samantha.
Mónica              es_ES    # ¡Hola! Me llamo Mónica.
Eddy (Spanish (Spain)) es_ES # ¡Hola! Me llamo Eddy.
Anna                de_DE    # Hallo! Ich heiße Anna.
Thomas              fr_FR    # Bonjour, je m'appelle Thomas.
"""


def _patch_voices(monkeypatch, stdout):
    class FakeResult:
        def __init__(self, out):
            self.stdout = out

    monkeypatch.setattr(
        tts_engine.subprocess,
        "run",
        lambda *a, **k: FakeResult(stdout),
    )
    tts_engine._installed_voices.cache_clear()
    tts_engine._resolve_voice.cache_clear()


def test_resolves_preferred_installed_voice(monkeypatch):
    _patch_voices(monkeypatch, SAMPLE_SAY_OUTPUT)
    # "Mónica" (accented) is the preferred es voice and is installed.
    assert tts_engine._resolve_voice("es") == "Mónica"
    assert tts_engine._resolve_voice("en") == "Samantha"
    assert tts_engine._resolve_voice("de") == "Anna"
    assert tts_engine._resolve_voice("fr") == "Thomas"


def test_falls_back_to_any_installed_voice(monkeypatch):
    # No preferred es voice installed; should pick the only installed es voice.
    out = "Eddy (Spanish (Spain)) es_ES # ¡Hola!\nSamantha en_US # Hi\n"
    _patch_voices(monkeypatch, out)
    assert tts_engine._resolve_voice("es") == "Eddy (Spanish (Spain))"


def test_returns_none_for_unsupported_language(monkeypatch):
    _patch_voices(monkeypatch, SAMPLE_SAY_OUTPUT)
    assert tts_engine._resolve_voice("ja") is None


def test_speak_to_device_builds_streaming_command(monkeypatch):
    _patch_voices(monkeypatch, SAMPLE_SAY_OUTPUT)
    monkeypatch.setattr(tts_engine.platform, "system", lambda: "Darwin")
    # Warm the voice cache from the fake list before swapping in the capturer,
    # so the only subprocess.run call we capture is the speak command.
    assert tts_engine._resolve_voice("es") == "Mónica"

    captured = {}
    monkeypatch.setattr(
        tts_engine.subprocess, "run", lambda cmd, **k: captured.__setitem__("cmd", cmd)
    )

    ok = tts_engine.speak_to_device("Hola", "es", device_name="BlackHole 2ch")
    assert ok is True
    cmd = captured["cmd"]
    assert cmd[0] == "say"
    assert "--voice=Mónica" in cmd
    assert "--audio-device=BlackHole 2ch" in cmd
    assert cmd[-1] == "Hola"


def test_speak_to_device_non_macos_returns_false(monkeypatch):
    monkeypatch.setattr(tts_engine.platform, "system", lambda: "Linux")
    assert tts_engine.speak_to_device("hi", "en") is False


def test_speak_to_device_empty_text_returns_false(monkeypatch):
    monkeypatch.setattr(tts_engine.platform, "system", lambda: "Darwin")
    assert tts_engine.speak_to_device("   ", "en") is False


def teardown_module(module):
    # Don't leak the fake voice cache into other tests.
    tts_engine._installed_voices.cache_clear()
    tts_engine._resolve_voice.cache_clear()
