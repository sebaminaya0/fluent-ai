# 🌍 Fluent AI - Bidirectional AI Translator

A real-time bidirectional AI translator that supports Spanish ↔ English translation with speech recognition and text-to-speech synthesis.

## ✨ Features

- **🎤 Speech Recognition**: Automatically detects and transcribes speech in both Spanish and English
- **🔄 Bidirectional Translation**: Translates seamlessly between Spanish and English
- **🗣️ Text-to-Speech**: Plays back translations using natural voice synthesis
- **🧠 Language Detection**: Automatically identifies the input language
- **🔇 Noise Filtering**: Advanced microphone sensitivity settings to avoid false positives
- **⚡ Real-time Processing**: Fast response times for natural conversation flow

## 🛠️ Technologies Used

- **Speech Recognition**: `speech_recognition` with Google Speech API
- **Translation**: Helsinki-NLP models via `transformers`
- **Text-to-Speech**: `gTTS` (Google Text-to-Speech)
- **Audio Processing**: `pygame` for audio playback
- **Language Processing**: `sentencepiece` for tokenization

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
   brew install portaudio sentencepiece protobuf cmake pkg-config
   ```

3. **Install Python dependencies**:
   ```bash
   uv sync
   ```

## 🎯 Usage

Run the translator:
```bash
uv run main.py
```

**How to use:**
1. The program will start and load the translation models
2. When prompted, speak in either Spanish or English
3. The program will automatically detect the language
4. Translation will be displayed and played back in audio
5. Press `Ctrl+C` to exit

**Example:**
- Say: "Hola, mi nombre es Sebastian" → Plays: "Hello, my name is Sebastian"
- Say: "How are you today?" → Plays: "¿Cómo estás hoy?"

## 🔧 Configuration

The microphone sensitivity is pre-configured for optimal performance. If you experience issues with false positives or missed speech, you can adjust these parameters in `main.py`:

```python
recognizer.energy_threshold = 4000  # Adjust sensitivity
recognizer.dynamic_energy_threshold = True
```

## 📁 Project Structure

```
fluent-ai/
├── main.py              # Main application
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

- Helsinki-NLP for providing excellent translation models
- Google for Speech Recognition and Text-to-Speech services
- The open-source community for the amazing tools and libraries

---

**Made with ❤️ by Sebastian Minaya**
