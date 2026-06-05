"""Audio preprocessing utilities shared by the GUI and CLI entry points.

These pure functions operate on 16-bit PCM audio held as ``bytes``. They were
previously duplicated as module-level functions in ``main_whisper.py`` and as
methods on the ``FluentAIGUI`` class; this module is now the single source.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


def normalize_audio_rms(audio_data: bytes, target_rms: float = 0.2) -> bytes:
    """Normalize 16-bit PCM audio to a target RMS level for better ASR.

    Args:
        audio_data: Raw 16-bit PCM audio as bytes.
        target_rms: Target RMS level in the range 0.0-1.0.

    Returns:
        Normalized audio as bytes. The input is returned unchanged if it is
        silent (RMS == 0) or if normalization fails for any reason.
    """
    try:
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        if audio_array.size == 0:
            return audio_data

        current_rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
        if current_rms <= 0:
            return audio_data

        scale = (target_rms * 32767) / current_rms
        normalized = np.clip(audio_array * scale, -32767, 32767)
        return normalized.astype(np.int16).tobytes()
    except Exception as e:  # pragma: no cover - defensive fallback
        logger.warning("Audio normalization failed: %s", e)
        return audio_data


def apply_automatic_gain_control(audio_data: bytes) -> bytes:
    """Apply gentle compression and a mild gain boost to 16-bit PCM audio.

    Reduces dynamic range and lifts quiet speech for more consistent results
    across microphones.

    Args:
        audio_data: Raw 16-bit PCM audio as bytes.

    Returns:
        Audio with AGC applied as bytes. The input is returned unchanged if it
        is silent (peak == 0) or if AGC fails for any reason.
    """
    try:
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)

        peak = np.max(np.abs(audio_array)) if audio_array.size else 0
        if peak <= 0:
            return audio_data

        # Gentle compression to reduce dynamic range.
        compressed = (
            np.sign(audio_array) * np.power(np.abs(audio_array) / peak, 0.7) * peak
        )

        # Mild gain boost for quiet speech (capped at 2x).
        gain_factor = min(2.0, 16000 / (peak + 1))
        boosted = compressed * gain_factor

        result = np.clip(boosted, -32767, 32767)
        return result.astype(np.int16).tobytes()
    except Exception as e:  # pragma: no cover - defensive fallback
        logger.warning("AGC failed: %s", e)
        return audio_data
