# 🌍 Fluent AI - Bidirectional AI Translator

A real-time bidirectional AI translator that supports Spanish ↔ English translation with advanced speech recognition and text-to-speech synthesis.

## ✨ Features

### 🎤 **Advanced Speech Recognition**
- **Offline Recognition**: Powered by OpenAI Whisper for high-quality offline speech recognition
- **Dual Recognition System**: Whisper as primary with Google Speech Recognition as fallback
- **Language Validation**: Robust filtering to prevent non-Latin script recognition (Greek, Cyrillic, etc.)
- **Noise Filtering**: Advanced microphone sensitivity settings to avoid false positives

### 🔄 **Intelligent Translation**
- **Bidirectional Translation**: Translates seamlessly between Spanish and English
- **Language Detection**: Automatically identifies the input language
- **Quality Filtering**: Validates text quality before translation

### 🗣️ **Natural Speech Synthesis**
- **Text-to-Speech**: Plays back translations using natural voice synthesis
- **Multi-language Audio**: Supports both Spanish and English voice output

### ⚡ **Performance & Reliability**
- **Real-time Processing**: Fast response times for natural conversation flow
- **Robust Error Handling**: Graceful fallback mechanisms and user feedback
- **Offline Capability**: Core speech recognition works without internet connection

## 🔧️ Technologies Used

- **Primary Speech Recognition**: OpenAI Whisper for offline, high-quality transcription
- **Fallback Speech Recognition**: `speech_recognition` with Google Speech API
- **Translation**: Helsinki-NLP models via `transformers`
- **Text-to-Speech**: `gTTS` (Google Text-to-Speech)
- **Audio Processing**: `pygame` for audio playback, `ffmpeg` for audio conversion
- **Language Processing**: `sentencepiece` for tokenization
- **Language Validation**: Custom algorithms to filter non-Latin scripts

## 📋 Requirements

- Python 3.13+
- macOS (tested on macOS Sequoia)
- Homebrew (for system dependencies)
- Internet connection (for speech recognition and TTS)

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sebaminaya0/fluent-ai.git
   cd fluent-ai
   ```

2. **Install system dependencies**:
   ```bash
   brew install portaudio sentencepiece protobuf cmake pkg-config ffmpeg
   ```

3. **Install Python dependencies**:
   ```bash
   uv sync
   ```

## 🎯 Usage

### 🆕 **Standard Version**
Run the standard translator with Google Speech Recognition:
```bash
uv run main.py
```

### 🆕 **Whisper Version (Recommended)**
Run the enhanced version with OpenAI Whisper:
```bash
uv run main_whisper.py
```

> **Note**: The Whisper version provides better accuracy, offline capability, and robust language validation. It's recommended for most use cases.

### 📝 **How to use:**
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

The microphone sensitivity is pre-configured for optimal performance. If you experience issues with false positives or missed speech, you can adjust these parameters in `main.py`:

```python
recognizer.energy_threshold = 4000  # Adjust sensitivity
recognizer.dynamic_energy_threshold = True
```

## 📁 Project Structure

```
fluent-ai/
├── main.py              # Standard version with Google Speech Recognition
├── main_whisper.py      # Enhanced version with OpenAI Whisper (Recommended)
├── pyproject.toml       # Python dependencies
├── uv.lock             # Lock file with exact versions
├── .gitignore          # Git ignore rules
├── .python-version     # Python version specification
└── README.md           # This file
```

## 🔮 Future Enhancements

- [ ] Add support for more languages
- [ ] Implement offline translation capabilities
- [ ] Create a graphical user interface
- [ ] Add conversation history
- [ ] Implement custom wake words
- [ ] Add support for batch file translation

## 🤝 Contributing

Feel free to open issues or submit pull requests to improve the translator!

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- **OpenAI** for the incredible Whisper model for speech recognition
- **Helsinki-NLP** for providing excellent translation models
- **Google** for Speech Recognition and Text-to-Speech services
- **The open-source community** for the amazing tools and libraries

---

**Made with ❤️ by Sebastian Minaya**
