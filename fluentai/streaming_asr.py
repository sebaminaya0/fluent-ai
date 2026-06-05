"""Streaming transcription for Meeting Mode (live captions + sentence audio).

The capture thread emits growing snapshots of the in-progress utterance. This
transcriber re-transcribes each snapshot and uses **LocalAgreement-2** to commit
only the word-prefix that two consecutive transcriptions agree on — stable text
that won't flicker. Committed text drives live captions; each newly completed
sentence is translated and pushed to the speak stage immediately, so audio starts
before the speaker finishes the whole turn.
"""

import io
import logging
import queue
import re
import threading
import time

import soundfile as sf

from fluentai.database_logger import db_logger

logger = logging.getLogger(__name__)

_SENTENCE_END = re.compile(r"[.!?]+(?:\s|$)")

# Whisper params that curb hallucination/looping on short streaming clips.
_TRANSCRIBE_OPTS = {
    "condition_on_previous_text": False,
    "temperature": 0.0,
    "no_speech_threshold": 0.6,
    "compression_ratio_threshold": 2.4,
}


def _common_prefix(a: list[str], b: list[str]) -> list[str]:
    """Longest common leading run of two word lists (LocalAgreement core)."""
    out = []
    for wa, wb in zip(a, b, strict=False):
        if wa != wb:
            break
        out.append(wa)
    return out


def _next_sentences(text: str, from_idx: int) -> tuple[list[str], int]:
    """Complete sentences in ``text[from_idx:]`` and the index past the last one.

    A sentence is text ending in ``.``/``!``/``?``. A trailing incomplete
    fragment is left for next time (the returned index does not advance past it).
    """
    segment = text[from_idx:]
    sentences: list[str] = []
    last_end = 0
    for match in _SENTENCE_END.finditer(segment):
        end = match.end()
        sentence = segment[last_end:end].strip()
        if sentence:
            sentences.append(sentence)
        last_end = end
    return sentences, from_idx + last_end


class StreamingTranscriber(threading.Thread):
    """Consume partial/final snapshots; emit live captions + sentence audio."""

    def __init__(
        self,
        asr_queue: queue.Queue,
        speak_queue: queue.Queue,
        controller,
        src_lang: str,
        dst_lang: str,
        whisper_model: str = "small",
        on_partial=None,
    ):
        super().__init__(daemon=True)
        self.asr_queue = asr_queue
        self.speak_queue = speak_queue
        self.controller = controller
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.whisper_model_name = whisper_model
        self.on_partial = on_partial  # callback(committed_text, tentative_text)
        self.stop_event = threading.Event()
        self.session_id = None
        self._whisper = None
        self._reset_utterance(None)

    def set_session_id(self, session_id: str):
        self.session_id = session_id

    def _reset_utterance(self, utterance_id):
        self._utt_id = utterance_id
        self._prev_words: list[str] = []
        self._committed_words: list[str] = []
        self._spoken_idx = 0

    def run(self):
        import whisper

        self._whisper = whisper.load_model(self.whisper_model_name, device="cpu")
        logger.info("StreamingTranscriber: whisper '%s' ready", self.whisper_model_name)
        while not self.stop_event.is_set():
            for item in self._drain_coalesced():
                try:
                    self._process(item)
                except Exception as e:
                    logger.error("StreamingTranscriber error: %s", e)

    def _drain_coalesced(self) -> list[dict]:
        """Block for items, then drop superseded partials (keep finals)."""
        items = []
        try:
            items.append(self.asr_queue.get(timeout=1))
        except queue.Empty:
            return []
        while True:
            try:
                items.append(self.asr_queue.get_nowait())
            except queue.Empty:
                break
        # Drop a partial if a later item for the same utterance exists.
        coalesced = []
        for i, it in enumerate(items):
            if not it.get("is_final") and any(
                later.get("utterance_id") == it.get("utterance_id")
                for later in items[i + 1 :]
            ):
                continue
            coalesced.append(it)
        return coalesced

    def _transcribe(self, audio) -> str:
        return self._whisper.transcribe(
            audio, language=self.src_lang, **_TRANSCRIBE_OPTS
        )["text"].strip()

    def _process(self, item: dict):
        uid = item.get("utterance_id")
        if uid != self._utt_id:
            self._reset_utterance(uid)

        audio = item.get("audio")
        if audio is None:
            audio, _sr = sf.read(io.BytesIO(item["wav_data"]), dtype="float32")
        is_final = bool(item.get("is_final"))

        cur_words = self._transcribe(audio).split()

        if is_final:
            committed_words = cur_words  # everything is stable now
        else:
            committed_words = _common_prefix(self._prev_words, cur_words)
            # Monotonic: never un-commit text we already showed/spoke.
            if len(committed_words) < len(self._committed_words):
                committed_words = self._committed_words
        self._prev_words = cur_words
        self._committed_words = committed_words

        committed_text = " ".join(committed_words)
        tentative = "" if is_final else " ".join(cur_words[len(committed_words) :])
        if self.on_partial:
            self.on_partial(committed_text, tentative)

        # Speak each newly completed sentence.
        sentences, new_idx = _next_sentences(committed_text, self._spoken_idx)
        for sentence in sentences:
            self._speak_sentence(sentence)
        self._spoken_idx = new_idx

        if is_final:
            tail = committed_text[self._spoken_idx :].strip()
            if tail:
                self._speak_sentence(tail)
            self._reset_utterance(None)

    def _speak_sentence(self, sentence: str):
        start = time.time()
        if self.src_lang == self.dst_lang:
            translated = sentence
        else:
            translated = (
                self.controller.translate(sentence, self.src_lang, self.dst_lang)
                or sentence
            )
        latency_ms = (time.time() - start) * 1000
        self.speak_queue.put(
            {"original": sentence, "translated": translated, "latency_ms": latency_ms}
        )
        if self.session_id:
            db_logger.log_asr_translation(
                session_id=self.session_id,
                input_lang=self.src_lang,
                output_lang=self.dst_lang,
                original_text=sentence,
                translated_text=translated,
                model_used=self.whisper_model_name,
                latency_ms=latency_ms,
                errors=[],
            )

    def stop(self):
        self.stop_event.set()
