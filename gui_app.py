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
        
        # Cola para comunicación entre hilos
        self.message_queue = queue.Queue()
        
        # Inicializar componentes de audio
        pygame.init()
        pygame.mixer.init()
        
        # Configurar reconocedor de voz
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        
        # Suprimir warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
        
        # Variables para los modelos
        self.whisper_model = None
        self.translator_es_en = None
        self.translator_en_es = None
        self.translator_es_de = None
        self.translator_de_es = None
        self.translator_es_fr = None
        self.translator_fr_es = None
        self.translator_en_de = None
        self.translator_de_en = None
        self.translator_en_fr = None
        self.translator_fr_en = None
        
        # Variables para selección de idiomas
        self.source_language = tk.StringVar(value='auto')
        self.target_language = tk.StringVar(value='auto')
        
        # Crear la interfaz
        self.create_ui()
        
        # Iniciar el monitoreo de la cola de mensajes
        self.check_message_queue()
        
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
        
        # Frame para selección de idiomas
        language_frame = tk.Frame(self.root, bg='#f0f0f0')
        language_frame.pack(pady=10)
        
        # Selector de idioma de origen
        source_frame = tk.Frame(language_frame, bg='#f0f0f0')
        source_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(source_frame, text="Idioma de origen:", 
                font=('Arial', 11, 'bold'), bg='#f0f0f0', fg='#2c3e50').pack()
        
        self.source_combo = ttk.Combobox(source_frame, textvariable=self.source_language, 
                                        values=['auto', 'es', 'en', 'de', 'fr'],
                                        state='readonly', width=15)
        self.source_combo.pack(pady=5)
        
        # Mapeo de códigos a nombres
        self.language_names = {
            'auto': '🔄 Detectar automáticamente',
            'es': '🇪🇸 Español',
            'en': '🇺🇸 English',
            'de': '🇩🇪 Deutsch',
            'fr': '🇫🇷 Français'
        }
        
        # Actualizar el combobox con nombres legibles
        self.source_combo.config(values=list(self.language_names.values()))
        self.source_combo.set(self.language_names['auto'])
        
        # Selector de idioma de destino
        target_frame = tk.Frame(language_frame, bg='#f0f0f0')
        target_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Label(target_frame, text="Idioma de destino:", 
                font=('Arial', 11, 'bold'), bg='#f0f0f0', fg='#2c3e50').pack()
        
        self.target_combo = ttk.Combobox(target_frame, textvariable=self.target_language, 
                                        values=list(self.language_names.values()),
                                        state='readonly', width=15)
        self.target_combo.pack(pady=5)
        self.target_combo.set(self.language_names['auto'])
        
        # Vincular eventos para actualizar restricciones
        self.source_combo.bind('<<ComboboxSelected>>', self.update_target_options)
        self.target_combo.bind('<<ComboboxSelected>>', self.update_source_options)
        
        # Frame para los botones de control
        control_frame = tk.Frame(self.root, bg='#f0f0f0')
        control_frame.pack(pady=20)
        
        # Botón para cargar modelos
        self.load_models_btn = tk.Button(control_frame, text="🔄 Cargar Modelos", 
                                        command=self.load_models_thread,
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
                                   state=tk.DISABLED)
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
        
        # Barra de estado
        self.status_frame = tk.Frame(self.root, bg='#34495e')
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(self.status_frame, text="🔴 Modelos no cargados", 
                                    font=('Arial', 10), bg='#34495e', fg='white')
        self.status_label.pack(pady=5)
        
        # Progress bar para carga de modelos
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.status_frame, variable=self.progress_var, 
                                           maximum=100, length=300)
        
    def get_language_code(self, display_name):
        """Convierte nombre de idioma a código"""
        for code, name in self.language_names.items():
            if name == display_name:
                return code
        return 'auto'
        
    def update_target_options(self, event=None):
        """Actualiza las opciones de idioma de destino según el origen seleccionado"""
        source_code = self.get_language_code(self.source_combo.get())
        
        if source_code == 'de':  # Alemán
            # Alemán solo puede traducir a español o inglés
            available_targets = ['auto', 'es', 'en']
        elif source_code == 'fr':  # Francés
            # Francés solo puede traducir a español o inglés
            available_targets = ['auto', 'es', 'en']
        else:
            # Español, inglés o auto pueden traducir a cualquiera
            available_targets = ['auto', 'es', 'en', 'de', 'fr']
            
        target_options = [self.language_names[code] for code in available_targets]
        self.target_combo.config(values=target_options)
        
        # Si la selección actual no está disponible, cambiar a auto
        current_target = self.get_language_code(self.target_combo.get())
        if current_target not in available_targets:
            self.target_combo.set(self.language_names['auto'])
            
    def update_source_options(self, event=None):
        """Actualiza las opciones de idioma de origen según el destino seleccionado"""
        target_code = self.get_language_code(self.target_combo.get())
        
        if target_code == 'de':  # Alemán
            # Solo español o inglés pueden traducir a alemán
            available_sources = ['auto', 'es', 'en']
        elif target_code == 'fr':  # Francés
            # Solo español o inglés pueden traducir a francés
            available_sources = ['auto', 'es', 'en']
        else:
            # Cualquier idioma puede traducir a español, inglés o auto
            available_sources = ['auto', 'es', 'en', 'de', 'fr']
            
        source_options = [self.language_names[code] for code in available_sources]
        self.source_combo.config(values=source_options)
        
        # Si la selección actual no está disponible, cambiar a auto
        current_source = self.get_language_code(self.source_combo.get())
        if current_source not in available_sources:
            self.source_combo.set(self.language_names['auto'])
        
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
            
    def load_models_thread(self):
        """Carga los modelos en un hilo separado"""
        if self.models_loading:
            return
            
        self.models_loading = True
        self.load_models_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.load_models)
        thread.daemon = True
        thread.start()
        
    def load_models(self):
        """Carga los modelos de IA"""
        try:
            self.message_queue.put(("status", "🔄 Cargando modelos... Esto puede tardar un momento", "orange"))
            self.message_queue.put(("progress", True))
            
            # Cargar Whisper
            self.message_queue.put(("status", "🔄 Cargando Whisper...", "orange"))
            self.message_queue.put(("progress_value", 10))
            self.whisper_model = whisper.load_model("base")
            
            # Cargar traductores español-inglés
            self.message_queue.put(("status", "🔄 Cargando traductor ES→EN...", "orange"))
            self.message_queue.put(("progress_value", 20))
            self.translator_es_en = pipeline("translation", model="Helsinki-NLP/opus-mt-es-en")
            
            self.message_queue.put(("status", "🔄 Cargando traductor EN→ES...", "orange"))
            self.message_queue.put(("progress_value", 30))
            self.translator_en_es = pipeline("translation", model="Helsinki-NLP/opus-mt-en-es")
            
            # Cargar traductores español-alemán
            self.message_queue.put(("status", "🔄 Cargando traductor ES→DE...", "orange"))
            self.message_queue.put(("progress_value", 40))
            self.translator_es_de = pipeline("translation", model="Helsinki-NLP/opus-mt-es-de")
            
            self.message_queue.put(("status", "🔄 Cargando traductor DE→ES...", "orange"))
            self.message_queue.put(("progress_value", 50))
            self.translator_de_es = pipeline("translation", model="Helsinki-NLP/opus-mt-de-es")
            
            # Cargar traductores español-francés
            self.message_queue.put(("status", "🔄 Cargando traductor ES→FR...", "orange"))
            self.message_queue.put(("progress_value", 60))
            self.translator_es_fr = pipeline("translation", model="Helsinki-NLP/opus-mt-es-fr")
            
            self.message_queue.put(("status", "🔄 Cargando traductor FR→ES...", "orange"))
            self.message_queue.put(("progress_value", 70))
            self.translator_fr_es = pipeline("translation", model="Helsinki-NLP/opus-mt-fr-es")
            
            # Cargar traductores inglés-alemán
            self.message_queue.put(("status", "🔄 Cargando traductor EN→DE...", "orange"))
            self.message_queue.put(("progress_value", 80))
            self.translator_en_de = pipeline("translation", model="Helsinki-NLP/opus-mt-en-de")
            
            self.message_queue.put(("status", "🔄 Cargando traductor DE→EN...", "orange"))
            self.message_queue.put(("progress_value", 85))
            self.translator_de_en = pipeline("translation", model="Helsinki-NLP/opus-mt-de-en")
            
            # Cargar traductores inglés-francés
            self.message_queue.put(("status", "🔄 Cargando traductor EN→FR...", "orange"))
            self.message_queue.put(("progress_value", 90))
            self.translator_en_fr = pipeline("translation", model="Helsinki-NLP/opus-mt-en-fr")
            
            self.message_queue.put(("status", "🔄 Cargando traductor FR→EN...", "orange"))
            self.message_queue.put(("progress_value", 95))
            self.translator_fr_en = pipeline("translation", model="Helsinki-NLP/opus-mt-fr-en")
            
            self.message_queue.put(("progress_value", 100))
            time.sleep(0.5)  # Pequeña pausa para mostrar el 100%
            
            self.is_models_loaded = True
            self.message_queue.put(("status", "✅ Modelos cargados correctamente", "lightgreen"))
            self.message_queue.put(("progress", False))
            self.message_queue.put(("enable_record", True))
            
        except Exception as e:
            self.message_queue.put(("status", f"❌ Error cargando modelos: {str(e)}", "red"))
            self.message_queue.put(("progress", False))
            
        finally:
            self.models_loading = False
            self.message_queue.put(("enable_load_btn", True))
            
    def toggle_recording(self):
        """Inicia o detiene la grabación"""
        if not self.is_models_loaded:
            messagebox.showwarning("Advertencia", "Por favor, carga los modelos primero")
            return
            
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def start_recording(self):
        """Inicia la grabación"""
        self.is_recording = True
        self.record_btn.config(text="🛑 Detener", bg='#e74c3c')
        
        # Mostrar idioma seleccionado en el estado
        source_code = self.get_language_code(self.source_combo.get())
        if source_code == 'auto':
            self.update_status("🎤 Escuchando... Habla ahora (detección automática)", "yellow")
        else:
            lang_name = self.language_names[source_code]
            self.update_status(f"🎤 Escuchando... Habla en {lang_name}", "yellow")
        
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
        
    def record_and_process(self):
        """Graba audio y procesa la traducción"""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Escuchar audio con tiempo extendido para capturar oraciones completas
                audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=12)
                
            if not self.is_recording:
                return
                
            # Mostrar estado de procesamiento más detallado
            source_code = self.get_language_code(self.source_combo.get())
            if source_code == 'auto':
                self.message_queue.put(("status", "🔍 Procesando con Whisper (detección automática)...", "orange"))
            else:
                lang_name = self.language_names[source_code]
                self.message_queue.put(("status", f"🔍 Procesando con Whisper ({lang_name})...", "orange"))
            
            # Procesar con Whisper
            texto_transcrito, idioma_detectado = self.process_with_whisper(audio)
            
            if texto_transcrito:
                self.message_queue.put(("original_text", texto_transcrito))
                
                # Determinar idioma de origen basado en selección del usuario
                source_code = self.get_language_code(self.source_combo.get())
                if source_code == 'auto':
                    idioma_origen = idioma_detectado
                    print(f"Usando idioma detectado automáticamente: {idioma_origen}")
                else:
                    idioma_origen = source_code
                    print(f"Usando idioma forzado por usuario: {idioma_origen}")
                
                # Determinar idioma de destino
                target_code = self.get_language_code(self.target_combo.get())
                idioma_destino = self.determine_target_language(idioma_origen, target_code)
                
                if idioma_destino:
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
                    self.message_queue.put(("status", "❌ Combinación de idiomas no válida", "red"))
            else:
                self.message_queue.put(("status", "❌ No se pudo procesar el audio", "red"))
                
        except sr.WaitTimeoutError:
            self.message_queue.put(("status", "⏱️ Tiempo de espera agotado", "orange"))
        except Exception as e:
            self.message_queue.put(("status", f"❌ Error: {str(e)}", "red"))
        finally:
            self.is_recording = False
            self.message_queue.put(("reset_record_btn", True))
            
    def process_with_whisper(self, audio):
        """Procesa el audio con Whisper con configuración mejorada"""
        try:
            print("\n=== INICIO DE PROCESO WHISPER ===")
            
            # Guardar audio en archivo temporal
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_filename = temp_audio.name
                with open(temp_filename, "wb") as f:
                    audio_data = audio.get_wav_data()
                    f.write(audio_data)
                    print(f"Audio guardado en: {temp_filename}")
                    print(f"Tamaño del archivo de audio: {len(audio_data)} bytes")
            
            # Verificar que el archivo existe
            if os.path.exists(temp_filename):
                print(f"Archivo temporal creado correctamente: {os.path.getsize(temp_filename)} bytes")
            else:
                print("ERROR: El archivo temporal no se creó")
                return None, None
            
            # Determinar idioma para forzar en Whisper
            source_code = self.get_language_code(self.source_combo.get())
            
            # Transcribir con Whisper
            print("Iniciando transcripción con Whisper...")
            print(f"Idioma seleccionado por usuario: {source_code}")
            
            if source_code != 'auto':
                print(f"Forzando idioma en Whisper: {source_code}")
                result = self.whisper_model.transcribe(
                    temp_filename,
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
                print("Permitiendo detección automática de idioma")
                result = self.whisper_model.transcribe(
                    temp_filename,
                    word_timestamps=True,
                    fp16=False,
                    temperature=0.0,
                    best_of=5,
                    beam_size=5,
                    patience=2.0,
                    condition_on_previous_text=True
                )
            
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
            
            # Mapear combinaciones a traductores
            translator_map = {
                ('es', 'en'): self.translator_es_en,
                ('en', 'es'): self.translator_en_es,
                ('es', 'de'): self.translator_es_de,
                ('de', 'es'): self.translator_de_es,
                ('es', 'fr'): self.translator_es_fr,
                ('fr', 'es'): self.translator_fr_es,
                ('en', 'de'): self.translator_en_de,
                ('de', 'en'): self.translator_de_en,
                ('en', 'fr'): self.translator_en_fr,
                ('fr', 'en'): self.translator_fr_en,
            }
            
            translator = translator_map.get((idioma_origen, idioma_destino))
            if translator:
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
            # Determinar idioma para TTS basado en la selección de destino
            target_code = self.get_language_code(self.target_combo.get())
            
            if target_code == 'auto':
                # Detección automática como antes
                idioma_tts = self.detect_language_for_tts(self.current_translation)
            else:
                idioma_tts = target_code
            
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
                    
        except queue.Empty:
            pass
            
        # Programar la próxima verificación
        self.root.after(100, self.check_message_queue)

def main():
    root = tk.Tk()
    app = FluentAIGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
