"""
Hilo 2 - ASR Whisper → Traducción → Síntesis

Este módulo implementa un hilo para procesamiento de audio en pipeline:
• Transcribe audio con Whisper en inglés.
• Traduce el texto si el idioma de destino no es inglés usando MarianMT.
• Genera un archivo de audio usando gTTS.
• Envía los resultados a una cola de salida.
"""

import io
import logging
import queue
import threading
import time

import numpy as np
import whisper
from gtts import gTTS
from transformers import pipeline

from fluentai.database_logger import db_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ASRTranslationSynthesisThread(threading.Thread):
    def __init__(self, queue_in, queue_out, src_lang='en', dst_lang='en', whisper_model='base'):
        super().__init__()
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.whisper_model_name = whisper_model
        self.stop_event = threading.Event()
        
        # Database logging
        self.session_id = None

        # Models will be loaded in the run method
        self.whisper_model = None
        self.translation_pipeline = None
        
    def set_session_id(self, session_id: str):
        """Set the session ID for database logging."""
        self.session_id = session_id
        logger.info(f"Session ID set to: {session_id}")

    def _load_models(self):
        """Load models in the thread context to avoid initialization issues."""
        try:
            logger.info(f"Loading Whisper model: {self.whisper_model_name}")
            self.whisper_model = whisper.load_model(self.whisper_model_name, device="cpu")
            logger.info("Whisper model loaded successfully")

            # Load translation pipeline if needed (if source and destination are different)
            if self.src_lang != self.dst_lang:
                logger.info(f"Loading translation pipeline: {self.src_lang} -> {self.dst_lang}")
                self.translation_pipeline = pipeline(
                    "translation",
                    model=f"Helsinki-NLP/opus-mt-{self.src_lang}-{self.dst_lang}",
                    device="cpu"
                )
                logger.info("Translation pipeline loaded successfully")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise

    def run(self):
        # Load models on first run to avoid initialization issues
        self._load_models()

        while not self.stop_event.is_set():
            try:
                # Get WAV data from input queue
                audio_segment = self.queue_in.get(timeout=1)
                logger.info("Processing audio segment...")
                
                # Track processing time
                start_time = time.time()
                original_text = ""
                translated_text = ""
                processing_errors = []

                # Transcribe audio to text
                # Convert WAV bytes to numpy array for Whisper
                import os
                import tempfile

                # Write WAV bytes to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(audio_segment['wav_data'])
                    temp_file_path = temp_file.name

                try:
                    # Use the temporary file path with Whisper
                    # Specify source language to avoid detection issues
                    result = self.whisper_model.transcribe(temp_file_path, language=self.src_lang)
                    original_text = result['text'].strip()
                    logger.info(f"Whisper transcribed: '{original_text}' (language: {result.get('language', 'unknown')})")
                except Exception as e:
                    processing_errors.append(f"Whisper transcription error: {e}")
                    logger.error(f"Error in transcription: {e}")
                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)

                # Skip empty transcriptions
                if not original_text:
                    if self.session_id:
                        db_logger.log_asr_translation(
                            session_id=self.session_id,
                            input_lang=self.src_lang,
                            output_lang=self.dst_lang,
                            original_text="",
                            translated_text="",
                            model_used=self.whisper_model_name,
                            latency_ms=(time.time() - start_time) * 1000,
                            errors=processing_errors + ["Empty transcription"]
                        )
                    logger.warning("Empty transcription, skipping synthesis")
                    continue
                    
                # Translate text if necessary (if source and destination are different)
                translated_text = original_text  # Default to original text
                if self.src_lang != self.dst_lang:
                    try:
                        logger.info(f"Translating from {self.src_lang} to {self.dst_lang}...")
                        translation = self.translation_pipeline(original_text)
                        translated_text = translation[0]['translation_text']
                        logger.info(f"Translated text: '{translated_text}'")
                    except Exception as e:
                        processing_errors.append(f"Translation error: {e}")
                        logger.error(f"Error in translation: {e}")
                        translated_text = original_text  # Fall back to original

                # Skip empty translations
                if not translated_text:
                    if self.session_id:
                        db_logger.log_asr_translation(
                            session_id=self.session_id,
                            input_lang=self.src_lang,
                            output_lang=self.dst_lang,
                            original_text=original_text,
                            translated_text="",
                            model_used=self.whisper_model_name,
                            latency_ms=(time.time() - start_time) * 1000,
                            errors=processing_errors + ["Empty translation"]
                        )
                    logger.warning("Empty translation, skipping synthesis")
                    continue

                # Synthesize translated text to speech
                try:
                    logger.info(f"Synthesizing speech in {self.dst_lang}: '{translated_text}'")
                    tts = gTTS(text=translated_text, lang=self.dst_lang)

                    # Save to a file-like object to convert to np.float32 array
                    buf = io.BytesIO()
                    tts.write_to_fp(buf)
                    buf.seek(0)

                    # Convert MP3 data to audio array using pydub
                    from pydub import AudioSegment
                    from pydub.playback import play
                    import tempfile
                    import os
                    
                    # Write MP3 bytes to temporary file
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
                        temp_mp3.write(buf.read())
                        temp_mp3_path = temp_mp3.name
                    
                    try:
                        # Load MP3 and convert to numpy array
                        audio_segment = AudioSegment.from_mp3(temp_mp3_path)
                        
                        # Convert to 44100 Hz mono (matching BlackHole output)
                        audio_segment = audio_segment.set_frame_rate(44100).set_channels(1)
                        
                        # Convert to numpy array (float32)
                        audio_fp = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
                        
                        # Normalize to [-1, 1] range
                        if len(audio_fp) > 0:
                            audio_fp = audio_fp / np.max(np.abs(audio_fp))
                        
                        # Place in output queue
                        self.queue_out.put(audio_fp)
                        logger.info(f"Audio segment processed and placed in output queue: {len(audio_fp)} samples")
                        
                    finally:
                        # Clean up temporary file
                        os.unlink(temp_mp3_path)
                        
                except Exception as e:
                    processing_errors.append(f"TTS synthesis error: {e}")
                    logger.error(f"Error in TTS synthesis: {e}")
                
                # Log processing to database
                if self.session_id:
                    processing_time = (time.time() - start_time) * 1000
                    db_logger.log_asr_translation(
                        session_id=self.session_id,
                        input_lang=self.src_lang,
                        output_lang=self.dst_lang,
                        original_text=original_text,
                        translated_text=translated_text,
                        model_used=self.whisper_model_name,
                        latency_ms=processing_time,
                        errors=processing_errors,
                        metadata={
                            "audio_duration": audio_segment.get('duration', 0),
                            "audio_samples": audio_segment.get('samples', 0),
                            "output_samples": len(audio_fp) if 'audio_fp' in locals() else 0
                        }
                    )

            except queue.Empty:
                continue

            except Exception as e:
                logger.error(f"Error during audio processing: {e}")

    def stop(self):
        self.stop_event.set()


