# FluentAI CLI - Real-time Translation

The FluentAI CLI provides a command-line interface for real-time voice translation using a multi-threaded architecture.

## Features

- **Language Configuration**: Loads language mappings from YAML configuration
- **Multi-threaded Architecture**: Runs 3 parallel processing threads
- **Real-time Stats**: Live overlay showing FPS, queue sizes, and latency
- **Voice Activity Detection**: Configurable VAD aggressiveness levels
- **Graceful Shutdown**: Proper cleanup on interruption

## Architecture

The CLI coordinates three main threads:

1. **Audio Capture Thread**: Captures audio with VAD and circular buffering
2. **ASR + Translation + Synthesis Thread**: Processes audio through Whisper ASR, translation, and TTS
3. **BlackHole Reproduction Thread**: Outputs processed audio to BlackHole device

## Usage

### Basic Usage

```bash
uv run python -m fluentai.cli.translate_rt --src es --dst en --voice female --vad 2
```

### Command-line Options

- `--src SRC`: Source language code (required)
- `--dst DST`: Destination language code (required)
- `--voice {female,male}`: Voice type for synthesis (default: female)
- `--vad {0,1,2,3}`: Voice Activity Detection aggressiveness (default: 2)
- `--verbose, -v`: Enable verbose logging

### Examples

```bash
# Spanish to English with female voice
uv run python -m fluentai.cli.translate_rt --src es --dst en --voice female --vad 2

# English to Spanish with male voice
uv run python -m fluentai.cli.translate_rt --src en --dst es --voice male --vad 1

# German to French with default settings
uv run python -m fluentai.cli.translate_rt --src de --dst fr

# With verbose logging
uv run python -m fluentai.cli.translate_rt --src pt --dst en --verbose
```

## Supported Languages

The CLI supports the following languages configured in `conf/languages.yaml`:

- `es`: Spanish
- `en`: English  
- `pt`: Portuguese
- `de`: German
- `fr`: French

Each language has mappings for:
- `whisper`: Language code for Whisper ASR
- `tts`: Language code for Text-to-Speech synthesis

## Stats Overlay

The CLI displays a real-time stats overlay showing:

- **Runtime**: Total elapsed time
- **Thread Performance**: FPS and queue sizes for each thread
- **End-to-end Latency**: Processing latency in milliseconds
- **System Information**: Current timestamp

Example output:
```
================================================================================
FluentAI Real-time Translation - Stats Overlay
================================================================================
Runtime: 00:02:34

Thread Performance:
  Audio Capture:
    FPS: 33.2
    Queue Size: 2

  ASR + Translation:
    FPS: 1.8
    Queue Size: 1

  Audio Output:
    FPS: 1.8
    Queue Size: 0

End-to-End Latency: 1250.5ms

System:
  Timestamp: 2024-01-15 10:30:45

Press Ctrl+C to stop
================================================================================
```

## Error Handling

The CLI includes comprehensive error handling for:

- Missing or invalid language configurations
- Thread initialization failures
- Model loading errors
- Audio device issues
- PyTorch/MPS backend compatibility

## Dependencies

The CLI depends on the following FluentAI modules:

- `fluentai.model_loader`: For loading and managing translation models
- `fluentai.asr_translation_synthesis_thread`: For ASR+translation+TTS processing
- `fluentai.blackhole_reproduction_thread`: For audio output
- `audio_capture_thread`: For audio capture with VAD

## Configuration

Language configurations are loaded from `conf/languages.yaml`:

```yaml
es:
  whisper: 'spanish'
  tts: 'es'

en:
  whisper: 'english'
  tts: 'en'

# ... other languages
```

## Testing

Run the CLI test suite:

```bash
python test_cli.py
```

This tests:
- CLI help functionality
- Argument validation
- Configuration loading
- Thread initialization

## Shutdown

The CLI handles graceful shutdown:
- Press `Ctrl+C` to stop
- All threads are properly terminated
- Model resources are cleaned up
- Audio devices are released

## Troubleshooting

### Common Issues

1. **MPS Backend Error**: If you encounter MPS-related errors, the CLI will suggest using CPU backend or updating PyTorch.

2. **Audio Device Not Found**: Ensure BlackHole is installed and configured properly.

3. **Model Loading Errors**: Check internet connection for downloading Hugging Face models.

4. **Permission Denied**: Ensure microphone permissions are granted.

### Logs

Use `--verbose` flag for detailed logging:

```bash
uv run python -m fluentai.cli.translate_rt --src es --dst en --verbose
```

## Performance Tips

- Use VAD level 2 for balanced performance
- Ensure stable internet connection for model downloads
- Close unnecessary audio applications
- Use SSD for faster model loading

## Development

To extend the CLI:

1. Add new language mappings to `conf/languages.yaml`
2. Implement new thread types in the corresponding modules
3. Update stats overlay for new metrics
4. Add new command-line options as needed

## License

This CLI is part of the FluentAI project.
