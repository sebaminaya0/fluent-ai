# Silence Detection Features

This document describes the robust silence/pause detection system implemented in Fluent AI. The system provides real-time audio energy monitoring with configurable parameters to automatically detect when to stop transcription based on sustained silence.

## Features

### Core Capabilities
- **Real-time audio energy monitoring** using webrtcvad and pydub
- **Configurable silence parameters** (minimum silence duration, audio threshold)
- **Auto-stop transcription** when sustained silence exceeds threshold
- **Timer reset** when speech resumes
- **Multiple detection methods** (webrtcvad, pydub, auto-selection)
- **Preset configurations** for different environments
- **GUI controls** for easy configuration
- **CLI flags** for power users

### Detection Methods

#### WebRTC VAD (Voice Activity Detection)
- **Recommended for:** Real-time speech detection
- **Advantages:** Low latency, optimized for speech
- **Configuration:** Aggressiveness levels 0-3
- **Requirements:** `webrtcvad` package

#### Pydub Silence Detection
- **Recommended for:** General audio analysis
- **Advantages:** Works with any audio content
- **Configuration:** dBFS threshold-based
- **Requirements:** `pydub` package

#### Auto-Selection
- **Default behavior:** Automatically chooses the best available method
- **Fallback order:** webrtcvad → pydub → error

## Configuration

### Silence Parameters

| Parameter | Description | Default | Range |
|-----------|-------------|---------|--------|
| `min_silence_len` | Minimum silence duration to trigger auto-stop | 800ms | 200-2000ms |
| `silence_thresh` | Audio level threshold for silence detection | -40dBFS | -60 to -20dBFS |
| `aggressiveness` | WebRTC VAD aggressiveness (0=least, 3=most) | 2 | 0-3 |
| `method` | Detection method to use | 'auto' | 'auto', 'webrtcvad', 'pydub' |

### Preset Configurations

| Preset | Min Silence | Threshold | Aggressiveness | Use Case |
|--------|-------------|-----------|---------------|----------|
| `sensitive` | 600ms | -35dBFS | 1 | Quiet environments |
| `balanced` | 800ms | -40dBFS | 2 | General use (default) |
| `aggressive` | 1200ms | -45dBFS | 3 | Noisy environments |
| `very_aggressive` | 1500ms | -50dBFS | 3 | Very noisy environments |

## Usage

### CLI Usage

#### Basic Usage
```bash
# Enable silence detection with default settings
python main_whisper.py --silence-detection

# Use a specific preset
python main_whisper.py --silence-detection --silence-preset aggressive

# Custom parameters
python main_whisper.py --silence-detection --min-silence-len 1000 --silence-thresh -35
```

#### Advanced Usage
```bash
# All parameters combined
python main_whisper.py --silence-detection \
  --silence-preset balanced \
  --min-silence-len 1200 \
  --silence-thresh -45 \
  --silence-method webrtcvad \
  --vad-aggressiveness 3
```

### GUI Usage

1. **Enable Detection**: Check the "🔇 Detección de silencio automática" checkbox
2. **Choose Preset**: Select from the dropdown (sensitive, balanced, aggressive, very_aggressive)
3. **Fine-tune Parameters**: Use the sliders to adjust:
   - Silence duration (200-2000ms)
   - Audio threshold (-60 to -20dBFS)
4. **Monitor Status**: The status bar shows real-time detection events

### Programmatic Usage

#### Basic Setup
```python
from silence_detector import create_silence_detector, SilenceDetectorIntegration
import speech_recognition as sr

# Create detector with preset
detector = create_silence_detector(preset='balanced')

# Set up callbacks
def on_silence_detected(timestamp):
    print(f"Silence detected at {timestamp}")

def on_speech_detected(timestamp):
    print(f"Speech detected at {timestamp}")

def on_silence_threshold_exceeded(duration_ms):
    print(f"Auto-stop triggered after {duration_ms:.0f}ms of silence")

detector.set_callbacks(
    on_silence_detected=on_silence_detected,
    on_speech_detected=on_speech_detected,
    on_silence_threshold_exceeded=on_silence_threshold_exceeded
)
```

#### Integration with Speech Recognition
```python
# Create components
recognizer = sr.Recognizer()
detector = create_silence_detector(preset='balanced')
integration = SilenceDetectorIntegration(recognizer, detector)

# Set up auto-stop callback
def on_auto_stop(duration_ms):
    print(f"Auto-stopping after {duration_ms:.0f}ms of silence")
    # Implement your auto-stop logic here

integration.set_transcription_callback(on_auto_stop)

# Use with microphone
with sr.Microphone() as source:
    audio = integration.listen_with_silence_detection(source, timeout=30)
    if audio:
        # Process audio with Whisper or other transcription
        pass
```

#### Custom Configuration
```python
# For noisy environments
noisy_detector = create_silence_detector(
    min_silence_len=1200,  # Longer silence required
    silence_thresh=-50,    # Lower threshold for noisy environments
    method='webrtcvad',    # More robust for speech detection
    aggressiveness=3       # Most aggressive VAD setting
)

# For quiet environments
quiet_detector = create_silence_detector(
    min_silence_len=600,   # Shorter silence acceptable
    silence_thresh=-30,    # Higher threshold for quiet environments
    method='pydub',        # Good for general audio analysis
    aggressiveness=1       # Less aggressive VAD setting
)
```

## Installation

### Dependencies
```bash
pip install webrtcvad pydub
```

### Additional Requirements
The silence detection system requires the following packages to be installed:
- `webrtcvad>=2.0.10` - For WebRTC VAD support
- `pydub>=0.25.1` - For general audio silence detection
- `numpy` - For audio processing
- `librosa` - For audio file handling
- `soundfile` - For audio file I/O

These are automatically included in the project's `pyproject.toml` file.

## API Reference

### SilenceDetector Class

#### Constructor
```python
SilenceDetector(
    min_silence_len: int = 800,    # Minimum silence duration in ms
    silence_thresh: int = -40,     # Silence threshold in dBFS
    frame_duration: int = 30,      # Frame duration for webrtcvad (10, 20, or 30 ms)
    aggressiveness: int = 2,       # WebRTC VAD aggressiveness (0-3)
    sample_rate: int = 16000,      # Audio sample rate
    method: str = 'auto'           # Detection method
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `set_callbacks(on_silence_detected, on_speech_detected, on_silence_threshold_exceeded)` | Set event callbacks |
| `update_parameters(**kwargs)` | Update detection parameters |
| `process_audio_frame(audio_data: bytes)` | Process a single audio frame |
| `start_monitoring(audio_source)` | Start monitoring audio source |
| `stop_monitoring()` | Stop monitoring |
| `reset_state()` | Reset detector state |
| `get_stats()` | Get current statistics |

### SilenceDetectorIntegration Class

#### Constructor
```python
SilenceDetectorIntegration(recognizer: sr.Recognizer, detector: SilenceDetector)
```

#### Methods

| Method | Description |
|--------|-------------|
| `set_transcription_callback(callback)` | Set callback for transcription events |
| `listen_with_silence_detection(source, timeout, phrase_time_limit)` | Listen with silence detection |

### Utility Functions

| Function | Description |
|----------|-------------|
| `create_silence_detector(preset='balanced', **kwargs)` | Create detector with preset configuration |

## Examples

### Example 1: Basic CLI Usage
```bash
# Start with silence detection enabled
python main_whisper.py --silence-detection

# Use aggressive preset for noisy environment
python main_whisper.py --silence-detection --silence-preset aggressive
```

### Example 2: GUI Usage
```bash
# Start GUI application
python gui_app.py

# In the GUI:
# 1. Check "🔇 Detección de silencio automática"
# 2. Select preset from dropdown
# 3. Adjust sliders as needed
# 4. Start recording - silence detection will be active
```

### Example 3: Custom Integration
```python
import speech_recognition as sr
from silence_detector import create_silence_detector

# Create custom detector
detector = create_silence_detector(
    min_silence_len=1000,
    silence_thresh=-35,
    method='webrtcvad'
)

# Set up callbacks
def handle_silence_threshold(duration_ms):
    print(f"Stopping recording after {duration_ms}ms of silence")
    # Your auto-stop logic here

detector.set_callbacks(
    on_silence_threshold_exceeded=handle_silence_threshold
)

# Use in your application
recognizer = sr.Recognizer()
with sr.Microphone() as source:
    # Your audio processing logic with silence detection
    pass
```

## Troubleshooting

### Common Issues

#### 1. Dependencies Not Found
```
Error: Neither webrtcvad nor pydub is available
```
**Solution:** Install the required packages:
```bash
pip install webrtcvad pydub
```

#### 2. WebRTC VAD Not Working
```
Error: webrtcvad is not available
```
**Solution:** Install webrtcvad or use pydub method:
```python
detector = create_silence_detector(method='pydub')
```

#### 3. Audio Sample Rate Issues
```
Warning: Sample rate 44100 not supported by webrtcvad, using 16000
```
**Solution:** This is handled automatically, but you can set the sample rate explicitly:
```python
detector = create_silence_detector(sample_rate=16000)
```

### Performance Tips

1. **Choose the right method:**
   - Use `webrtcvad` for real-time speech detection
   - Use `pydub` for general audio analysis
   - Use `auto` for automatic selection

2. **Adjust parameters for your environment:**
   - **Noisy environments:** Increase `min_silence_len`, decrease `silence_thresh`
   - **Quiet environments:** Decrease `min_silence_len`, increase `silence_thresh`

3. **Use appropriate presets:**
   - `sensitive` for quiet environments
   - `balanced` for general use
   - `aggressive` for noisy environments

## Testing

Run the demonstration script to test the silence detection features:

```bash
# Show all features
python demo_silence_detection.py

# Show specific features
python demo_silence_detection.py --cli
python demo_silence_detection.py --programmatic
python demo_silence_detection.py --realtime
python demo_silence_detection.py --gui
python demo_silence_detection.py --integration
```

## Contributing

When contributing to the silence detection system:

1. **Test with both detection methods** (webrtcvad and pydub)
2. **Validate across different audio environments**
3. **Ensure backward compatibility** with existing code
4. **Update documentation** for new features
5. **Add tests** for new functionality

## License

This silence detection system is part of the Fluent AI project and follows the same license terms.
