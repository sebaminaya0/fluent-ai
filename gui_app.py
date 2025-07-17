import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import speech_recognition as sr
import whisper
from transformers.pipelines import pipeline
from gtts import gTTS
import os
import pygame
import time
import re
import tempfile
import warnings
import numpy as np
from fluentai.model_loader import LazyModelLoader
from silence_detector import SilenceDetector, SilenceDetectorIntegration, create_silence_detector

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="librosa")

class FluentAIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🌍 Fluent AI - Bidirectional Translator")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Variables de estado
        self.is_recording = False
        self.is_models_loaded = False
        self.models_loading = False
        self.current_text = ""
        self.current_translation = ""
        self.is_listening = False
        self.is_processing = False
        self.microphone_level = 0.0
        self.current_model_status = "No model loaded"
        
        # Cola para comunicación entre hilos
        self.message_queue = queue.Queue()
        
        # Inicializar componentes de audio
        pygame.init()
        pygame.mixer.init()
        
        # Configurar reconocedor de voz para capturar frases más largas
        self.recognizer = sr.Recognizer()
        # Reducir el umbral de energía para ser más sensible a voz baja
        self.recognizer.energy_threshold = 300  # Mucho más bajo que 4000
        # Desactivar el ajuste dinámico de energía para evitar cortes prematuros
        self.recognizer.dynamic_energy_threshold = False
        # Configurar para ser más tolerante con pausas y silencios
        self.recognizer.pause_threshold = 2.0  # Esperar 2 segundos de silencio antes de considerar fin
        self.recognizer.operation_timeout = None  # Sin timeout de operación
        self.recognizer.non_speaking_duration = 2.0  # Duración de no-habla antes de parar
        
        # Suprimir warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
        
        # Initialize LazyModelLoader
        self.model_loader = LazyModelLoader(cache_dir="./model_cache", max_cache_size=10)
        self.model_loader.set_progress_callback(self._on_model_progress)
        
        # Cache for current models
        self.current_whisper_model = None
        self.current_translator = None
        
        # Variable para selección de dirección de traducción
        self.translation_direction = tk.StringVar(value='es->en')
        
        # Variables para detección de silencio
        self.silence_detection_enabled = tk.BooleanVar(value=False)
        self.silence_preset = tk.StringVar(value='balanced')
        self.min_silence_len = tk.IntVar(value=800)
        self.silence_thresh = tk.IntVar(value=-40)
        
        # Detector de silencio
        self.silence_detector = None
        self.silence_integration = None
        
        # Crear la interfaz
        self.create_ui()
        
        # Iniciar el monitoreo de la cola de mensajes
        self.check_message_queue()
        
        # Iniciar simulación de nivel de micrófono
        self.simulate_microphone_level()
        
    def create_ui(self):
        # Título principal
        title_frame = tk.Frame(self.root, bg='#f0f0f0')
        title_frame.pack(pady=20)
        
        title_label = tk.Label(title_frame, text="🌍 Fluent AI Translator", 
                              font=('Arial', 24, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Español • English • Deutsch • Français", 
                                 font=('Arial', 14), bg='#f0f0f0', fg='#7f8c8d')
        subtitle_label.pack()
        
        # Frame para selección de dirección de traducción
        direction_frame = tk.Frame(self.root, bg='#f0f0f0')
        direction_frame.pack(pady=10)
        
        tk.Label(direction_frame, text="Dirección de traducción:", 
                font=('Arial', 14, 'bold'), bg='#f0f0f0', fg='#2c3e50').pack()
        
        # Mapeo de direcciones de traducción
        self.translation_directions = {
            'es->en': '🇪🇸 Español → 🇺🇸 English',
            'en->es': '🇺🇸 English → 🇪🇸 Español',
            'es->de': '🇪🇸 Español → 🇩🇪 Deutsch',
            'de->es': '🇩🇪 Deutsch → 🇪🇸 Español',
            'es->fr': '🇪🇸 Español → 🇫🇷 Français',
            'fr->es': '🇫🇷 Français → 🇪🇸 Español',
            'en->de': '🇺🇸 English → 🇩🇪 Deutsch',
            'de->en': '🇩🇪 Deutsch → 🇺🇸 English',
            'en->fr': '🇺🇸 English → 🇫🇷 Français',
            'fr->en': '🇫🇷 Français → 🇺🇸 English'
        }
        
        # Selector de dirección de traducción
        self.direction_combo = ttk.Combobox(direction_frame, 
                                          textvariable=self.translation_direction,
                                          values=list(self.translation_directions.values()),
                                          state='readonly', width=35, font=('Arial', 12))
        self.direction_combo.pack(pady=10)
        self.direction_combo.set(self.translation_directions['es->en'])
        
        # Vincular evento para cargar modelo necesario
        self.direction_combo.bind('<<ComboboxSelected>>', self.on_direction_change)
        
        # Frame para configuración de detección de silencio
        silence_frame = tk.Frame(self.root, bg='#f0f0f0')
        silence_frame.pack(pady=10)
        
        # Checkbox para habilitar detección de silencio
        self.silence_checkbox = tk.Checkbutton(silence_frame, 
                                              text="🔇 Detección de silencio automática",
                                              variable=self.silence_detection_enabled,
                                              command=self.toggle_silence_detection,
                                              font=('Arial', 11, 'bold'),
                                              bg='#f0f0f0', fg='#2c3e50')
        self.silence_checkbox.pack()
        
        # Frame para controles de silencio (inicialmente oculto)
        self.silence_controls_frame = tk.Frame(silence_frame, bg='#f0f0f0')
        
        # Preset selector
        preset_frame = tk.Frame(self.silence_controls_frame, bg='#f0f0f0')
        preset_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(preset_frame, text="Preset:", 
                font=('Arial', 10), bg='#f0f0f0', fg='#2c3e50').pack()
        
        self.preset_combo = ttk.Combobox(preset_frame, 
                                        textvariable=self.silence_preset,
                                        values=['sensitive', 'balanced', 'aggressive', 'very_aggressive'],
                                        state='readonly', width=12)
        self.preset_combo.pack(pady=2)
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_silence_preset_change)
        
        # Silence length slider
        length_frame = tk.Frame(self.silence_controls_frame, bg='#f0f0f0')
        length_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(length_frame, text="Duración silencio (ms):", 
                font=('Arial', 10), bg='#f0f0f0', fg='#2c3e50').pack()
        
        self.silence_length_scale = tk.Scale(length_frame, 
                                           from_=200, to=2000, 
                                           orient=tk.HORIZONTAL,
                                           variable=self.min_silence_len,
                                           command=self.on_silence_param_change,
                                           bg='#f0f0f0', fg='#2c3e50',
                                           length=100)
        self.silence_length_scale.pack(pady=2)
        
        # Silence threshold slider
        thresh_frame = tk.Frame(self.silence_controls_frame, bg='#f0f0f0')
        thresh_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(thresh_frame, text="Umbral silencio (dBFS):", 
                font=('Arial', 10), bg='#f0f0f0', fg='#2c3e50').pack()
        
        self.silence_thresh_scale = tk.Scale(thresh_frame, 
                                           from_=-60, to=-20, 
                                           orient=tk.HORIZONTAL,
                                           variable=self.silence_thresh,
                                           command=self.on_silence_param_change,
                                           bg='#f0f0f0', fg='#2c3e50',
                                           length=100)
        self.silence_thresh_scale.pack(pady=2)
        
        # Frame para los botones de control
        control_frame = tk.Frame(self.root, bg='#f0f0f0')
        control_frame.pack(pady=20)
        
        # Botón para cargar modelos (inicialmente habilitado)
        self.load_models_btn = tk.Button(control_frame, text="🔄 Cargar Whisper", 
                                        command=self.load_whisper_model,
                                        font=('Arial', 12, 'bold'),
                                        bg='#3498db', fg='white', 
                                        padx=20, pady=10)
        self.load_models_btn.pack(side=tk.LEFT, padx=10)
        
        # Botón para grabar
        self.record_btn = tk.Button(control_frame, text="🎤 Hablar", 
                                   command=self.toggle_recording,
                                   font=('Arial', 12, 'bold'),
                                   bg='#2ecc71', fg='white', 
                                   padx=20, pady=10,
                                   state=tk.NORMAL)
        self.record_btn.pack(side=tk.LEFT, padx=10)
        
        # Botón para reproducir traducción
        self.play_btn = tk.Button(control_frame, text="🔊 Reproducir", 
                                 command=self.play_translation,
                                 font=('Arial', 12, 'bold'),
                                 bg='#e74c3c', fg='white', 
                                 padx=20, pady=10,
                                 state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, padx=10)
        
        # Frame para el contenido principal
        content_frame = tk.Frame(self.root, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Panel izquierdo - Texto original
        left_panel = tk.Frame(content_frame, bg='#f0f0f0')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(left_panel, text="📝 Texto Original", 
                font=('Arial', 14, 'bold'), bg='#f0f0f0', fg='#2c3e50').pack(anchor=tk.W)
        
        self.original_text = scrolledtext.ScrolledText(left_panel, 
                                                      wrap=tk.WORD, 
                                                      font=('Arial', 12),
                                                      height=8,
                                                      bg='#ffffff',
                                                      fg='#2c3e50')
        self.original_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Panel derecho - Texto traducido
        right_panel = tk.Frame(content_frame, bg='#f0f0f0')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(right_panel, text="🔄 Traducción", 
                font=('Arial', 14, 'bold'), bg='#f0f0f0', fg='#2c3e50').pack(anchor=tk.W)
        
        self.translated_text = scrolledtext.ScrolledText(right_panel, 
                                                        wrap=tk.WORD, 
                                                        font=('Arial', 12),
                                                        height=8,
                                                        bg='#ffffff',
                                                        fg='#2c3e50')
        self.translated_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Barra de estado con múltiples componentes
        self.status_frame = tk.Frame(self.root, bg='#34495e')
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Frame superior para indicadores de estado
        self.status_upper_frame = tk.Frame(self.status_frame, bg='#34495e')
        self.status_upper_frame.pack(fill=tk.X, pady=2)
        
        # Frame izquierdo para el medidor de micrófono
        self.mic_frame = tk.Frame(self.status_upper_frame, bg='#34495e')
        self.mic_frame.pack(side=tk.LEFT, padx=10)
        
        # Etiqueta del medidor de micrófono
        self.mic_label = tk.Label(self.mic_frame, text="🎤", 
                                 font=('Arial', 12), bg='#34495e', fg='white')
        self.mic_label.pack(side=tk.LEFT)
        
        # Barra de nivel de micrófono
        self.mic_level_canvas = tk.Canvas(self.mic_frame, width=100, height=8, 
                                        bg='#2c3e50', highlightthickness=0)
        self.mic_level_canvas.pack(side=tk.LEFT, padx=5)
        
        # Indicador de escucha/procesamiento
        self.listening_indicator = tk.Label(self.status_upper_frame, 
                                          text="", font=('Arial', 10, 'bold'), 
                                          bg='#34495e', fg='yellow')
        self.listening_indicator.pack(side=tk.RIGHT, padx=10)
        
        # Frame central para el estado del modelo
        self.model_status_frame = tk.Frame(self.status_upper_frame, bg='#34495e')
        self.model_status_frame.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)
        
        self.model_status_label = tk.Label(self.model_status_frame, 
                                          text="📋 Model Status: Not loaded", 
                                          font=('Arial', 9), bg='#34495e', fg='#95a5a6')
        self.model_status_label.pack()
        
        # Frame inferior para el estado general
        self.status_lower_frame = tk.Frame(self.status_frame, bg='#34495e')
        self.status_lower_frame.pack(fill=tk.X, pady=2)
        
        self.status_label = tk.Label(self.status_lower_frame, text="🟡 Listo para usar (modelos se cargan automáticamente)", 
                                    font=('Arial', 10), bg='#34495e', fg='white')
        self.status_label.pack(pady=2)
        
        # Progress bar para carga de modelos
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.status_lower_frame, variable=self.progress_var, 
                                           maximum=100, length=300)
        
        # Spinner para mostrar carga de modelos
        self.spinner_label = tk.Label(self.status_lower_frame, text="", 
                                    font=('Arial', 10), bg='#34495e', fg='yellow')
        self.spinner_active = False
        self.spinner_chars = ['◐', '◓', '◑', '◒']
        self.spinner_index = 0
        
        # Inicializar la actualización del medidor de micrófono
        self.update_mic_level_display()
        
    def get_direction_from_display(self, display_text):
        """Convierte el texto de display a la clave de dirección"""
        for key, value in self.translation_directions.items():
            if value == display_text:
                return key
        return 'es->en'  # Default
    
    def get_source_and_target_from_direction(self, direction=None):
        """Obtiene idioma origen y destino desde la dirección seleccionada"""
        if direction is None:
            direction = self.get_direction_from_display(self.direction_combo.get())
        
        if '->' in direction:
            src, tgt = direction.split('->')
            return src, tgt
        return 'es', 'en'  # Default
    
    def on_direction_change(self, event=None):
        """Maneja el cambio de dirección de traducción"""
        direction = self.get_direction_from_display(self.direction_combo.get())
        src_lang, tgt_lang = self.get_source_and_target_from_direction(direction)
        
        # Cargar solo el modelo necesario
        self.load_specific_model(src_lang, tgt_lang)
        
        # Actualizar status
        self.update_status(f"📋 Dirección seleccionada: {self.translation_directions[direction]}", "lightblue")
        
        
    def update_status(self, message, color='white'):
        """Actualiza la barra de estado"""
        self.status_label.config(text=message, fg=color)
        self.root.update_idletasks()
        
    def show_progress(self, show=True):
        """Muestra u oculta la barra de progreso"""
        if show:
            self.progress_bar.pack(pady=5)
        else:
            self.progress_bar.pack_forget()
            
            
    def toggle_recording(self):
        """Inicia o detiene la grabación"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def start_recording(self):
        """Inicia la grabación"""
        self.is_recording = True
        self.record_btn.config(text="🛑 Detener", bg='#e74c3c')
        
        # Activar indicador de escucha
        self.update_listening_indicator("listening")
        
        # Mostrar idioma seleccionado en el estado
        src_lang, tgt_lang = self.get_source_and_target_from_direction()
        self.update_status(f"🎤 Escuchando... Habla en {src_lang.upper()}", "yellow")
        
        # Limpiar textos anteriores
        self.original_text.delete(1.0, tk.END)
        self.translated_text.delete(1.0, tk.END)
        
        # Iniciar grabación en hilo separado
        thread = threading.Thread(target=self.record_and_process)
        thread.daemon = True
        thread.start()
        
    def stop_recording(self):
        """Detiene la grabación"""
        self.is_recording = False
        self.record_btn.config(text="🎤 Hablar", bg='#2ecc71')
        self.update_status("⏹️ Grabación detenida", "white")
        
        # Desactivar indicador de escucha
        self.update_listening_indicator("idle")
        
    def record_and_process(self):
        """Graba audio y procesa la traducción"""
        try:
            # Configure microphone with optimized settings for Whisper (16 kHz, 1024 chunk size)
            with sr.Microphone(sample_rate=16000, chunk_size=1024) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Escuchar audio con tiempo extendido para capturar oraciones completas (3 minutos)
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=None)
                
            if not self.is_recording:
                return
                
            # Cambiar a indicador de procesamiento
            self.message_queue.put(("listening_indicator", "processing"))
            
            # Obtener idiomas de la dirección seleccionada
            src_lang, tgt_lang = self.get_source_and_target_from_direction()
            
            self.message_queue.put(("status", f"🔍 Procesando con Whisper ({src_lang})...", "orange"))
            
            # Procesar con Whisper usando el idioma de origen específico
            texto_transcrito, idioma_detectado = self.process_with_whisper(audio, src_lang)
            
            if texto_transcrito:
                self.message_queue.put(("original_text", texto_transcrito))
                
                # Usar los idiomas de la dirección seleccionada directamente
                idioma_origen = src_lang
                idioma_destino = tgt_lang
                
                print(f"Usando dirección seleccionada: {idioma_origen} → {idioma_destino}")
                
                self.message_queue.put(("status", f"🔄 Traduciendo {idioma_origen}→{idioma_destino}...", "orange"))
                
                # Traducir
                texto_traducido = self.translate_text(texto_transcrito, idioma_origen, idioma_destino)
                
                if texto_traducido:
                    self.current_translation = texto_traducido
                    self.message_queue.put(("translated_text", texto_traducido))
                    self.message_queue.put(("status", "✅ Traducción completada", "lightgreen"))
                    self.message_queue.put(("enable_play", True))
                else:
                    self.message_queue.put(("status", "❌ Error en la traducción", "red"))
            else:
                self.message_queue.put(("status", "❌ No se pudo procesar el audio", "red"))
                
        except sr.WaitTimeoutError:
            self.message_queue.put(("status", "⏱️ Tiempo de espera agotado", "orange"))
        except Exception as e:
            self.message_queue.put(("status", f"❌ Error: {str(e)}", "red"))
        finally:
            self.is_recording = False
            self.message_queue.put(("reset_record_btn", True))
            self.message_queue.put(("listening_indicator", "idle"))
            
    def normalize_audio_rms(self, audio_data, target_rms=0.2):
        """
        Normalize audio volume using RMS (Root Mean Square) for better Whisper recognition.
        
        Args:
            audio_data: Audio data as bytes
            target_rms: Target RMS level (0.0 to 1.0)
        
        Returns:
            Normalized audio data as bytes
        """
        try:
            # Convert bytes to numpy array (assuming 16-bit PCM)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate current RMS
            current_rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
            
            if current_rms > 0:
                # Calculate scaling factor
                scale = (target_rms * 32767) / current_rms
                
                # Apply scaling and clip to prevent overflow
                normalized = np.clip(audio_array * scale, -32767, 32767)
                
                # Convert back to bytes
                return normalized.astype(np.int16).tobytes()
            else:
                return audio_data
                
        except Exception as e:
            print(f"Warning: Audio normalization failed: {e}")
            return audio_data
    
    def apply_automatic_gain_control(self, audio_data):
        """
        Apply basic automatic gain control to improve consistency across microphones.
        
        Args:
            audio_data: Audio data as bytes
        
        Returns:
            Audio data with AGC applied
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # Calculate dynamic range
            peak = np.max(np.abs(audio_array))
            
            if peak > 0:
                # Apply gentle compression - reduce dynamic range
                compressed = np.sign(audio_array) * np.power(np.abs(audio_array) / peak, 0.7) * peak
                
                # Apply mild gain boost for quiet speech
                gain_factor = min(2.0, 16000 / (peak + 1))
                boosted = compressed * gain_factor
                
                # Clip to prevent distortion
                result = np.clip(boosted, -32767, 32767)
                
                return result.astype(np.int16).tobytes()
            else:
                return audio_data
                
        except Exception as e:
            print(f"Warning: AGC failed: {e}")
            return audio_data
    
    def process_with_whisper(self, audio, src_lang):
        """Procesa el audio con Whisper con configuración mejorada"""
        try:
            print("\n=== INICIO DE PROCESO WHISPER ===")
            
            # Guardar audio en archivo temporal con procesamiento mejorado
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_filename = temp_audio.name
                
                # Get complete WAV data (includes headers)
                wav_data = audio.get_wav_data()
                
                # Write the original WAV file first
                with open(temp_filename, "wb") as f:
                    f.write(wav_data)
                
                # Now read it back properly, process it, and save it again
                try:
                    import soundfile as sf
                    import numpy as np
                    
                    # Read the audio data properly
                    audio_array, sample_rate = sf.read(temp_filename)
                    
                    # Convert to int16 format for processing if needed
                    if audio_array.dtype != np.int16:
                        audio_array = (audio_array * 32767).astype(np.int16)
                    
                    # Apply audio normalization using RMS for better Whisper recognition
                    print("Aplicando normalización de audio...")
                    normalized_audio = self.normalize_audio_rms(audio_array.tobytes(), target_rms=0.2)
                    
                    # Apply automatic gain control for consistency across microphones
                    print("Aplicando control automático de ganancia...")
                    processed_audio = self.apply_automatic_gain_control(normalized_audio)
                    
                    # Convert back to numpy array and save properly
                    processed_array = np.frombuffer(processed_audio, dtype=np.int16)
                    
                    # Save the processed audio back to the file with proper WAV format
                    sf.write(temp_filename, processed_array, sample_rate)
                    
                    print(f"Audio guardado en: {temp_filename}")
                    print(f"Tamaño del archivo de audio: {os.path.getsize(temp_filename)} bytes")
                    
                except ImportError:
                    print("Warning: soundfile not available, using original audio without processing")
                    # Just use the original WAV data
                    with open(temp_filename, "wb") as f:
                        f.write(wav_data)
                    print(f"Audio guardado en: {temp_filename}")
                    print(f"Tamaño del archivo de audio: {len(wav_data)} bytes")
                    
                except Exception as e:
                    print(f"Warning: Audio processing failed: {e}, using original audio")
                    # Fall back to original WAV data
                    with open(temp_filename, "wb") as f:
                        f.write(wav_data)
                    print(f"Audio guardado en: {temp_filename}")
                    print(f"Tamaño del archivo de audio: {len(wav_data)} bytes")
            
            # Verificar que el archivo existe
            if os.path.exists(temp_filename):
                print(f"Archivo temporal creado correctamente: {os.path.getsize(temp_filename)} bytes")
            else:
                print("ERROR: El archivo temporal no se creó")
                return None, None
            
            # Obtener el modelo Whisper
            if not self.current_whisper_model:
                self.current_whisper_model = self.model_loader.get_whisper_model('base')
            
            if not self.current_whisper_model:
                print("ERROR: No se pudo cargar el modelo Whisper")
                return None, None
            
            # Transcribir con Whisper usando chunked processing
            print("Iniciando transcripción con Whisper...")
            print(f"Idioma seleccionado por usuario: {src_lang}")
            
            result = self.transcribe_long_audio_gui(temp_filename, src_lang)
            
            print(f"\nResultado completo de Whisper:")
            print(f"- Texto: '{result['text']}'")
            print(f"- Idioma detectado: {result['language']}")
            print(f"- Longitud del texto: {len(result['text'])}")
            print(f"- Texto después de strip: '{result['text'].strip()}'")
            print(f"- Longitud después de strip: {len(result['text'].strip())}")
            
            # Mostrar información adicional del resultado
            if 'segments' in result:
                print(f"- Número de segmentos: {len(result['segments'])}")
                for i, segment in enumerate(result['segments']):
                    print(f"  Segmento {i}: '{segment['text']}' (confianza: {segment.get('avg_logprob', 'N/A')})")
            
            texto_transcrito = result["text"].strip()
            idioma_detectado = result["language"]
            
            # Limpiar archivo temporal
            os.unlink(temp_filename)
            print(f"Archivo temporal eliminado")
            
            # Validar resultado
            print(f"\nValidando texto...")
            print(f"- Texto a validar: '{texto_transcrito}'")
            print(f"- Idioma detectado: {idioma_detectado}")
            
            es_valido = self.validate_text(texto_transcrito, idioma_detectado)
            print(f"- Resultado de validación: {es_valido}")
            
            if es_valido:
                # El idioma detectado ya viene en formato ISO, no necesitamos mapear
                idioma_final = idioma_detectado
                print(f"- Idioma final: {idioma_final}")
                print(f"- RETORNANDO: '{texto_transcrito}', '{idioma_final}'")
                print("=== FIN DE PROCESO WHISPER (EXITOSO) ===\n")
                return texto_transcrito, idioma_final
            else:
                print("- TEXTO NO VÁLIDO - Retornando None")
                print("=== FIN DE PROCESO WHISPER (FALLIDO) ===\n")
                return None, None
                
        except Exception as e:
            print(f"\nERROR EN WHISPER: {e}")
            print(f"Tipo de error: {type(e)}")
            import traceback
            traceback.print_exc()
            print("=== FIN DE PROCESO WHISPER (ERROR) ===\n")
            return None, None
            
    def transcribe_long_audio_gui(self, audio_file, source_code, chunk_length=30):
        """
        Transcribe audio files in chunks for GUI version.
        
        Args:
            audio_file: Path to the audio file
            source_code: Language code or 'auto' for auto-detection
            chunk_length: Length of each chunk in seconds (default: 30)
        
        Returns:
            Combined transcription result
        """
        try:
            # Try to use librosa for chunked processing
            import librosa
            import numpy as np
            
            # Load audio file
            audio, sr = librosa.load(audio_file, sr=16000)
            audio_duration = len(audio) / sr
            
            print(f"Audio duration: {audio_duration:.2f} seconds")
            
            # If audio is short enough, process normally
            if audio_duration <= chunk_length:
                if source_code != 'auto':
                    return self.current_whisper_model.transcribe(
                        audio_file,
                        language=source_code,
                        word_timestamps=True,
                        fp16=False,
                        temperature=0.0,
                        best_of=5,
                        beam_size=5,
                        patience=2.0,
                        condition_on_previous_text=True
                    )
                else:
                    return self.current_whisper_model.transcribe(
                        audio_file,
                        word_timestamps=True,
                        fp16=False,
                        temperature=0.0,
                        best_of=5,
                        beam_size=5,
                        patience=2.0,
                        condition_on_previous_text=True
                    )
            
            # Process in chunks for long audio
            chunk_size = chunk_length * sr  # Convert to samples
            chunks = []
            texts = []
            
            for i in range(0, len(audio), chunk_size):
                chunk = audio[i:i + chunk_size]
                chunks.append(chunk)
                
                # Create temporary file for this chunk
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_chunk:
                    chunk_filename = temp_chunk.name
                    
                    # Write chunk to temporary file
                    import soundfile as sf
                    sf.write(chunk_filename, chunk, sr)
                    
                    try:
                        # Transcribe chunk
                        if source_code != 'auto':
                            chunk_result = self.current_whisper_model.transcribe(
                                chunk_filename,
                                language=source_code
                            )
                        else:
                            chunk_result = self.current_whisper_model.transcribe(chunk_filename)
                        
                        texts.append(chunk_result["text"])
                        print(f"Chunk {len(texts)}: '{chunk_result['text']}'")
                        
                    finally:
                        # Clean up chunk file
                        try:
                            os.unlink(chunk_filename)
                        except:
                            pass
            
            # Combine results
            combined_text = " ".join(texts).strip()
            
            # Return result in same format as regular transcribe
            # Use the language from the first non-empty chunk
            language = "es"  # Default
            try:
                if source_code != 'auto':
                    language = source_code
                else:
                    first_chunk_result = self.current_whisper_model.transcribe(audio_file, language=None)
                    language = first_chunk_result["language"]
            except:
                pass
                
            return {
                "text": combined_text,
                "language": language,
                "segments": []  # Could be enhanced to combine segments
            }
            
        except ImportError:
            print("Warning: librosa not available, falling back to regular transcription")
            # Fall back to regular transcription
            if source_code != 'auto':
                return self.current_whisper_model.transcribe(
                    audio_file,
                    language=source_code,
                    word_timestamps=True,
                    fp16=False,
                    temperature=0.0,
                    best_of=5,
                    beam_size=5,
                    patience=2.0,
                    condition_on_previous_text=True
                )
            else:
                return self.current_whisper_model.transcribe(
                    audio_file,
                    word_timestamps=True,
                    fp16=False,
                    temperature=0.0,
                    best_of=5,
                    beam_size=5,
                    patience=2.0,
                    condition_on_previous_text=True
                )
        except Exception as e:
            print(f"Error in chunked transcription: {e}")
            # Fall back to regular transcription
            if source_code != 'auto':
                return self.current_whisper_model.transcribe(
                    audio_file,
                    language=source_code,
                    word_timestamps=True,
                    fp16=False,
                    temperature=0.0,
                    best_of=5,
                    beam_size=5,
                    patience=2.0,
                    condition_on_previous_text=True
                )
            else:
                return self.current_whisper_model.transcribe(
                    audio_file,
                    word_timestamps=True,
                    fp16=False,
                    temperature=0.0,
                    best_of=5,
                    beam_size=5,
                    patience=2.0,
                    condition_on_previous_text=True
                )

    def validate_text(self, texto, idioma_detectado):
        """Valida que el texto sea válido para los idiomas soportados"""
        print(f"\n=== VALIDANDO TEXTO ===")
        print(f"Texto original: '{texto}'")
        print(f"Texto después de strip: '{texto.strip()}'")
        print(f"Longitud después de strip: {len(texto.strip())}")
        print(f"Idioma detectado: {idioma_detectado}")
        
        # Verificar longitud mínima
        texto_limpio = texto.strip()
        print(f"\n>>> VERIFICANDO LONGITUD MÍNIMA <<<")
        print(f"Longitud del texto limpio: {len(texto_limpio)}")
        print(f"Requisito mínimo: 2 caracteres")
        
        if len(texto_limpio) < 2:
            print(f"❌ FALLO: Texto muy corto (menos de 2 caracteres)")
            print(f"=== FIN VALIDACIÓN (FALLIDO POR LONGITUD) ===\n")
            return False
        else:
            print(f"✅ ÉXITO: Longitud suficiente ({len(texto_limpio)} caracteres)")
            
        # Verificar caracteres latinos (ampliado para alemán y francés)
        print(f"\n>>> VERIFICANDO CARACTERES LATINOS <<<")
        
        caracteres_latinos = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                               'áéíóúüñÁÉÍÓÚÜÑ¿¡äöüÄÖÜßàâäçèêëïîôùûüÿÀÂÄÇÈÊËÏÎÔÙÛÜŸ'
                               '.,;:!?()[]{}"\'-_ ')
        
        caracteres_texto = set(texto)
        caracteres_no_latinos = caracteres_texto - caracteres_latinos
        
        print(f"Total de caracteres únicos en el texto: {len(caracteres_texto)}")
        print(f"Caracteres únicos: {sorted(list(caracteres_texto))}")
        print(f"Caracteres no latinos encontrados: {len(caracteres_no_latinos)}")
        
        if len(caracteres_no_latinos) > 0:
            print(f"Caracteres no latinos: {sorted(list(caracteres_no_latinos))}")
            porcentaje_no_latinos = len(caracteres_no_latinos) / len(caracteres_texto)
            print(f"Porcentaje de caracteres no latinos: {porcentaje_no_latinos:.2%}")
            print(f"Umbral máximo permitido: 20%")
            
            if porcentaje_no_latinos > 0.2:
                print(f"❌ FALLO: Demasiados caracteres no latinos ({porcentaje_no_latinos:.2%} > 20%)")
                print(f"=== FIN VALIDACIÓN (FALLIDO POR CARACTERES NO LATINOS) ===\n")
                return False
            else:
                print(f"✅ ÉXITO: Porcentaje de caracteres no latinos aceptable ({porcentaje_no_latinos:.2%} <= 20%)")
        else:
            print(f"✅ ÉXITO: Todos los caracteres son latinos")
                
        # Verificar idioma detectado (usando códigos ISO ampliado)
        idiomas_validos = ['es', 'en', 'de', 'fr']
        print(f"Idiomas válidos: {idiomas_validos}")
        print(f"Idioma detectado: '{idioma_detectado}'")
        
        if idioma_detectado in idiomas_validos:
            print(f"✓ Idioma válido")
            print(f"=== FIN VALIDACIÓN (EXITOSO) ===\n")
            return True
        else:
            print(f"FALLO: Idioma no válido ('{idioma_detectado}' no está en {idiomas_validos})")
            print(f"=== FIN VALIDACIÓN (FALLIDO) ===\n")
            return False
        
    def determine_target_language(self, idioma_origen, target_selection):
        """Determina el idioma de destino basado en la selección y restricciones"""
        if target_selection == 'auto':
            # Lógica automática: español <-> inglés por defecto
            if idioma_origen == 'es':
                return 'en'
            elif idioma_origen == 'en':
                return 'es'
            elif idioma_origen == 'de':
                return 'es'  # Alemán por defecto a español
            elif idioma_origen == 'fr':
                return 'es'  # Francés por defecto a español
            else:
                return 'en'  # Cualquier otro a inglés
        else:
            # Verificar si la combinación es válida
            valid_combinations = {
                'es': ['en', 'de', 'fr'],
                'en': ['es', 'de', 'fr'],
                'de': ['es', 'en'],
                'fr': ['es', 'en']
            }
            
            if idioma_origen in valid_combinations and target_selection in valid_combinations[idioma_origen]:
                return target_selection
            else:
                return None
                
    def translate_text(self, texto, idioma_origen, idioma_destino):
        """Traduce el texto usando el modelo apropiado"""
        try:
            print(f"\n=== TRADUCIENDO ===")
            print(f"Texto: '{texto}'")
            print(f"Idioma origen: {idioma_origen}")
            print(f"Idioma destino: {idioma_destino}")
            
            # Obtener el modelo traductor usando LazyModelLoader
            translator = self.model_loader.get_model(idioma_origen, idioma_destino)
            
            if translator:
                # Call the translator pipeline with clean parameters
                try:
                    resultado = translator(texto, max_length=512, do_sample=False)
                    translation = resultado[0]['translation_text']
                    print(f"Traducción: '{translation}'")
                    print(f"=== FIN TRADUCCIÓN (EXITOSO) ===\n")
                    return translation
                except Exception as pipeline_error:
                    print(f"Pipeline error: {pipeline_error}")
                    # Try a simpler call without extra parameters
                    resultado = translator(texto)
                    translation = resultado[0]['translation_text']
                    print(f"Traducción: '{translation}'")
                    print(f"=== FIN TRADUCCIÓN (EXITOSO) ===\n")
                    return translation
            else:
                print(f"ERROR: No hay traductor para {idioma_origen} → {idioma_destino}")
                print(f"=== FIN TRADUCCIÓN (FALLIDO) ===\n")
                return None
                
        except Exception as e:
            print(f"Error en traducción: {e}")
            print(f"=== FIN TRADUCCIÓN (ERROR) ===\n")
            return None
            
    def play_translation(self):
        """Reproduce la traducción"""
        if not self.current_translation:
            messagebox.showwarning("Advertencia", "No hay traducción para reproducir")
            return
            
        self.update_status("🔊 Reproduciendo traducción...", "yellow")
        
        thread = threading.Thread(target=self.play_audio)
        thread.daemon = True
        thread.start()
        
    def play_audio(self):
        """Reproduce el audio de la traducción"""
        try:
            # Determinar idioma para TTS basado en la dirección seleccionada
            src_lang, tgt_lang = self.get_source_and_target_from_direction()
            
            # Usar el idioma de destino de la dirección seleccionada
            idioma_tts = tgt_lang
            
            print(f"Reproduciendo audio en idioma: {idioma_tts}")
            
            tts = gTTS(text=self.current_translation, lang=idioma_tts, slow=False)
            nombre_archivo = "temp_translation.mp3"
            tts.save(nombre_archivo)
            
            pygame.mixer.music.load(nombre_archivo)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            pygame.mixer.music.unload()
            os.remove(nombre_archivo)
            
            self.message_queue.put(("status", "✅ Reproducción completada", "lightgreen"))
            
        except Exception as e:
            self.message_queue.put(("status", f"❌ Error reproduciendo: {str(e)}", "red"))
            
    def detect_language_for_tts(self, texto):
        """Detecta el idioma del texto para TTS"""
        texto_lower = texto.lower()
        
        # Palabras y caracteres característicos por idioma
        spanish_indicators = {
            'words': ['el', 'la', 'de', 'que', 'y', 'es', 'en', 'un', 'una', 'con', 'por', 'para', 'hola', 'gracias', 'sí', 'no', 'dónde', 'cuándo', 'cómo', 'qué'],
            'chars': ['ñ', 'á', 'é', 'í', 'ó', 'ú', '¿', '¡']
        }
        
        german_indicators = {
            'words': ['der', 'die', 'das', 'und', 'ich', 'sie', 'mit', 'für', 'auf', 'von', 'ist', 'war', 'haben', 'werden', 'sein', 'nicht', 'auch', 'aber', 'oder', 'wie'],
            'chars': ['ä', 'ö', 'ü', 'ß']
        }
        
        french_indicators = {
            'words': ['le', 'la', 'les', 'et', 'de', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'avec', 'pour', 'sur', 'dans', 'mais', 'ou', 'où', 'comment'],
            'chars': ['à', 'â', 'ä', 'ç', 'è', 'ê', 'ë', 'ï', 'î', 'ô', 'ù', 'û', 'ü', 'ÿ']
        }
        
        # Calcular puntuaciones para cada idioma
        spanish_score = sum(1 for word in spanish_indicators['words'] if word in texto_lower) + \
                       sum(1 for char in spanish_indicators['chars'] if char in texto_lower)
        
        german_score = sum(1 for word in german_indicators['words'] if word in texto_lower) + \
                      sum(1 for char in german_indicators['chars'] if char in texto_lower)
        
        french_score = sum(1 for word in french_indicators['words'] if word in texto_lower) + \
                      sum(1 for char in french_indicators['chars'] if char in texto_lower)
        
        # Determinar idioma basado en la puntuación más alta
        scores = {'es': spanish_score, 'de': german_score, 'fr': french_score}
        max_score = max(scores.values())
        
        if max_score == 0:
            return 'en'  # Por defecto inglés si no hay indicadores
        
        for lang, score in scores.items():
            if score == max_score:
                return lang
        
        return 'en'  # Fallback a inglés
        
    def check_message_queue(self):
        """Verifica la cola de mensajes y actualiza la UI"""
        try:
            while True:
                message_type, *args = self.message_queue.get_nowait()
                
                if message_type == "status":
                    self.update_status(args[0], args[1] if len(args) > 1 else 'white')
                elif message_type == "progress":
                    self.show_progress(args[0])
                elif message_type == "progress_value":
                    self.progress_var.set(args[0])
                elif message_type == "enable_record":
                    self.record_btn.config(state=tk.NORMAL)
                elif message_type == "enable_load_btn":
                    self.load_models_btn.config(state=tk.NORMAL)
                elif message_type == "enable_play":
                    self.play_btn.config(state=tk.NORMAL)
                elif message_type == "original_text":
                    self.original_text.delete(1.0, tk.END)
                    self.original_text.insert(tk.END, args[0])
                elif message_type == "translated_text":
                    self.translated_text.delete(1.0, tk.END)
                    self.translated_text.insert(tk.END, args[0])
                elif message_type == "reset_record_btn":
                    self.record_btn.config(text="🎤 Hablar", bg='#2ecc71')
                elif message_type == "spinner":
                    if args[0] == "start":
                        self.start_spinner()
                    else:
                        self.stop_spinner()
                elif message_type == "listening_indicator":
                    self.update_listening_indicator(args[0])
                elif message_type == "model_status":
                    self.update_model_status(args[0], args[1], args[2] if len(args) > 2 else None)
                    
        except queue.Empty:
            pass
            
        # Programar la próxima verificación
        self.root.after(100, self.check_message_queue)
        
    def _on_model_progress(self, message, progress):
        """Callback para reportar progreso de carga de modelos"""
        self.message_queue.put(("status", f"🔄 {message}", "orange"))
        self.message_queue.put(("progress_value", progress))
        
        # Update model status based on progress
        if "Whisper" in message:
            if progress < 100:
                self.message_queue.put(("model_status", "whisper", "loading"))
            else:
                self.message_queue.put(("model_status", "whisper", "loaded"))
        elif "translator" in message.lower():
            if progress < 100:
                self.message_queue.put(("model_status", "translator", "loading", message))
            else:
                self.message_queue.put(("model_status", "translator", "loaded", message))
        
    def start_spinner(self):
        """Inicia el spinner de carga"""
        self.spinner_active = True
        self.spinner_label.pack(pady=2)
        self.animate_spinner()
        
    def stop_spinner(self):
        """Detiene el spinner de carga"""
        self.spinner_active = False
        self.spinner_label.pack_forget()
        
    def animate_spinner(self):
        """Anima el spinner"""
        if self.spinner_active:
            self.spinner_label.config(text=self.spinner_chars[self.spinner_index])
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            self.root.after(200, self.animate_spinner)
            
    def preload_models_for_selection(self):
        """Precarga modelos basados en la dirección actual de traducción"""
        src_lang, tgt_lang = self.get_source_and_target_from_direction()
        
        # Precargar solo el modelo específico
        self.load_specific_model(src_lang, tgt_lang)
            
    def load_models_for_languages(self, lang_list):
        """Carga modelos para una lista de idiomas en un hilo separado"""
        def load_in_thread():
            self.message_queue.put(("spinner", "start"))
            self.message_queue.put(("status", "🔄 Cargando modelos para auto-detección...", "orange"))
            
            # Usar load_all_for_languages para cargar todos los modelos necesarios
            results = self.model_loader.load_all_for_languages(lang_list)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            self.message_queue.put(("spinner", "stop"))
            if success_count == total_count:
                self.message_queue.put(("status", f"✅ Todos los modelos cargados ({success_count}/{total_count})", "lightgreen"))
            else:
                self.message_queue.put(("status", f"⚠️ Algunos modelos fallaron ({success_count}/{total_count})", "orange"))
                
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
        
    def load_specific_model(self, src_lang, tgt_lang):
        """Carga un modelo específico en un hilo separado"""
        def load_in_thread():
            self.message_queue.put(("spinner", "start"))
            self.message_queue.put(("status", f"🔄 Cargando modelo {src_lang}→{tgt_lang}...", "orange"))
            
            model = self.model_loader.get_model(src_lang, tgt_lang)
            
            self.message_queue.put(("spinner", "stop"))
            if model:
                self.message_queue.put(("status", f"✅ Modelo {src_lang}→{tgt_lang} cargado", "lightgreen"))
            else:
                self.message_queue.put(("status", f"❌ Error cargando modelo {src_lang}→{tgt_lang}", "red"))
                
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
        
    def load_whisper_model(self):
        """Carga el modelo Whisper"""
        def load_in_thread():
            self.message_queue.put(("spinner", "start"))
            self.message_queue.put(("status", "🔄 Cargando modelo Whisper...", "orange"))
            self.message_queue.put(("model_status", "whisper", "loading"))
            
            model = self.model_loader.get_whisper_model('base')
            
            self.message_queue.put(("spinner", "stop"))
            if model:
                self.current_whisper_model = model
                self.message_queue.put(("status", "✅ Modelo Whisper cargado", "lightgreen"))
                self.message_queue.put(("model_status", "whisper", "loaded"))
            else:
                self.message_queue.put(("status", "❌ Error cargando modelo Whisper", "red"))
                self.message_queue.put(("model_status", "whisper", "error"))
                
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
        
    def toggle_silence_detection(self):
        """Activa/desactiva la detección de silencio"""
        if self.silence_detection_enabled.get():
            self.silence_controls_frame.pack(pady=10)
            self.init_silence_detector()
        else:
            self.silence_controls_frame.pack_forget()
            if self.silence_detector:
                self.silence_detector.stop_monitoring()
                self.silence_detector = None
                self.silence_integration = None
                
    def init_silence_detector(self):
        """Inicializa el detector de silencio"""
        try:
            self.silence_detector = create_silence_detector(
                preset=self.silence_preset.get(),
                min_silence_len=self.min_silence_len.get(),
                silence_thresh=self.silence_thresh.get(),
                method='auto'
            )
            
            self.silence_integration = SilenceDetectorIntegration(
                self.recognizer, 
                self.silence_detector
            )
            
            # Configurar callbacks
            def on_silence_detected(timestamp):
                self.message_queue.put(("status", "🔇 Silencio detectado", "yellow"))
                
            def on_speech_detected(timestamp):
                self.message_queue.put(("status", "🎤 Habla detectada", "lightgreen"))
                
            def on_silence_threshold_exceeded(duration_ms):
                self.message_queue.put(("status", f"⏹️ Auto-stop: {duration_ms:.0f}ms de silencio", "orange"))
                # Aquí se podría implementar la lógica de auto-stop
                
            self.silence_detector.set_callbacks(
                on_silence_detected=on_silence_detected,
                on_speech_detected=on_speech_detected,
                on_silence_threshold_exceeded=on_silence_threshold_exceeded
            )
            
            self.update_status("🔇 Detector de silencio activado", "lightgreen")
            
        except Exception as e:
            self.message_queue.put(("status", f"❌ Error inicializando detector: {str(e)}", "red"))
            
    def on_silence_preset_change(self, event=None):
        """Maneja el cambio de preset de silencio"""
        preset = self.silence_preset.get()
        from silence_detector import SILENCE_DETECTION_PRESETS
        
        if preset in SILENCE_DETECTION_PRESETS:
            config = SILENCE_DETECTION_PRESETS[preset]
            self.min_silence_len.set(config['min_silence_len'])
            self.silence_thresh.set(config['silence_thresh'])
            
            # Reinicializar detector si está activo
            if self.silence_detection_enabled.get():
                self.init_silence_detector()
                
    def on_silence_param_change(self, event=None):
        """Maneja el cambio de parámetros de silencio"""
        if self.silence_detector:
            self.silence_detector.update_parameters(
                min_silence_len=self.min_silence_len.get(),
                silence_thresh=self.silence_thresh.get()
            )
    
    def update_mic_level_display(self):
        """Update the microphone level meter display"""
        if not hasattr(self, 'mic_level_canvas'):
            return
        
        # Clear the canvas
        self.mic_level_canvas.delete("all")
        
        # Calculate level bar width based on microphone level (0.0 to 1.0)
        canvas_width = 100
        canvas_height = 8
        level_width = int(canvas_width * self.microphone_level)
        
        # Draw background
        self.mic_level_canvas.create_rectangle(0, 0, canvas_width, canvas_height, 
                                              fill='#2c3e50', outline='#2c3e50')
        
        # Draw level bar with color based on level
        if level_width > 0:
            if self.microphone_level < 0.3:
                color = '#27ae60'  # Green for low levels
            elif self.microphone_level < 0.7:
                color = '#f39c12'  # Orange for medium levels
            else:
                color = '#e74c3c'  # Red for high levels
            
            self.mic_level_canvas.create_rectangle(0, 0, level_width, canvas_height, 
                                                  fill=color, outline=color)
        
        # Schedule next update
        self.root.after(100, self.update_mic_level_display)
    
    def update_listening_indicator(self, state):
        """Update the listening/processing indicator"""
        if state == "listening":
            self.listening_indicator.config(text="🎤 Listening...", fg='#27ae60')
            self.is_listening = True
            self.is_processing = False
        elif state == "processing":
            self.listening_indicator.config(text="⚙️ Processing...", fg='#f39c12')
            self.is_listening = False
            self.is_processing = True
        elif state == "silence_detected":
            self.listening_indicator.config(text="🔇 Silence detected", fg='#e74c3c')
        else:
            self.listening_indicator.config(text="", fg='white')
            self.is_listening = False
            self.is_processing = False
    
    def update_model_status(self, model_type, status, details=None):
        """Update the model status display"""
        if model_type == "whisper":
            if status == "loading":
                self.model_status_label.config(text="📋 Whisper: Loading...", fg='#f39c12')
            elif status == "loaded":
                self.model_status_label.config(text="📋 Whisper: Ready", fg='#27ae60')
            elif status == "error":
                self.model_status_label.config(text="📋 Whisper: Error", fg='#e74c3c')
        elif model_type == "translator":
            if status == "loading":
                lang_pair = details if details else "model"
                self.model_status_label.config(text=f"📋 Loading {lang_pair}...", fg='#f39c12')
            elif status == "loaded":
                lang_pair = details if details else "model"
                self.model_status_label.config(text=f"📋 {lang_pair}: Ready", fg='#27ae60')
            elif status == "error":
                lang_pair = details if details else "model"
                self.model_status_label.config(text=f"📋 {lang_pair}: Error", fg='#e74c3c')
        elif model_type == "none":
            self.model_status_label.config(text="📋 No model loaded", fg='#95a5a6')
    
    def simulate_microphone_level(self):
        """Simulate microphone level changes during recording"""
        if self.is_listening:
            # Simulate varying microphone levels during listening
            import random
            self.microphone_level = random.uniform(0.1, 0.8)
        elif self.is_processing:
            # Show steady low level during processing
            self.microphone_level = 0.2
        else:
            # Gradually decrease to zero when not recording
            self.microphone_level = max(0.0, self.microphone_level - 0.05)
        
        # Schedule next update
        self.root.after(50, self.simulate_microphone_level)

def main():
    root = tk.Tk()
    app = FluentAIGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
