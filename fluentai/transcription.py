"""Chunked Whisper transcription shared by the GUI and CLI entry points.

Previously this logic was duplicated as ``transcribe_long_audio`` in
``main_whisper.py`` and a richer ``transcribe_long_audio_gui`` method on the GUI
class. This single implementation covers both via keyword options:

- ``language``: ``None`` auto-detects; a code (e.g. ``"es"``) is forced.
- ``min_duration``: clips below this (seconds) are skipped and return empty text.
- ``transcribe_options``: extra kwargs passed to ``model.transcribe`` on the
  whole-file / short-audio / fallback paths (e.g. ``word_timestamps=True``).
  Per-chunk transcription intentionally uses only the language hint, matching
  the original behavior of both callers.
"""

import os
import tempfile

EMPTY_LANGUAGE_DEFAULT = "es"


def transcribe_long_audio(
    model,
    audio_file,
    *,
    language=None,
    chunk_length=30,
    min_duration=0.0,
    transcribe_options=None,
):
    """Transcribe an audio file, splitting long recordings into chunks.

    Args:
        model: A loaded Whisper model exposing ``.transcribe()``.
        audio_file: Path to the audio file (read at 16 kHz).
        language: Language code, or ``None`` to auto-detect.
        chunk_length: Chunk size in seconds for long audio.
        min_duration: Skip transcription for clips shorter than this (seconds).
        transcribe_options: Extra kwargs for whole-file / fallback transcription.

    Returns:
        A dict with ``text``, ``language`` and ``segments`` keys, matching the
        shape of ``model.transcribe`` consumers in this project.
    """
    lang_kwargs = {"language": language} if language else {}
    options = transcribe_options or {}

    try:
        import librosa

        audio, sr = librosa.load(audio_file, sr=16000)
        audio_duration = len(audio) / sr
        print(f"Audio duration: {audio_duration:.2f} seconds")

        # Too short for Whisper to do anything useful with.
        if audio_duration < min_duration:
            print(f"Audio too short ({audio_duration:.2f}s), skipping transcription")
            return {
                "text": "",
                "language": language or EMPTY_LANGUAGE_DEFAULT,
                "segments": [],
            }

        # Short enough to transcribe in one shot.
        if audio_duration <= chunk_length:
            return model.transcribe(audio_file, **lang_kwargs, **options)

        # Long audio: transcribe in chunks.
        texts = []
        chunk_size = int(chunk_length * sr)
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_chunk:
                chunk_filename = temp_chunk.name
                import soundfile as sf

                sf.write(chunk_filename, chunk, sr)
                try:
                    chunk_result = model.transcribe(chunk_filename, **lang_kwargs)
                    texts.append(chunk_result["text"])
                    print(f"Chunk {len(texts)}: '{chunk_result['text']}'")
                finally:
                    try:
                        os.unlink(chunk_filename)
                    except Exception:
                        pass

        combined_text = " ".join(texts).strip()

        # Determine the result language: use the forced one, else detect it.
        result_language = language or EMPTY_LANGUAGE_DEFAULT
        if language is None:
            try:
                first_chunk_result = model.transcribe(audio_file, language=None)
                result_language = first_chunk_result["language"]
            except Exception:
                pass

        return {
            "text": combined_text,
            "language": result_language,
            "segments": [],  # Could be enhanced to combine per-chunk segments.
        }

    except ImportError:
        print("Warning: librosa not available, falling back to regular transcription")
        return model.transcribe(audio_file, **lang_kwargs, **options)
    except Exception as e:
        print(f"Error in chunked transcription: {e}")
        return model.transcribe(audio_file, **lang_kwargs, **options)
