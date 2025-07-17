import speech_recognition as sr
from transformers.pipelines import pipeline
from gtts import gTTS
import os
import pygame
import time
import re

# --- 1. CONFIGURACIÓN INICIAL ---

# Inicializar Pygame para el audio
pygame.init()
pygame.mixer.init()

# Inicializar el reconocedor de voz
recognizer = sr.Recognizer()

# Cargar los pipelines de traducción de Hugging Face
# Usando Helsinki-NLP que funciona bien con sentencepiece
print("Cargando modelos de traducción... Esto puede tardar un momento.")
translator_es_en = pipeline("translation", model="Helsinki-NLP/opus-mt-es-en")
translator_en_es = pipeline("translation", model="Helsinki-NLP/opus-mt-en-es")
print("Modelos cargados exitosamente.")


# --- 2. DEFINICIÓN DE FUNCIONES ---

def detectar_idioma(texto):
    """
    Detecta si el texto está en español o inglés usando patrones básicos.
    """
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

def grabar_y_reconocer_voz():
    """
    Captura audio del micrófono, intenta reconocerlo en ambos idiomas y devuelve
    el texto junto con el idioma detectado.
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

    # Intentar reconocimiento en español primero
    try:
        print("Reconociendo tu voz...")
        texto_es = recognizer.recognize_google(audio, language="es-ES")  # type: ignore
        
        # Intentar también en inglés
        try:
            texto_en = recognizer.recognize_google(audio, language="en-US")  # type: ignore
            
            # Detectar cuál es más probable basado en el contenido
            idioma_detectado_es = detectar_idioma(texto_es)
            idioma_detectado_en = detectar_idioma(texto_en)
            
            if idioma_detectado_es == 'es' and idioma_detectado_en == 'en':
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
            texto_final, idioma_final = texto_es, detectar_idioma(texto_es)
            
        # Validar que el texto tenga sentido y no sea demasiado corto
        if len(texto_final.strip()) < 2 or len(texto_final.split()) < 1:
            print("Texto demasiado corto o sin contenido. Intenta de nuevo.")
            return None, None
            
        # Filtrar texto que parece ser solo ruido
        if all(len(palabra) <= 2 for palabra in texto_final.split()):
            print("Texto parece ser ruido. Intenta hablar más claro.")
            return None, None
        
        print(f"Texto reconocido ({idioma_final}): '{texto_final}'")
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
    print("=== Traductor IA Personal Bidireccional ===")
    print("Habla en español o inglés y el programa lo traducirá automáticamente.")
    print("Español → Inglés  |  Inglés → Español")
    print("Presiona Ctrl+C para salir.")

    try:
        while True:
            # Paso 1: Escuchar y transcribir con detección de idioma
            texto_original, idioma_origen = grabar_y_reconocer_voz()
            
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
