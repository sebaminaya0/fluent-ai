import speech_recognition as sr
import whisper
from transformers.pipelines import pipeline
from gtts import gTTS
import os
import pygame
import time
import re
import tempfile
import numpy as np

# --- 1. CONFIGURACIÓN INICIAL ---

# Inicializar Pygame para el audio
pygame.init()
pygame.mixer.init()

# Inicializar el reconocedor de voz (como fallback)
recognizer = sr.Recognizer()

# Cargar el modelo Whisper
print("Cargando modelo Whisper... Esto puede tardar un momento.")
whisper_model = whisper.load_model("base")  # Puedes usar "tiny", "base", "small", "medium", "large"
print("Modelo Whisper cargado exitosamente.")

# Suprimir warnings de Whisper
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")

# Cargar los pipelines de traducción de Hugging Face
print("Cargando modelos de traducción...")
translator_es_en = pipeline("translation", model="Helsinki-NLP/opus-mt-es-en")
translator_en_es = pipeline("translation", model="Helsinki-NLP/opus-mt-en-es")
print("Modelos de traducción cargados exitosamente.")


# --- 2. DEFINICIÓN DE FUNCIONES ---

def es_texto_latino(texto):
    """
    Verifica si el texto contiene principalmente caracteres latinos (español/inglés).
    Retorna False si detecta caracteres de otros alfabetos como griego, cirílico, etc.
    """
    # Caracteres latinos básicos + acentos españoles + signos de puntuación
    caracteres_latinos = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                           'áéíóúüñÁÉÍÓÚÜÑ¿¡.,;:!?()[]{}"\'-_ ')
    
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
    
    # Verificar que el idioma detectado sea español o inglés
    if idioma_detectado not in ['spanish', 'english', 'es', 'en']:
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
    palabras_espanol = ['el', 'la', 'de', 'que', 'y', 'es', 'en', 'un', 'una', 'con', 'por', 'para', 'como', 'mi', 'tu', 'hola', 'gracias', 'por favor', 'sí', 'no', 'donde', 'cuando', 'porque', 'muy', 'más', 'menos', 'bueno', 'malo', 'grande', 'pequeño']
    
    # Palabras comunes en inglés
    palabras_ingles = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'hello', 'hi', 'thank', 'you', 'please', 'yes', 'no', 'where', 'when', 'because', 'very', 'more', 'less', 'good', 'bad', 'big', 'small']
    
    texto_lower = texto.lower()
    palabras_texto = re.findall(r'\b\w+\b', texto_lower)
    
    puntos_espanol = sum(1 for palabra in palabras_texto if palabra in palabras_espanol)
    puntos_ingles = sum(1 for palabra in palabras_texto if palabra in palabras_ingles)
    
    # También verificar caracteres específicos del español
    if any(char in texto_lower for char in ['ñ', 'á', 'é', 'í', 'ó', 'ú', '¿', '¡']):
        puntos_espanol += 2
    
    if puntos_espanol > puntos_ingles:
        return 'es'
    elif puntos_ingles > puntos_espanol:
        return 'en'
    else:
        # Si no está claro, intentar detectar por estructura
        if any(word in texto_lower for word in ['hola', 'gracias', 'por favor', 'buenos días']):
            return 'es'
        elif any(word in texto_lower for word in ['hello', 'thank you', 'please', 'good morning']):
            return 'en'
        else:
            return 'es'  # Por defecto español

def grabar_y_reconocer_con_whisper():
    """
    Captura audio del micrófono y lo transcribe usando Whisper.
    """
    with sr.Microphone() as source:
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
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            print("No se detectó ningún sonido. Intenta de nuevo.")
            return None, None

    # Guardar el audio en un archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_filename = temp_audio.name
        with open(temp_filename, "wb") as f:
            f.write(audio.get_wav_data())
    
    try:
        print("Reconociendo tu voz con Whisper...")
        
        # Transcribir usando Whisper
        result = whisper_model.transcribe(temp_filename)
        texto_transcrito = result["text"].strip()
        idioma_detectado = result["language"]
        
        # Validar que el texto y el idioma sean válidos
        if not validar_idioma_whisper(texto_transcrito, idioma_detectado):
            print(f"Se detectó texto en idioma no soportado ({idioma_detectado}) o con caracteres inválidos. Intenta de nuevo.")
            return None, None
        
        # Mapear códigos de idioma de Whisper a nuestros códigos
        if idioma_detectado == "spanish":
            idioma_final = "es"
        elif idioma_detectado == "english":
            idioma_final = "en"
        else:
            # Si Whisper detecta otro idioma, usar nuestra función de detección
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
        except:
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
                texto_final, idioma_final = texto_en, 'en'
            elif idioma_detectado_en is None:
                texto_final, idioma_final = texto_es, 'es'
            elif idioma_detectado_es == 'es' and idioma_detectado_en == 'en':
                # Ambos son consistentes, elegir el más largo (más probable)
                if len(texto_es.split()) >= len(texto_en.split()):
                    texto_final, idioma_final = texto_es, 'es'
                else:
                    texto_final, idioma_final = texto_en, 'en'
            elif idioma_detectado_es == 'es':
                texto_final, idioma_final = texto_es, 'es'
            else:
                texto_final, idioma_final = texto_en, 'en'
                
        except:
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
    Traduce texto entre español e inglés usando Helsinki-NLP.
    """
    if not texto_a_traducir:
        return None, None
    
    print("Traduciendo texto...")
    try:
        # Determinar dirección de traducción
        if idioma_origen == 'es':
            print(f"Traduciendo de español a inglés...")
            resultado = translator_es_en(texto_a_traducir)
            idioma_destino = 'en'
        else:
            print(f"Traduciendo de inglés a español...")
            resultado = translator_en_es(texto_a_traducir)
            idioma_destino = 'es'
        
        texto_traducido = resultado[0]['translation_text']
        print(f"Texto traducido: '{texto_traducido}'")
        return texto_traducido, idioma_destino
        
    except Exception as e:
        print(f"Ocurrió un error durante la traducción: {e}")
        return None, None

def hablar_texto(texto_a_hablar, idioma='en'):
    """
    Convierte el texto proporcionado a un archivo de audio y lo reproduce usando Pygame.
    """
    if not texto_a_hablar:
        return

    print("Generando audio...")
    try:
        tts = gTTS(text=texto_a_hablar, lang=idioma, slow=False)
        nombre_archivo = "traduccion.mp3"
        tts.save(nombre_archivo)

        print("Reproduciendo traducción...")
        pygame.mixer.music.load(nombre_archivo)
        pygame.mixer.music.play()

        # Esperar a que la música termine de reproducirse
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Pygame puede bloquear el archivo, así que lo descargamos y esperamos un poco
        pygame.mixer.music.unload()
        time.sleep(0.5)

        os.remove(nombre_archivo) # Limpiar el archivo de audio después de reproducirlo
    except Exception as e:
        print(f"Ocurrió un error al generar o reproducir el audio: {e}")


# --- 3. BUCLE PRINCIPAL DE EJECUCIÓN ---

if __name__ == "__main__":
    print("=== Traductor IA Personal con Whisper ===")
    print("Versión mejorada con reconocimiento de voz offline usando Whisper")
    print("Habla en español o inglés y el programa lo traducirá automáticamente.")
    print("Español → Inglés  |  Inglés → Español")
    print("Presiona Ctrl+C para salir.")

    try:
        while True:
            # Paso 1: Escuchar y transcribir con Whisper
            texto_original, idioma_origen = grabar_y_reconocer_con_whisper()
            
            if texto_original is None:
                continue

            # Paso 2: Traducir el texto
            texto_traducido, idioma_destino = traducir_texto(texto_original, idioma_origen)
            
            if texto_traducido is None:
                continue
            
            # Paso 3: Hablar la traducción
            hablar_texto(texto_traducido, idioma_destino)

    except KeyboardInterrupt:
        print("\n¡Adiós! Saliendo del programa.")
    finally:
        pygame.quit() # Limpiar pygame al salir
