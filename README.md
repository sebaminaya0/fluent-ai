# 🌍 Fluent AI - Bidirectional AI Translator

A real-time bidirectional AI translator that supports multiple language pairs (Spanish, English, German, French) with advanced speech recognition and text-to-speech synthesis. Available as both command-line and GUI applications.

## ✨ Features

### 🖥️ **User-Friendly GUI**
- **Modern Interface**: Clean Tkinter-based graphical interface with intuitive controls
- **Translation Direction Selector**: Single dropdown to choose translation direction (e.g., "🇪🇸 Español → 🇺🇸 English")
- **Real-time Status**: Visual feedback during model loading and processing
- **Easy Recording**: One-click audio recording with extended capture capabilities
- **Instant Playback**: Audio playback of translations with visual controls
- **Smart Audio Processing**: Automatic gain control and RMS normalization for better transcription quality

### 🎤 **Advanced Speech Recognition**
- **Offline Recognition**: Powered by OpenAI Whisper for high-quality offline speech recognition
- **Extended Audio Capture**: Records up to 3 minutes of continuous speech without premature cutoffs
- **Smart Silence Detection**: 10-second timeout for natural speech pauses, unlimited audio size capability
- **Audio Preprocessing**: RMS normalization and automatic gain control for consistent transcription quality
- **Language Validation**: Robust filtering to prevent non-Latin script recognition (Greek, Cyrillic, etc.)
- **Optimized Settings**: Low energy threshold (300) and extended pause tolerance (2 seconds) for natural speech
- **Language Code Alignment**: Improved language detection with proper Whisper language code mapping

### 🔄 **Intelligent Translation**
- **Multi-language Support**: Supports Spanish, English, German, and French translation pairs
- **Explicit Language Selection**: User-selected translation direction eliminates auto-detection ambiguity
- **Supported Language Pairs**:
  - 🇪🇸 Spanish ↔ 🇺🇸 English
  - 🇪🇸 Spanish ↔ 🇩🇪 German
  - 🇪🇸 Spanish ↔ 🇫🇷 French
  - 🇺🇸 English ↔ 🇩🇪 German
  - 🇺🇸 English ↔ 🇫🇷 French
- **Quality Filtering**: Validates text quality before translation
- **Helsinki-NLP Models**: Uses state-of-the-art transformer models for translation
- **Lazy Model Loading**: Efficient memory usage by loading only required models

### 🗣️ **Natural Speech Synthesis**
- **Text-to-Speech**: Plays back translations using natural voice synthesis
- **Multi-language Audio**: Supports Spanish, English, German, and French voice output
- **Pygame Integration**: Reliable audio playback with pygame
- **Automatic Language Detection**: TTS automatically uses the target language for playback

### ⚡ **Performance & Reliability**
- **Real-time Processing**: Fast response times for natural conversation flow
- **Robust Error Handling**: Graceful fallback mechanisms and user feedback
- **Offline Capability**: Core speech recognition works without internet connection
- **Threaded Processing**: Non-blocking GUI with background processing

## 🔧️ Technologies Used

- **GUI Framework**: Tkinter for cross-platform graphical interface
- **Primary Speech Recognition**: OpenAI Whisper for offline, high-quality transcription
- **Fallback Speech Recognition**: `speech_recognition` with Google Speech API
- **Translation**: Helsinki-NLP models via `transformers`
- **Text-to-Speech**: `gTTS` (Google Text-to-Speech)
- **Audio Processing**: `pygame` for audio playback, `ffmpeg` for audio conversion
- **Language Processing**: `sentencepiece` for tokenization
- **Language Validation**: Enhanced algorithms to filter non-Latin scripts with proper language code mapping
- **Threading**: Python threading for non-blocking GUI operations

## 📋 Requirements

- Python 3.13+
- macOS (tested on macOS Sequoia)
- Homebrew (for system dependencies)
- Tkinter (for GUI - install with `brew install python-tk`)
- Internet connection (for speech recognition and TTS)

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sebaminaya0/fluent-ai.git
   cd fluent-ai
   ```

2. **Install system dependencies**:
   ```bash
   brew install portaudio sentencepiece protobuf cmake pkg-config ffmpeg python-tk
   ```

3. **Install Python dependencies**:
   ```bash
   uv sync
   ```

## 🎯 Usage

### 🖥️ **GUI Application (Recommended)**
Run the graphical user interface:
```bash
uv run gui_app.py
```

### 🆕 **Command-Line Versions**

**Standard Version** with Google Speech Recognition:
```bash
uv run main.py
```

**Whisper Version** with OpenAI Whisper:
```bash
uv run main_whisper.py
```

> **Note**: The GUI version provides the best user experience with visual feedback and easy controls. The Whisper command-line version offers better accuracy and offline capability.

### 📝 **How to use the GUI:**
1. **Select Translation Direction**: Choose your desired translation pair from the dropdown (e.g., "🇪🇸 Español → 🇺🇸 English")
2. **Load Whisper Model**: Click "🔄 Cargar Whisper" to initialize the speech recognition model
3. **Start Recording**: Click "🎤 Hablar" to begin recording your voice
4. **Speak Naturally**: The app captures up to 3 minutes of continuous speech with 10-second silence timeout
5. **View Results**: Original and translated text appear in real-time
6. **Play Translation**: Click "🔊 Reproducir" to hear the translated audio
7. **Advanced Options**: Enable silence detection for fine-tuned audio processing

### 📝 **How to use the command-line versions:**
1. The program will start and load the translation models
2. When prompted, speak in either Spanish or English
3. The program will automatically detect the language
4. Translation will be displayed and played back in audio
5. Press `Ctrl+C` to exit

### 💯 **Examples:**

**Spanish → English:**
- Say: "Hola, mi nombre es Sebastian" → Plays: "Hello, my name is Sebastian"
- Say: "¿Cómo estás hoy?" → Plays: "How are you today?"

**English → Spanish:**
- Say: "What's your favorite food?" → Plays: "¿Cuál es tu comida favorita?"
- Say: "I love programming in Python" → Plays: "Me encanta programar en Python"

**German → Spanish:**
- Say: "Guten Tag, wie geht es dir?" → Plays: "Buenas tardes, ¿cómo estás?"

**French → English:**
- Say: "Bonjour, comment allez-vous?" → Plays: "Hello, how are you?"

## 🔧 Configuration

### CLI Flags

- `--lang-code`: Set input language code.
- `--offline-mode`: Enable offline usage with pre-loaded models.

### Environment Variables

- `FLUENT_AI_API_KEY`: Your API key for using cloud services.
- `FLUENT_AI_ENV`: Set to `development` or `production`.

### Audio Recording Configuration

The GUI application includes optimized audio settings for extended speech capture:

**Default Settings (Optimized for Natural Speech):**
```python
# Speech recognition settings
recognizer.energy_threshold = 300  # Low threshold for better sensitivity
recognizer.dynamic_energy_threshold = False  # Disabled to prevent premature cutoffs
recognizer.pause_threshold = 2.0  # 2-second pause tolerance
recognizer.operation_timeout = None  # No operation timeout
recognizer.non_speaking_duration = 2.0  # 2-second non-speaking duration

# Audio capture settings
phrase_time_limit = 180  # 3-minute maximum recording time
sample_rate = 16000  # Optimized for Whisper
chunk_size = 1024  # Optimal chunk size
```

**Silence Detection (Optional):**
- Enable via checkbox in GUI for fine-tuned control
- Adjustable presets: sensitive, balanced, aggressive, very_aggressive
- Customizable silence duration (200-2000ms) and threshold (-60 to -20 dBFS)

**Audio Preprocessing:**
- RMS normalization for consistent volume levels
- Automatic gain control for microphone consistency
- Optimized for Whisper transcription quality
## 📁 Project Structure

```
fluent-ai/
├── gui_app.py           # Main GUI application with Tkinter (Recommended)
├── main.py              # Command-line version with Google Speech Recognition
├── main_whisper.py      # Command-line version with OpenAI Whisper
├── fluentai/
│   ├── model_loader.py  # Lazy model loading system
│   └── __init__.py
├── silence_detector.py  # Advanced silence detection module
├── pyproject.toml       # Python dependencies
├── uv.lock             # Lock file with exact versions
├── .gitignore          # Git ignore rules
├── .python-version     # Python version specification
└── README.md           # This file
```

## 🔮 Future Enhancements

- [x] Add support for more languages (German, French) ✅
- [ ] Implement offline translation capabilities
- [x] Create a graphical user interface ✅
- [x] Extended audio capture capabilities ✅
- [x] Smart silence detection with configurable presets ✅
- [x] Translation direction selector ✅
- [ ] Add conversation history to GUI
- [ ] Implement custom wake words
- [ ] Add support for batch file translation
- [ ] Implement real-time streaming translation
- [ ] Add support for more language pairs (Italian, Portuguese, etc.)

## 🔄 Migration Notes

To upgrade to the latest version, please consider the following changes:

- **Eager Model Loading Removed**: Models are now lazy-loaded to improve startup times. Ensure your environment can handle dynamic loading.
- **Translation Direction Selector**: The GUI now uses a single dropdown for translation direction instead of separate source/target selectors.
- **Extended Audio Capture**: Recording time increased to 3 minutes with 10-second silence timeout.
- **Audio Preprocessing**: New RMS normalization and automatic gain control for better transcription quality.
- **Multi-language Support**: Added German and French language support with Helsinki-NLP models.

## 🤝 Contributing

Feel free to open issues or submit pull requests to improve the translator!

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- **OpenAI** for the incredible Whisper model for speech recognition
- **Helsinki-NLP** for providing excellent translation models
- **Google** for Speech Recognition and Text-to-Speech services
- **Tkinter** for the cross-platform GUI framework
- **The open-source community** for the amazing tools and libraries

---

**Made with ❤️ by Sebastian Minaya**
