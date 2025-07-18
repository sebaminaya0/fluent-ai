# Architecture Design

This document describes the multithreaded streaming architecture with a central queue. The system is composed of three main threads:

1️⃣ **CaptureThread**
   - Captures audio input segments.
   - Pushes segments to a `Queue[bytes]` for processing.

2️⃣ **WorkerThread**
   - Processes audio segments from the central queue using Whisper ASR (Automatic Speech Recognition).
   - Translates the recognized text to a target language using `translate(segment, target_lang)`.
   - Converts translated text to audio with `tts(text, target_lang)`.
   - Pushes the resulting audio buffers to a `Queue[np.ndarray]`.

3️⃣ **PlaybackThread**
   - Pulls audio buffers from the queue.
   - Uses a jitter buffer to handle timing variations before playback.
   - Outputs audio to a BlackHole device for audio output.

## Language Configuration

The language configurations are managed in a YAML file (`conf/languages.yaml`) with the following mappings:

```
es:  {whisper: 'spanish',  tts: 'es'}
en:  {whisper: 'english',  tts: 'en'}
pt:  {whisper: 'portuguese', tts: 'pt'}
de:  {whisper: 'german',   tts: 'de'}
fr:  {whisper: 'french',   tts: 'fr'}
```
