"""Tests for the streaming transcriber (LocalAgreement-2 + sentence audio)."""

import os
import queue
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai.streaming_asr import (  # noqa: E402
    StreamingTranscriber,
    _common_prefix,
    _next_sentences,
)


def test_common_prefix():
    assert _common_prefix(["a", "b", "c"], ["a", "b", "x"]) == ["a", "b"]
    assert _common_prefix([], ["a"]) == []
    assert _common_prefix(["a"], ["a"]) == ["a"]
    assert _common_prefix(["x"], ["y"]) == []


def test_next_sentences():
    s, idx = _next_sentences("Hello world. How are you?", 0)
    assert s == ["Hello world.", "How are you?"]
    assert idx == len("Hello world. How are you?")

    # No terminal punctuation -> nothing complete yet, index unchanged.
    s, idx = _next_sentences("incomplete sentence without", 0)
    assert s == [] and idx == 0

    # One complete sentence + a trailing fragment that stays uncommitted.
    s, idx = _next_sentences("Done. Not done", 0)
    assert s == ["Done."] and idx == len("Done. ")


class _FakeWhisper:
    def __init__(self, scripts):
        self.scripts = scripts
        self.i = 0

    def transcribe(self, audio, **kwargs):
        text = self.scripts[self.i]
        self.i += 1
        return {"text": text}


class _FakeController:
    def translate(self, text, src, dst):
        return f"[{dst}] {text}"


def _item(uid, final):
    return {
        "audio": np.zeros(1, dtype=np.float32),
        "utterance_id": uid,
        "is_final": final,
    }


def test_streaming_commits_monotonically_and_speaks_each_sentence_once():
    # Simulated growing transcriptions of one utterance.
    scripts = [
        "I think we should meet.",  # partial 1: nothing agreed yet
        "I think we should meet. Let us",  # partial 2: sentence 1 now stable
        "I think we should meet. Let us go.",  # final: sentence 2 completes
    ]
    speak_q = queue.Queue()
    partials = []
    st = StreamingTranscriber(
        queue.Queue(),
        speak_q,
        _FakeController(),
        "en",
        "es",
        on_partial=lambda c, t: partials.append(c),
    )
    st._whisper = _FakeWhisper(scripts)

    st._process(_item(1, False))
    st._process(_item(1, False))
    st._process(_item(1, True))

    spoken = [speak_q.get()["original"] for _ in range(speak_q.qsize())]
    assert spoken == ["I think we should meet.", "Let us go."]

    # Committed captions grow monotonically (each a prefix of the next).
    assert partials == [
        "",
        "I think we should meet.",
        "I think we should meet. Let us go.",
    ]


def test_translation_is_applied_per_sentence():
    speak_q = queue.Queue()
    st = StreamingTranscriber(queue.Queue(), speak_q, _FakeController(), "en", "es")
    st._whisper = _FakeWhisper(["Hello there."])
    st._process(_item(1, True))
    item = speak_q.get()
    assert item["original"] == "Hello there."
    assert item["translated"] == "[es] Hello there."
