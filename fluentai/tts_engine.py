"""
TTS Engine — fast speech synthesis for Fluent AI.

macOS fast path: uses the built-in `say` command (~100ms latency).
Non-macOS fallback: pyttsx3 (~800ms latency).
"""

import logging
import os
import platform
import subprocess
import tempfile

import numpy as np

logger = logging.getLogger(__name__)

# macOS voice map: language code → `say` voice name
_MACOS_VOICES: dict[str, str] = {
    "en": "Samantha",
    "es": "Monica",
    "de": "Anna",
    "fr": "Thomas",
}


def synthesize_to_numpy(text: str, lang: str, sample_rate: int = 44100) -> np.ndarray:
    """Synthesize *text* in *lang* and return a float32 numpy array at *sample_rate* Hz.

    On macOS, uses the `say` command for ~100ms TTS.
    On other platforms, falls back to pyttsx3.

    Returns an empty array on failure.
    """
    if not text.strip():
        return np.array([], dtype=np.float32)

    if platform.system() == "Darwin":
        return _synthesize_macos(text, lang, sample_rate)
    return _synthesize_pyttsx3(text, sample_rate)


def _synthesize_macos(text: str, lang: str, sample_rate: int) -> np.ndarray:
    """macOS `say` fast path → AIFF → pydub → numpy float32."""
    from pydub import AudioSegment as PydubSegment

    voice = _MACOS_VOICES.get(lang, "Samantha")

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = tmp.name

    try:
        result = subprocess.run(
            ["say", f"--voice={voice}", f"--output-file={aiff_path}", text],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning(
                "say command failed (rc=%d), falling back to pyttsx3", result.returncode
            )
            return _synthesize_pyttsx3(text, sample_rate)

        audio = PydubSegment.from_file(aiff_path, format="aiff")
        audio = audio.set_frame_rate(sample_rate).set_channels(1)

        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        if len(samples) > 0:
            peak = np.max(np.abs(samples))
            if peak > 0:
                samples = samples / peak
        return samples

    except Exception as exc:
        logger.error("macOS TTS error: %s", exc)
        return np.array([], dtype=np.float32)
    finally:
        try:
            os.unlink(aiff_path)
        except OSError:
            pass


def _synthesize_pyttsx3(text: str, sample_rate: int) -> np.ndarray:
    """pyttsx3 fallback (cross-platform, ~800ms)."""
    import pyttsx3
    from pydub import AudioSegment as PydubSegment

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.save_to_file(text, wav_path)
        engine.runAndWait()

        audio = PydubSegment.from_wav(wav_path)
        audio = audio.set_frame_rate(sample_rate).set_channels(1)

        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        if len(samples) > 0:
            peak = np.max(np.abs(samples))
            if peak > 0:
                samples = samples / peak
        return samples

    except Exception as exc:
        logger.error("pyttsx3 TTS error: %s", exc)
        return np.array([], dtype=np.float32)
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass
