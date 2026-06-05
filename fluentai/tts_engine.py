"""
TTS Engine — fast speech synthesis for Fluent AI.

macOS fast path: uses the built-in `say` command (~100ms latency).
Non-macOS fallback: pyttsx3 (~800ms latency).
"""

import functools
import logging
import os
import platform
import re
import subprocess
import tempfile

import numpy as np

logger = logging.getLogger(__name__)

# Preferred high-quality `say` voices per language, in priority order. Each is
# used only if actually installed; otherwise we fall back to any installed voice
# for the language, then to the system default. This avoids the old bug where a
# hardcoded name (e.g. "Monica" vs the installed "Mónica") silently fell back to
# the wrong voice.
_PREFERRED_VOICES: dict[str, list[str]] = {
    "en": ["Samantha", "Alex"],
    "es": ["Mónica", "Paulina"],
    "de": ["Anna", "Petra"],
    "fr": ["Thomas", "Amélie", "Audrey"],
}


@functools.lru_cache(maxsize=1)
def _installed_voices() -> dict[str, list[str]]:
    """Map a 2-letter language prefix → installed `say` voice names.

    Parses ``say -v '?'`` once (cached). Returns an empty map if `say` is
    unavailable.
    """
    voices: dict[str, list[str]] = {}
    try:
        result = subprocess.run(
            ["say", "-v", "?"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            match = re.match(r"^(.+?)\s+([a-z]{2})_[A-Z]{2}\s+#", line)
            if match:
                name, lang = match.group(1).strip(), match.group(2)
                voices.setdefault(lang, []).append(name)
    except Exception as exc:  # pragma: no cover - non-macOS / no `say`
        logger.debug("Could not list `say` voices: %s", exc)
    return voices


@functools.lru_cache(maxsize=16)
def _resolve_voice(lang: str) -> str | None:
    """Pick an installed `say` voice for *lang*, or None to use the default."""
    installed = _installed_voices().get(lang, [])
    for preferred in _PREFERRED_VOICES.get(lang, []):
        if preferred in installed:
            return preferred
    return installed[0] if installed else None


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

    voice = _resolve_voice(lang)

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = tmp.name

    try:
        say_cmd = ["say"]
        if voice:
            say_cmd.append(f"--voice={voice}")
        say_cmd += [f"--output-file={aiff_path}", text]
        result = subprocess.run(say_cmd, capture_output=True, timeout=10)
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
