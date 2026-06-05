"""Low-latency streaming pipeline for Meeting Mode.

Two stages connected by a queue so the next utterance is transcribed/translated
while the current one is still being spoken:

    asr_queue   -> MeetingASRThread   (decode WAV bytes -> numpy, Whisper, translate)
                -> speak_queue
                -> MeetingSpeakThread  (stream via `say --audio-device`, blocking)

Versus the older single ``ASRTranslationSynthesisThread`` this:
- feeds Whisper a numpy array directly (no temp-WAV round-trip), and
- streams TTS straight to the output device (no synthesize-to-numpy +
  BlackHole playback thread), so audio starts in ~milliseconds.
"""

import io
import logging
import queue
import threading
import time

import soundfile as sf

from fluentai.database_logger import db_logger
from fluentai.tts_engine import speak_to_device, synthesize_to_numpy

logger = logging.getLogger(__name__)


class MeetingASRThread(threading.Thread):
    """Transcribe + translate captured segments, hand text to the speak stage."""

    def __init__(
        self,
        asr_queue: queue.Queue,
        speak_queue: queue.Queue,
        controller,
        src_lang: str,
        dst_lang: str,
        whisper_model: str = "base",
    ):
        super().__init__(daemon=True)
        self.asr_queue = asr_queue
        self.speak_queue = speak_queue
        self.controller = controller
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.whisper_model_name = whisper_model
        self.stop_event = threading.Event()
        self.session_id = None
        self._whisper = None

    def set_session_id(self, session_id: str):
        self.session_id = session_id

    def run(self):
        import whisper

        self._whisper = whisper.load_model(self.whisper_model_name, device="cpu")
        logger.info("MeetingASRThread: whisper '%s' ready", self.whisper_model_name)

        while not self.stop_event.is_set():
            try:
                segment = self.asr_queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                start = time.time()
                audio = self._decode(segment["wav_data"])
                result = self._whisper.transcribe(audio, language=self.src_lang)
                original = result["text"].strip()
                if not original:
                    continue

                if self.src_lang == self.dst_lang:
                    translated = original
                else:
                    translated = (
                        self.controller.translate(
                            original, self.src_lang, self.dst_lang
                        )
                        or original
                    )

                self.speak_queue.put({"original": original, "translated": translated})

                if self.session_id:
                    db_logger.log_asr_translation(
                        session_id=self.session_id,
                        input_lang=self.src_lang,
                        output_lang=self.dst_lang,
                        original_text=original,
                        translated_text=translated,
                        model_used=self.whisper_model_name,
                        latency_ms=(time.time() - start) * 1000,
                        errors=[],
                    )
            except Exception as e:
                logger.error("MeetingASRThread error: %s", e)

    @staticmethod
    def _decode(wav_bytes: bytes):
        """Decode 16-bit PCM WAV bytes to a mono float32 array (no temp file)."""
        audio, _sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        return audio

    def stop(self):
        self.stop_event.set()


class MeetingSpeakThread(threading.Thread):
    """Speak translated text by streaming directly to the chosen output device."""

    def __init__(
        self,
        speak_queue: queue.Queue,
        device_name: str | None,
        dst_lang: str,
        callback=None,
    ):
        super().__init__(daemon=True)
        self.speak_queue = speak_queue
        self.device_name = device_name
        self.dst_lang = dst_lang
        self.callback = callback
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            try:
                item = self.speak_queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                # Update the UI first so text appears as playback starts.
                if self.callback:
                    self.callback(item["original"], item["translated"])

                # Blocking so utterances don't overlap; the ASR stage keeps
                # working on the next segment in parallel meanwhile.
                ok = speak_to_device(
                    item["translated"],
                    self.dst_lang,
                    device_name=self.device_name,
                    blocking=True,
                )
                if not ok:
                    self._fallback_play(item["translated"])
            except Exception as e:
                logger.error("MeetingSpeakThread error: %s", e)

    def _fallback_play(self, text: str):
        """Non-macOS / failure path: render to numpy and play via sounddevice."""
        try:
            import sounddevice as sd

            samples = synthesize_to_numpy(text, self.dst_lang, sample_rate=44100)
            if samples.size:
                sd.play(samples, samplerate=44100)
                sd.wait()
        except Exception as e:
            logger.error("Fallback playback failed: %s", e)

    def stop(self):
        self.stop_event.set()
