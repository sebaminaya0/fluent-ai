# Demo Video Recording Guide

This guide explains how to record demonstration videos of FluentAI's real-time translation capabilities.

## Prerequisites

### Software Requirements
- **OBS Studio** (recommended) or **QuickTime Player**
- **BlackHole** audio driver
- **FluentAI** with real-time dependencies

### Hardware Requirements
- **Microphone** for audio input
- **Speakers/Headphones** for audio output
- **Webcam** (optional, for presenter video)

## Setup Instructions

### 1. Install OBS Studio
Download and install OBS Studio from [https://obsproject.com/](https://obsproject.com/)

### 2. Configure Audio Routing
Follow the [USAGE.md](./USAGE.md) guide to set up:
- BlackHole audio driver
- Audio aggregate device ("BlackHole + Mic")
- Audio multi-output device ("BlackHole + Speakers")

### 3. Test Audio Setup
```bash
# Test audio devices
uv run python -c "import sounddevice as sd; print(sd.query_devices())"

# Test translation system
uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en
```

## Recording Setup

### OBS Studio Configuration

1. **Create a new Scene**
   - Name: "FluentAI Demo"

2. **Add Sources**:
   - **Display Capture**: Screen recording
   - **Audio Input Capture**: "BlackHole + Mic" (for input audio)
   - **Audio Output Capture**: "BlackHole + Speakers" (for translated audio)
   - **Video Capture Device**: Webcam (optional)

3. **Audio Settings**:
   - Go to **Settings → Audio**
   - Set **Desktop Audio**: "BlackHole + Speakers"
   - Set **Mic/Auxiliary Audio**: "BlackHole + Mic"
   - Sample Rate: 44.1 kHz
   - Channels: Stereo

4. **Output Settings**:
   - Go to **Settings → Output**
   - Output Mode: Simple
   - Recording Format: MP4
   - Recording Quality: High Quality, Medium File Size
   - Encoder: x264

### QuickTime Alternative
If using QuickTime Player:
1. **New Screen Recording**
2. **Options → Microphone**: Select "BlackHole + Mic"
3. **Options → Show Mouse Clicks**: Enable for better demos

## Demo Scripts

### Automated Demo Script
Use the provided demo script for structured recordings:

```bash
# Check dependencies first
python scripts/demo_recording.py --check-dependencies

# Run Spanish ↔ English demo
python scripts/demo_recording.py --demo-type es-en

# Run Portuguese ↔ German demo
python scripts/demo_recording.py --demo-type pt-de

# Run interactive demo
python scripts/demo_recording.py --demo-type interactive
```

### Manual Demo Process

1. **Start Recording**
2. **Open Terminal**
3. **Start FluentAI**:
   ```bash
   uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en
   ```
4. **Demonstrate Translation**:
   - Speak clearly in Spanish
   - Wait for translation
   - Explain the process
5. **Stop FluentAI** (Ctrl+C)
6. **Repeat for other language pairs**
7. **Stop Recording**

## Demo Content Structure

### Introduction (30 seconds)
- Introduce FluentAI
- Explain real-time translation capabilities
- Show supported language pairs

### Spanish ↔ English Demo (2 minutes)
1. **Start Spanish → English**
   - Show command execution
   - Speak Spanish phrases
   - Highlight English audio output
   - Demonstrate VAD detection

2. **Start English → Spanish**
   - Show command execution
   - Speak English phrases
   - Highlight Spanish audio output

### Portuguese ↔ German Demo (2 minutes)
1. **Start Portuguese → German**
   - Show command execution
   - Speak Portuguese phrases
   - Highlight German audio output

2. **Start German → Portuguese**
   - Show command execution
   - Speak German phrases
   - Highlight Portuguese audio output

### Technical Features Demo (1 minute)
- **Voice Activity Detection**: Show silence detection
- **Model Loading**: Display Whisper model initialization
- **Translation Pipeline**: Highlight ASR → Translation → TTS flow

### Conclusion (30 seconds)
- Summary of capabilities
- Use cases (Zoom, Google Meet)
- Setup instructions reference

## Sample Phrases for Demo

### Spanish Phrases
- "Hola, ¿cómo estás hoy?"
- "Me llamo María y soy de España"
- "¿Puedes ayudarme con este problema?"
- "El tiempo está muy bueno hoy"
- "Gracias por tu ayuda"

### Portuguese Phrases
- "Olá, como você está?"
- "Eu sou do Brasil"
- "Você pode me ajudar?"
- "O tempo está muito bom"
- "Obrigado pela ajuda"

### German Phrases
- "Hallo, wie geht es dir?"
- "Ich komme aus Deutschland"
- "Können Sie mir helfen?"
- "Das Wetter ist heute schön"
- "Vielen Dank für die Hilfe"

### English Phrases
- "Hello, how are you today?"
- "My name is John and I'm from the United States"
- "Can you help me with this problem?"
- "The weather is very nice today"
- "Thank you for your help"

## Recording Tips

### Audio Quality
- Use a good microphone
- Speak clearly and at normal pace
- Avoid background noise
- Test audio levels before recording

### Video Quality
- Use 1080p resolution minimum
- Ensure good lighting
- Keep screen clean and organized
- Use zoom for terminal text readability

### Presentation Tips
- Speak slowly and clearly
- Pause between demonstrations
- Explain each step
- Show both input and output audio
- Highlight key features

## Post-Production

### Editing Checklist
- [ ] Remove dead air/silence
- [ ] Add titles and annotations
- [ ] Highlight important text
- [ ] Add background music (optional)
- [ ] Include closed captions
- [ ] Export in multiple formats

### Recommended Editing Software
- **Free**: DaVinci Resolve, OpenShot
- **Paid**: Adobe Premiere Pro, Final Cut Pro

### Export Settings
- **Format**: MP4
- **Resolution**: 1080p (1920x1080)
- **Frame Rate**: 30fps
- **Bitrate**: 5-8 Mbps
- **Audio**: 44.1 kHz, 128 kbps

## Distribution

### File Naming Convention
```
fluentai-demo-[languages]-[date].mp4
```

Examples:
- `fluentai-demo-es-en-2024-07-17.mp4`
- `fluentai-demo-pt-de-2024-07-17.mp4`
- `fluentai-demo-full-2024-07-17.mp4`

### Upload Platforms
- **YouTube**: Main distribution
- **Vimeo**: High quality backup
- **GitHub**: Embed in README
- **Documentation**: Link in docs

### Video Metadata
- **Title**: "FluentAI Real-time Translation Demo - [Language Pair]"
- **Description**: Include setup instructions and links
- **Tags**: AI, translation, real-time, speech, voice, multilingual
- **Category**: Science & Technology

## Troubleshooting

### Common Issues

**Audio not recording properly**
- Check BlackHole configuration
- Verify OBS audio sources
- Test with simple audio first

**Translation not working**
- Check internet connection
- Verify model downloads
- Test with simple phrases

**Poor video quality**
- Increase bitrate settings
- Use better lighting
- Clean screen and close unnecessary apps

**Sync issues**
- Use higher frame rate
- Check audio sample rate
- Restart OBS if needed

### Testing Checklist
- [ ] Audio input working
- [ ] Audio output working
- [ ] Translation functioning
- [ ] Recording quality good
- [ ] No sync issues
- [ ] Clear terminal text

## Final Deliverables

1. **Main Demo Video** (5-6 minutes)
   - Complete functionality demonstration
   - Multiple language pairs
   - Technical explanations

2. **Quick Start Video** (2-3 minutes)
   - Basic setup and usage
   - Single language pair demo
   - Optimized for social media

3. **Technical Deep Dive** (8-10 minutes)
   - Architecture explanation
   - Performance metrics
   - Advanced configuration

4. **Setup Tutorial** (3-4 minutes)
   - Step-by-step installation
   - Audio configuration
   - Troubleshooting tips
