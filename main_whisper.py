import argparse
import os
import re
import sys
import tempfile
import time

# Suppress specific warnings
import warnings

import sounddevice as sd
import speech_recognition as sr

from fluentai import LazyModelLoader
from fluentai.audio_utils import (
    apply_automatic_gain_control,
    normalize_audio_rms,
)
from fluentai.transcription import transcribe_long_audio
from fluentai.tts_engine import synthesize_to_numpy
from silence_detector import (
    SilenceDetectorIntegration,
    create_silence_detector,
)

warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

# --- 1. CONFIGURACIÓN INICIAL ---

# Inicializar el reconocedor de voz (como fallback)
recognizer = sr.Recognizer()

# Suprimir warnings de Whisper
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")

# Global variables to be initialized based on CLI args
model_loader = None
whisper_model = None
src_lang = None
tgt_lang = None
auto_detect = False
silence_detector = None
silence_integration = None
args = None


# --- 2. DEFINICIÓN DE FUNCIONES ---


def es_texto_latino(texto):
    """
    Verifica si el texto contiene principalmente caracteres latinos (español/inglés).
    Retorna False si detecta caracteres de otros alfabetos como griego, cirílico, etc.
    """
    # Caracteres latinos básicos + acentos españoles + signos de puntuación
    caracteres_latinos = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "áéíóúüñÁÉÍÓÚÜÑ¿¡.,;:!?()[]{}\"'-_ "
    )

    # Contar caracteres latinos vs no latinos
    caracteres_texto = set(texto)
    caracteres_no_latinos = caracteres_texto - caracteres_latinos

    # Si hay más del 20% de caracteres no latinos, probablemente no es español/inglés
    if len(caracteres_no_latinos) > 0:
        porcentaje_no_latinos = len(caracteres_no_latinos) / len(caracteres_texto)
        if porcentaje_no_latinos > 0.2:
            return False

    return True


def validar_idioma_whisper(texto, idioma_detectado):
    """
    Valida que el texto transcrito sea consistente con el idioma detectado por Whisper.
    """
    # Primero verificar que sea texto latino
    if not es_texto_latino(texto):
        return False

    # Mapear idiomas de Whisper a códigos estándar
    whisper_to_code = {
        "spanish": "es",
        "english": "en",
        "german": "de",
        "french": "fr",
        "italian": "it",
        "portuguese": "pt",
    }

    # Obtener el código del idioma
    idioma_codigo = whisper_to_code.get(idioma_detectado, idioma_detectado)

    # En modo auto, solo aceptar español e inglés
    if auto_detect:
        if idioma_codigo not in ["es", "en"]:
            return False
    else:
        # En modo manual, verificar que el idioma detectado sea uno de los configurados
        if idioma_codigo not in [src_lang, tgt_lang]:
            return False

    return True


def detectar_idioma(texto):
    """
    Detecta si el texto está en español o inglés usando patrones básicos.
    """
    # Primero verificar que sea texto latino
    if not es_texto_latino(texto):
        return None  # Retornar None si no es texto latino

    # Palabras comunes en español
    palabras_espanol = [
        "el",
        "la",
        "de",
        "que",
        "y",
        "es",
        "en",
        "un",
        "una",
        "con",
        "por",
        "para",
        "como",
        "mi",
        "tu",
        "hola",
        "gracias",
        "por favor",
        "sí",
        "no",
        "donde",
        "cuando",
        "porque",
        "muy",
        "más",
        "menos",
        "bueno",
        "malo",
        "grande",
        "pequeño",
    ]

    # Palabras comunes en inglés
    palabras_ingles = [
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "hello",
        "hi",
        "thank",
        "you",
        "please",
        "yes",
        "no",
        "where",
        "when",
        "because",
        "very",
        "more",
        "less",
        "good",
        "bad",
        "big",
        "small",
    ]

    texto_lower = texto.lower()
    palabras_texto = re.findall(r"\b\w+\b", texto_lower)

    puntos_espanol = sum(1 for palabra in palabras_texto if palabra in palabras_espanol)
    puntos_ingles = sum(1 for palabra in palabras_texto if palabra in palabras_ingles)

    # También verificar caracteres específicos del español
    if any(char in texto_lower for char in ["ñ", "á", "é", "í", "ó", "ú", "¿", "¡"]):
        puntos_espanol += 2

    if puntos_espanol > puntos_ingles:
        return "es"
    elif puntos_ingles > puntos_espanol:
        return "en"
    else:
        # Si no está claro, intentar detectar por estructura
        if any(
            word in texto_lower
            for word in ["hola", "gracias", "por favor", "buenos días"]
        ):
            return "es"
        elif any(
            word in texto_lower
            for word in ["hello", "thank you", "please", "good morning"]
        ):
            return "en"
        else:
            return "es"  # Por defecto español


def grabar_y_reconocer_con_whisper(max_duration=60):
    """
    Captura audio del micrófono y lo transcribe usando Whisper.
    Optimizado para 16 kHz sample rate y chunk size mejorado.
    """
    # Configure microphone with optimized settings for Whisper
    with sr.Microphone(sample_rate=16000, chunk_size=1024) as source:
        print("\nDi algo en español o inglés...")
        # Ajuste más estricto para el ruido ambiental
        recognizer.adjust_for_ambient_noise(source, duration=1)

        # Configurar umbrales más altos para evitar falsos positivos
        recognizer.energy_threshold = 4000  # Umbral de energía más alto
        recognizer.dynamic_energy_threshold = True
        recognizer.dynamic_energy_adjustment_damping = 0.15
        recognizer.dynamic_energy_ratio = 1.5

        # Escuchar con timeout y tiempo mínimo de frase
        try:
            audio = recognizer.listen(
                source, timeout=max_duration, phrase_time_limit=max_duration
            )
        except sr.WaitTimeoutError:
            print("No se detectó ningún sonido. Intenta de nuevo.")
            return None, None

    # Guardar el audio en un archivo temporal con procesamiento mejorado
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_filename = temp_audio.name
        with open(temp_filename, "wb") as f:
            # Get raw audio data
            audio_data = audio.get_wav_data()

            # Apply audio normalization using RMS for better Whisper recognition
            print("Aplicando normalización de audio...")
            normalized_audio = normalize_audio_rms(audio_data, target_rms=0.2)

            # Apply automatic gain control for consistency across microphones
            print("Aplicando control automático de ganancia...")
            processed_audio = apply_automatic_gain_control(normalized_audio)

            f.write(processed_audio)

    try:
        print("Reconociendo tu voz con Whisper...")

        # Transcribir usando Whisper con procesamiento por segmentos
        result = transcribe_long_audio(whisper_model, temp_filename)
        texto_transcrito = result["text"].strip()
        idioma_detectado = result["language"]

        # Validar que el texto y el idioma sean válidos
        if not validar_idioma_whisper(texto_transcrito, idioma_detectado):
            print(
                f"Se detectó texto en idioma no soportado ({idioma_detectado}) o con caracteres inválidos. Intenta de nuevo."
            )
            return None, None

        # Mapear códigos de idioma de Whisper a nuestros códigos
        whisper_to_code = {
            "spanish": "es",
            "english": "en",
            "german": "de",
            "french": "fr",
            "italian": "it",
            "portuguese": "pt",
        }

        idioma_final = whisper_to_code.get(idioma_detectado, idioma_detectado)

        # Si no se pudo mapear y estamos en auto-detect, usar función de detección
        if auto_detect and idioma_final not in ["es", "en"]:
            idioma_final = detectar_idioma(texto_transcrito)
            if idioma_final is None:
                print("No se pudo determinar el idioma del texto. Intenta de nuevo.")
                return None, None

        # Validar que el texto tenga sentido y no sea demasiado corto
        if len(texto_transcrito) < 2 or len(texto_transcrito.split()) < 1:
            print("Texto demasiado corto o sin contenido. Intenta de nuevo.")
            return None, None

        # Filtrar texto que parece ser solo ruido
        if all(len(palabra) <= 2 for palabra in texto_transcrito.split()):
            print("Texto parece ser ruido. Intenta hablar más claro.")
            return None, None

        print(f"Texto reconocido con Whisper ({idioma_final}): '{texto_transcrito}'")
        return texto_transcrito, idioma_final

    except Exception as e:
        print(f"Error con Whisper: {e}")
        print("Intentando con reconocimiento de Google como fallback...")
        return grabar_y_reconocer_fallback(audio)

    finally:
        # Limpiar el archivo temporal
        try:
            os.unlink(temp_filename)
        except Exception:
            pass


def grabar_y_reconocer_fallback(audio):
    """
    Función de fallback que usa Google Speech Recognition si Whisper falla.
    """
    try:
        print("Usando Google Speech Recognition como fallback...")
        texto_es = recognizer.recognize_google(audio, language="es-ES")  # type: ignore

        # Intentar también en inglés
        try:
            texto_en = recognizer.recognize_google(audio, language="en-US")  # type: ignore

            # Detectar cuál es más probable basado en el contenido
            idioma_detectado_es = detectar_idioma(texto_es)
            idioma_detectado_en = detectar_idioma(texto_en)

            # Verificar si alguno de los idiomas es None (texto no latino)
            if idioma_detectado_es is None and idioma_detectado_en is None:
                print("Texto no reconocido como español o inglés.")
                return None, None
            elif idioma_detectado_es is None:
                texto_final, idioma_final = texto_en, "en"
            elif idioma_detectado_en is None:
                texto_final, idioma_final = texto_es, "es"
            elif idioma_detectado_es == "es" and idioma_detectado_en == "en":
                # Ambos son consistentes, elegir el más largo (más probable)
                if len(texto_es.split()) >= len(texto_en.split()):
                    texto_final, idioma_final = texto_es, "es"
                else:
                    texto_final, idioma_final = texto_en, "en"
            elif idioma_detectado_es == "es":
                texto_final, idioma_final = texto_es, "es"
            else:
                texto_final, idioma_final = texto_en, "en"

        except Exception:
            idioma_fallback = detectar_idioma(texto_es)
            if idioma_fallback is None:
                print("Texto no reconocido como español o inglés.")
                return None, None
            texto_final, idioma_final = texto_es, idioma_fallback

        print(f"Texto reconocido con fallback ({idioma_final}): '{texto_final}'")
        return texto_final, idioma_final

    except sr.UnknownValueError:
        print("Lo siento, no pude entender lo que dijiste.")
        return None, None
    except sr.RequestError as e:
        print(f"Error con el servicio de reconocimiento de voz; {e}")
        return None, None


def traducir_texto(texto_a_traducir, idioma_origen):
    """
    Traduce texto usando LazyModelLoader.
    """
    if not texto_a_traducir:
        return None, None

    print("Traduciendo texto...")
    try:
        # Determinar dirección de traducción
        if auto_detect:
            # En modo auto-detect, usar el idioma detectado para determinar el idioma de destino
            if idioma_origen == "es":
                idioma_destino = "en"
            else:
                idioma_destino = "es"
        else:
            # En modo manual, usar los idiomas especificados por CLI
            if idioma_origen == src_lang:
                idioma_destino = tgt_lang
            else:
                # Si el idioma detectado no coincide con src_lang, intercambiar
                idioma_destino = src_lang

        # Obtener el modelo de traducción usando LazyModelLoader
        translator = model_loader.get_model(idioma_origen, idioma_destino)

        if translator is None:
            print(
                f"No hay modelo disponible para traducir de {idioma_origen} a {idioma_destino}"
            )
            return None, None

        print(f"Traduciendo de {idioma_origen} a {idioma_destino}...")
        resultado = translator(texto_a_traducir)
        texto_traducido = resultado[0]["translation_text"]
        print(f"Texto traducido: '{texto_traducido}'")
        return texto_traducido, idioma_destino

    except Exception as e:
        print(f"Ocurrió un error durante la traducción: {e}")
        return None, None


def hablar_texto(texto_a_hablar, idioma="en"):
    """
    Sintetiza y reproduce texto con la TTS unificada.
    """
    if not texto_a_hablar:
        return

    print("Generando audio...")
    try:
        samples = synthesize_to_numpy(texto_a_hablar, idioma, sample_rate=44100)
        if samples.size == 0:
            print("TTS no generó muestras.")
            return
        sd.play(samples, samplerate=44100)
        sd.wait()
    except Exception as e:
        print(f"Ocurrió un error al reproducir el audio: {e}")


def parse_cli_args():
    """
    Parse command line arguments for the translator.
    """
    parser = argparse.ArgumentParser(
        description="Traductor IA Personal con Whisper y LazyModelLoader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detection mode (default)
  python main_whisper.py --auto

  # Specific language pair
  python main_whisper.py --src_lang es --tgt_lang en

  # With preloading
  python main_whisper.py --src_lang en --tgt_lang es --preload

  # Preload models for multiple languages
  python main_whisper.py --auto --preload
  """,
    )

    # Language configuration
    lang_group = parser.add_mutually_exclusive_group(required=False)
    lang_group.add_argument(
        "--auto",
        action="store_true",
        default=True,
        help="Auto-detect language mode (default). Supports es<->en translation.",
    )

    lang_group.add_argument(
        "--src_lang", type=str, help="Source language code (e.g., es, en, de, fr)"
    )

    parser.add_argument(
        "--tgt_lang",
        type=str,
        help="Target language code (e.g., es, en, de, fr). Required when --src_lang is specified.",
    )

    # Model configuration
    parser.add_argument(
        "--whisper_model",
        type=str,
        default="base",
        choices=["base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )

    parser.add_argument(
        "--cache_dir",
        type=str,
        default="./model_cache",
        help="Directory to cache models (default: ./model_cache)",
    )

    # Preloading options
    parser.add_argument(
        "--preload", action="store_true", help="Preload translation models at startup"
    )

    parser.add_argument(
        "--preload_languages",
        type=str,
        nargs="*",
        default=["es", "en"],
        help="Languages to preload models for (default: es en)",
    )

    parser.add_argument(
        "--max_duration",
        type=int,
        default=60,
        help="Maximum recording duration in seconds (default: 60)",
    )

    # Silence detection parameters
    parser.add_argument(
        "--silence-detection",
        action="store_true",
        help="Enable silence detection for auto-stopping transcription",
    )

    parser.add_argument(
        "--silence-preset",
        type=str,
        default="balanced",
        choices=["sensitive", "balanced", "aggressive", "very_aggressive"],
        help="Silence detection preset (default: balanced)",
    )

    parser.add_argument(
        "--min-silence-len",
        type=int,
        default=800,
        help="Minimum silence duration in ms to trigger auto-stop (default: 800)",
    )

    parser.add_argument(
        "--silence-thresh",
        type=int,
        default=-40,
        help="Silence threshold in dBFS (default: -40)",
    )

    parser.add_argument(
        "--silence-method",
        type=str,
        default="auto",
        choices=["auto", "webrtcvad", "pydub"],
        help="Silence detection method (default: auto)",
    )

    parser.add_argument(
        "--vad-aggressiveness",
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help="WebRTC VAD aggressiveness level (0-3, default: 2)",
    )

    args = parser.parse_args()

    # Validation
    if args.src_lang and not args.tgt_lang:
        parser.error("--tgt_lang is required when --src_lang is specified")

    if args.tgt_lang and not args.src_lang:
        parser.error("--src_lang is required when --tgt_lang is specified")

    # If src_lang and tgt_lang are specified, disable auto mode
    if args.src_lang and args.tgt_lang:
        args.auto = False

    return args


def init_models(args):
    """
    Initialize models based on CLI arguments.
    """
    global \
        model_loader, \
        whisper_model, \
        src_lang, \
        tgt_lang, \
        auto_detect, \
        silence_detector, \
        silence_integration

    # Set global variables
    src_lang = args.src_lang
    tgt_lang = args.tgt_lang
    auto_detect = args.auto

    # Initialize LazyModelLoader
    print("Initializing LazyModelLoader...")
    model_loader = LazyModelLoader(cache_dir=args.cache_dir)

    # Progress callback for model loading with timing
    model_start_times = {}

    def progress_callback(message, progress):
        # Track timing for concise logging
        if progress == 0.0:
            # Starting to load
            model_start_times[message] = time.time()
            print(f"Loading {message}...", end="", flush=True)
        elif progress == 100.0:
            # Finished loading
            if message in model_start_times:
                elapsed = time.time() - model_start_times[message]
                print(f"done ({elapsed:.1f} s)")
                del model_start_times[message]
            else:
                print(f"[{progress:.1f}%] {message}")
        # Don't print intermediate progress for cleaner output

    model_loader.set_progress_callback(progress_callback)

    # Initialize Whisper model
    print(f"Loading Whisper model ({args.whisper_model})...", end="", flush=True)
    start_time = time.time()
    whisper_model = model_loader.get_whisper_model(args.whisper_model)

    if whisper_model is None:
        print("error")
        print(f"Error: Could not load Whisper model {args.whisper_model}")
        sys.exit(1)
    else:
        elapsed = time.time() - start_time
        print(f"done ({elapsed:.1f} s)")

    # Preload translation models if requested
    if args.preload:
        print("Preloading translation models...")
        if auto_detect:
            # In auto mode, preload models for specified languages
            results = model_loader.load_all_for_languages(args.preload_languages)

            # Print summary
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            print(f"Preloaded {success_count}/{total_count} translation models")

            if success_count < total_count:
                failed_models = [
                    pair for pair, success in results.items() if not success
                ]
                print(f"Failed to load: {', '.join(failed_models)}")
        else:
            # In manual mode, preload specific model
            print(f"Loading model {src_lang}→{tgt_lang}...", end="", flush=True)
            start_time = time.time()
            model = model_loader.get_model(src_lang, tgt_lang)

            if model:
                elapsed = time.time() - start_time
                print(f"done ({elapsed:.1f} s)")
            else:
                print("error")
                print(f"Warning: Could not preload model {src_lang}→{tgt_lang}")

    # Initialize silence detector if enabled
    if args.silence_detection:
        print("Inicializando detector de silencio...")
        try:
            # Create silence detector with CLI parameters
            silence_detector = create_silence_detector(
                preset=args.silence_preset,
                min_silence_len=args.min_silence_len,
                silence_thresh=args.silence_thresh,
                method=args.silence_method,
                aggressiveness=args.vad_aggressiveness,
            )

            # Create integration helper
            silence_integration = SilenceDetectorIntegration(
                recognizer, silence_detector
            )

            print(
                f"Detector de silencio inicializado: {silence_detector.active_method}"
            )
            print(
                f"Configuración: min_silence_len={args.min_silence_len}ms, threshold={args.silence_thresh}dBFS"
            )
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar el detector de silencio: {e}")
            print("Continuando sin detección de silencio...")
            silence_detector = None
            silence_integration = None
    else:
        print("Detección de silencio deshabilitada")

    print("Inicialización completada.")

    # Print configuration summary
    print("\n=== CONFIGURACIÓN ===")
    if auto_detect:
        print("Modo: Auto-detección de idioma")
        print(f"Idiomas soportados: {', '.join(args.preload_languages)}")
    else:
        print(f"Modo: Traducción específica {src_lang} -> {tgt_lang}")

    print(f"Modelo Whisper: {args.whisper_model}")
    print(f"Directorio de cache: {args.cache_dir}")
    print(f"Precarga activada: {'Sí' if args.preload else 'No'}")

    # Show silence detection configuration
    if args.silence_detection and silence_detector:
        print("\nDetección de silencio: ACTIVADA")
        print(f"Método: {silence_detector.active_method}")
        print(f"Preset: {args.silence_preset}")
        print(f"Umbral mínimo de silencio: {args.min_silence_len}ms")
        print(f"Umbral de nivel de audio: {args.silence_thresh}dBFS")
        if silence_detector.active_method == "webrtcvad":
            print(f"Agresividad VAD: {args.vad_aggressiveness}")
    else:
        print("\nDetección de silencio: DESACTIVADA")

    # Show available language pairs
    pairs = model_loader.get_supported_language_pairs()
    print(f"\nPares de idiomas disponibles ({len(pairs)}):")
    for i, (src, tgt) in enumerate(pairs):
        print(f"  {src} -> {tgt}", end="")
        if (i + 1) % 4 == 0:
            print()  # New line every 4 pairs
    if len(pairs) % 4 != 0:
        print()  # Final newline if needed

    print("========================\n")


# --- 3. BUCLE PRINCIPAL DE EJECUCIÓN ---

if __name__ == "__main__":
    print("=== Traductor IA Personal con Whisper ===")
    print(
        "Versión mejorada con reconocimiento de voz offline usando Whisper y LazyModelLoader"
    )

    # Parse command line arguments
    args = parse_cli_args()

    # Initialize models
    init_models(args)

    # Start main loop
    if auto_detect:
        print(
            "Habla en cualquier idioma soportado y el programa lo traducirá automáticamente."
        )
    else:
        print(f"Habla en {src_lang} y será traducido a {tgt_lang}.")

    print("Presiona Ctrl+C para salir.")

    try:
        while True:
            # Paso 1: Escuchar y transcribir con Whisper
            texto_original, idioma_origen = grabar_y_reconocer_con_whisper(
                args.max_duration
            )

            if texto_original is None:
                continue

            # Paso 2: Traducir el texto
            texto_traducido, idioma_destino = traducir_texto(
                texto_original, idioma_origen
            )

            if texto_traducido is None:
                continue

            # Paso 3: Hablar la traducción
            hablar_texto(texto_traducido, idioma_destino)

    except KeyboardInterrupt:
        print("\n¡Adiós! Saliendo del programa.")
    finally:
        if model_loader:
            model_loader.shutdown()
