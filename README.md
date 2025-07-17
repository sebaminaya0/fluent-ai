# 🌍 Fluent AI - Bidirectional AI Translator

A real-time bidirectional AI translator that supports Spanish ↔ English translation with advanced speech recognition and text-to-speech synthesis. Available as both command-line and GUI applications.

## ✨ Features

### 🖥️ **User-Friendly GUI**
- **Modern Interface**: Clean Tkinter-based graphical interface
- **Real-time Status**: Visual feedback during model loading and processing
- **Easy Recording**: One-click audio recording and translation
- **Instant Playback**: Audio playback of translations with visual controls

### 🎤 **Advanced Speech Recognition**
- **Offline Recognition**: Powered by OpenAI Whisper for high-quality offline speech recognition
- **Dual Recognition System**: Whisper as primary with Google Speech Recognition as fallback
- **Language Validation**: Robust filtering to prevent non-Latin script recognition (Greek, Cyrillic, etc.)
- **Noise Filtering**: Advanced microphone sensitivity settings to avoid false positives
- **Language Code Alignment**: Improved language detection with proper Whisper language code mapping

### 🔄 **Intelligent Translation**
- **Bidirectional Translation**: Translates seamlessly between Spanish and English
- **Language Detection**: Automatically identifies the input language with enhanced validation
- **Quality Filtering**: Validates text quality before translation
- **Helsinki-NLP Models**: Uses state-of-the-art transformer models for translation

### 🗣️ **Natural Speech Synthesis**
- **Text-to-Speech**: Plays back translations using natural voice synthesis
- **Multi-language Audio**: Supports both Spanish and English voice output
- **Pygame Integration**: Reliable audio playback with pygame

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
uv run gui.py
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
1. Click "Load Models" to initialize the translation models
2. Click "Record" to start recording your voice
3. Speak in either Spanish or English
4. The program will automatically detect the language and translate
5. Click "Play Translation" to hear the translated audio
6. Original and translated text will be displayed in the interface

### 📝 **How to use the command-line versions:**
1. The program will start and load the translation models
2. When prompted, speak in either Spanish or English
3. The program will automatically detect the language
4. Translation will be displayed and played back in audio
5. Press `Ctrl+C` to exit

### 💯 **Example:**
- Say: "Hola, mi nombre es Sebastian" → Plays: "Hello, my name is Sebastian"
- Say: "How are you today?" → Plays: "¿Cómo estás hoy?"
- Say: "What's your favorite food?" → Plays: "¿Cuál es tu comida favorita?"

## 🔧 Configuration

The microphone sensitivity is pre-configured for optimal performance. If you experience issues with false positives or missed speech, you can adjust these parameters in the command-line versions (`main.py` or `main_whisper.py`):

```python
recognizer.energy_threshold = 4000  # Adjust sensitivity
recognizer.dynamic_energy_threshold = True
```

For the GUI version, the audio recording parameters can be adjusted in `gui.py`:

```python
# Audio recording settings
channels = 1
rate = 16000
chunk = 1024
```

## 📁 Project Structure

```
fluent-ai/
├── gui.py               # GUI application with Tkinter (Recommended)
├── main.py              # Command-line version with Google Speech Recognition
├── main_whisper.py      # Command-line version with OpenAI Whisper
├── pyproject.toml       # Python dependencies
├── uv.lock             # Lock file with exact versions
├── .gitignore          # Git ignore rules
├── .python-version     # Python version specification
└── README.md           # This file
```

## 🔮 Future Enhancements

- [ ] Add support for more languages
- [ ] Implement offline translation capabilities
- [x] Create a graphical user interface ✅
- [ ] Add conversation history to GUI
- [ ] Implement custom wake words
- [ ] Add support for batch file translation
- [ ] Add voice activity detection
- [ ] Implement real-time streaming translation

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
