"""Unit tests for the unified chunked transcription helper.

A fake Whisper-like model records the calls made to ``.transcribe`` so we can
assert on branching/argument behavior without downloading real models. The
short test-data clips exercise the single-shot path (duration <= chunk_length).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai.transcription import transcribe_long_audio  # noqa: E402

TEST_WAV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "test_data",
    "spanish_test.wav",
)


class FakeModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_file, **kwargs):
        self.calls.append((audio_file, kwargs))
        return {"text": "hola", "language": "es", "segments": []}


def test_single_shot_autodetect_passes_no_language():
    model = FakeModel()
    result = transcribe_long_audio(model, TEST_WAV)
    assert result["text"] == "hola"
    assert len(model.calls) == 1
    _, kwargs = model.calls[0]
    assert "language" not in kwargs  # auto-detect => no language hint


def test_single_shot_forced_language_is_passed():
    model = FakeModel()
    transcribe_long_audio(model, TEST_WAV, language="es")
    _, kwargs = model.calls[0]
    assert kwargs["language"] == "es"


def test_transcribe_options_are_forwarded():
    model = FakeModel()
    transcribe_long_audio(
        model, TEST_WAV, transcribe_options={"fp16": False, "temperature": 0.0}
    )
    _, kwargs = model.calls[0]
    assert kwargs["fp16"] is False
    assert kwargs["temperature"] == 0.0


def test_min_duration_skips_and_returns_empty():
    model = FakeModel()
    result = transcribe_long_audio(model, TEST_WAV, min_duration=9999)
    assert result["text"] == ""
    assert result["language"] == "es"  # default when language is None
    assert model.calls == []  # model never invoked


def test_min_duration_skip_keeps_forced_language():
    model = FakeModel()
    result = transcribe_long_audio(model, TEST_WAV, language="fr", min_duration=9999)
    assert result["language"] == "fr"
    assert model.calls == []
