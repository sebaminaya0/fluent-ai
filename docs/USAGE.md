# Usage Guide - FluentAI Real-time Translation

This guide covers how to set up and use FluentAI for real-time translation in video conferencing applications like Zoom and Google Meet.

## Requirements

- macOS (for BlackHole setup)
- Python 3.13+
- FluentAI installed with real-time dependencies

## Installation

```bash
# Install FluentAI with real-time dependencies
uv sync --extra rt

# Or using pip
pip install -e .[rt]
```

## Audio Setup with BlackHole

### 1. Install BlackHole

BlackHole is a virtual audio driver that allows audio routing between applications.

```bash
# Install via Homebrew
brew install blackhole-2ch

# Or download from: https://github.com/ExistentialAudio/BlackHole
```

### 2. Configure Audio Aggregate Device

1. Open **Audio MIDI Setup** (Applications > Utilities > Audio MIDI Setup)
2. Click the **+** button and select **Create Aggregate Device**
3. Name it "BlackHole + Mic"
4. Check both:
   - **BlackHole 2ch** (for virtual audio routing)
   - **Built-in Microphone** (for your actual microphone)
5. Set **Built-in Microphone** as the clock source
6. Click **Apply**

### 3. Configure Audio Multi-Output Device

1. In Audio MIDI Setup, click **+** and select **Create Multi-Output Device**
2. Name it "BlackHole + Speakers"
3. Check both:
   - **BlackHole 2ch**
   - **Built-in Output** (or your preferred speakers/headphones)
4. Click **Apply**

## Zoom Setup

### Audio Settings

1. Open Zoom preferences
2. Go to **Audio** settings
3. Configure:
   - **Microphone**: Select "BlackHole + Mic"
   - **Speaker**: Select "BlackHole + Speakers"
4. Test your microphone to ensure it's working

### During a Meeting

1. Start FluentAI before joining the meeting:
   ```bash
   uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en
   ```

2. Join your Zoom meeting
3. FluentAI will:
   - Capture audio from the meeting participants
   - Translate it in real-time
   - Play the translated audio through your speakers

## Google Meet Setup

### Audio Settings

1. In Google Meet, click the **Settings** gear icon
2. Go to **Audio**
3. Configure:
   - **Microphone**: Select "BlackHole + Mic"
   - **Speakers**: Select "BlackHole + Speakers"

### During a Meeting

1. Start FluentAI:
   ```bash
   uv run python -m fluentai.cli.translate_rt --src-lang pt --dst-lang de
   ```

2. Join your Google Meet
3. The translation will work automatically

## FluentAI Command Line Options

### Basic Usage

```bash
# Spanish to English translation
uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en

# Portuguese to German translation
uv run python -m fluentai.cli.translate_rt --src-lang pt --dst-lang de

# English to Spanish translation
uv run python -m fluentai.cli.translate_rt --src-lang en --dst-lang es
```

### Advanced Options

```bash
# Specify Whisper model size
uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en --whisper-model large

# Adjust silence detection sensitivity
uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en --silence-preset sensitive

# Set custom audio devices
uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en --input-device 2 --output-device 1
```

### Available Language Codes

- `es` - Spanish
- `en` - English
- `pt` - Portuguese
- `de` - German
- `fr` - French
- `it` - Italian
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese

## Troubleshooting

### Audio Issues

**Problem**: No audio is being captured
- **Solution**: Ensure BlackHole + Mic is selected as the microphone in your video app
- **Check**: Audio MIDI Setup shows the aggregate device is configured correctly

**Problem**: Translated audio is not playing
- **Solution**: Verify BlackHole + Speakers is selected as the speaker output
- **Check**: System audio output is set to BlackHole + Speakers

**Problem**: Feedback loop or echo
- **Solution**: Use headphones instead of speakers
- **Alternative**: Lower the system volume

### Translation Issues

**Problem**: Translation is not accurate
- **Solution**: Try using a larger Whisper model (`--whisper-model large`)
- **Check**: Ensure the source language is correctly specified

**Problem**: Translation is too slow
- **Solution**: Use a smaller Whisper model (`--whisper-model base`)
- **Check**: Close other resource-intensive applications

**Problem**: No translation output
- **Solution**: Check that your microphone is working and audio is being captured
- **Check**: Verify the language pair is supported

### Performance Optimization

1. **Use appropriate Whisper model**:
   - `tiny`: Fastest, lowest accuracy
   - `base`: Good balance for real-time use
   - `small`: Better accuracy, slightly slower
   - `medium`: High accuracy, requires more resources
   - `large`: Best accuracy, slowest

2. **Adjust silence detection**:
   - `sensitive`: Detects shorter pauses
   - `balanced`: Default setting
   - `aggressive`: Only detects longer pauses
   - `very_aggressive`: Minimal pause detection

3. **System requirements**:
   - 8GB+ RAM recommended
   - Modern CPU (Intel i5/AMD Ryzen 5 or better)
   - Good internet connection for model downloads

## Demo Recording

To record a demo of the translation system:

1. **Setup recording software** (e.g., OBS Studio, QuickTime)
2. **Configure audio capture** to include both input and output
3. **Start FluentAI** with your desired language pair
4. **Join a test meeting** or use pre-recorded audio
5. **Demonstrate translation** between different language pairs

### Example Demo Script

```bash
# Terminal 1: Start Spanish to English translation
uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en

# Terminal 2: Start Portuguese to German translation (separate instance)
uv run python -m fluentai.cli.translate_rt --src-lang pt --dst-lang de --input-device 3 --output-device 4
```

## Support

For issues or questions:
- Check the logs in the terminal for error messages
- Verify audio device configurations
- Ensure all dependencies are properly installed
- Test with different language pairs to isolate issues

## Advanced Configuration

### Custom Audio Devices

List available audio devices:
```bash
uv run python -c "import sounddevice as sd; print(sd.query_devices())"
```

Use specific device IDs:
```bash
uv run python -m fluentai.cli.translate_rt --src-lang es --dst-lang en --input-device 2 --output-device 5
```

### Batch Processing

For offline translation of recorded meetings:
```bash
uv run python -m fluentai.cli.translate_batch --input meeting.wav --src-lang es --dst-lang en --output translated.wav
```
