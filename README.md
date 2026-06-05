# 🌍 fluent ai — real-time speech translator

**fluent ai** is a real-time, offline-capable bidirectional speech translator for
macOS. It listens to your microphone, transcribes with OpenAI Whisper, translates
with Helsinki-NLP MarianMT, and speaks the result back — across Spanish, English,
German, and French.

The current focus is **Meeting Mode**: a low-latency streaming pipeline with live
captions and per-sentence audio, plus **mic-in-use auto-detection** — the moment
a call grabs your microphone (Zoom, Teams, browser Google Meet), fluent ai can
offer to start translating, Granola-style.

> Status: active development (v0.2.0). Test suite green (72 passed, 3 skipped),
> lint clean. macOS-first; degrades gracefully on other platforms.

---

## ✨ What it does

### 🎤 Meeting Mode (streaming, low-latency)
- **Two-stage pipeline** — the next utterance is transcribed while the current
  one is still being spoken, so translated audio starts in ~milliseconds.
- **Live captions** via `StreamingTranscriber` — re-transcribes growing audio
  snapshots and commits only the text two passes agree on (**LocalAgreement-2**),
  so captions are stable and don't flicker.
- **Streaming TTS** through the macOS `say` engine (~100ms to first audio), with
  a `sounddevice` fallback off macOS.
- **Feedback-loop control** — the mic is muted while speaking (plus a short echo
  tail) so fluent ai never re-records its own output (half-duplex).
- **Floating overlay** — a compact Meeting Mode window shows the live caption,
  translation, and latency.

### 📞 Mic-in-use auto-detection
- Pure-ctypes CoreAudio watcher (`fluentai/meeting_detector.py`) polls whether
  *any* app is capturing the default input device.
- Debounced `MicMonitor` fires `call started` / `call ended` callbacks, so the
  app can prompt "Call detected — start live translation?"
- macOS-only and dependency-free; no-ops elsewhere.

### 🔄 Translation
- Bidirectional pairs across **Spanish · English · German · French**.
- Explicit direction selection (no auto-detect ambiguity).
- **Helsinki-NLP OPUS-MT** models, **lazily loaded** with an LRU cache.

### 🗄️ Logging & analytics
- Every step (audio, ASR, translation, playback) logged to **DuckDB**, with
  millisecond latency, model used, errors, and JSON metadata.
- A live monitor dashboard (`live_monitor.py --db`) and a `view_database.py`
  inspector.

---

## 🧩 Architecture (high level)

```
Microphone
   ↓
audio_capture_thread.py        CircularAudioBuffer + WebRTC VAD (+ partial snapshots)
   ↓ asr_queue
MeetingASRThread               Whisper (numpy in) → MarianMT translate
   ↓ speak_queue
MeetingSpeakThread             stream TTS via `say --audio-device`
   ↓
Output device / BlackHole
```

The basic translator still uses the legacy single-thread path
(`asr_translation_synthesis_thread.py`). Meeting Mode uses the streaming
two-stage pipeline (`fluentai/meeting_pipeline.py`). See
[`docs/architecture.md`](./docs/architecture.md) for detail.

---

## 📋 Requirements

- macOS (mic auto-detection and the `say` TTS fast path are macOS-only)
- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/) package manager
- Homebrew (for system audio dependencies)

---

## 🚀 Installation

```bash
# 1. Clone
git clone https://github.com/sebaminaya0/fluent-ai.git
cd fluent-ai

# 2. System dependencies
brew install portaudio sentencepiece protobuf cmake pkg-config ffmpeg python-tk

# 3. Python dependencies (add --extra dev for the test/lint tools)
uv sync
uv sync --extra dev
```

---

## 🎯 Usage

### GUI (recommended)
```bash
uv run gui_app.py
```
Pick a translation direction, load the Whisper model, and either use the basic
recorder or switch on **Meeting Mode** for streaming live translation.

### Command line
```bash
# Whisper-backed CLI
uv run main_whisper.py

# Real-time CLI translation (installed entry point or module form)
uv run fluentai-rt --src es --dst en
python -m fluentai.cli.translate_rt --src es --dst en
```

### Auto-detection demo
```bash
# Prints when a call (mic capture) starts/ends — open Zoom/Teams/Meet to see it
uv run python -m fluentai.meeting_detector
```

### Live monitor & database
```bash
uv run live_monitor.py            # dashboard only
uv run live_monitor.py --db       # dashboard + DuckDB logging

uv run init_database.py           # initialize schema
uv run view_database.py [session_id]
```

### BlackHole audio (for routing translated audio into a call)
```bash
uv run examples/blackhole_setup.py
```
See [`docs/blackhole-setup.md`](./docs/blackhole-setup.md) and
[`docs/meeting-testing.md`](./docs/meeting-testing.md).

---

## 🗣️ Supported language pairs

| Pair | Models |
|---|---|
| 🇪🇸 Spanish ↔ 🇺🇸 English | `opus-mt-es-en`, `opus-mt-en-es` |
| 🇪🇸 Spanish ↔ 🇩🇪 German | `opus-mt-es-de`, `opus-mt-de-es` |
| 🇪🇸 Spanish ↔ 🇫🇷 French | `opus-mt-es-fr`, `opus-mt-fr-es` |
| 🇺🇸 English ↔ 🇩🇪 German | `opus-mt-en-de`, `opus-mt-de-en` |
| 🇺🇸 English ↔ 🇫🇷 French | `opus-mt-en-fr`, `opus-mt-fr-en` |

Language codes live in [`conf/languages.yaml`](./conf/languages.yaml).

---

## 🛠️ Development

```bash
uv run ruff check .            # lint
uv run ruff format .           # format
uv run mypy fluentai/          # type-check
uv run pytest tests/           # tests (currently: 72 passed, 3 skipped)
uv run pytest tests/test_benchmarks.py -v -s   # latency benchmarks
```

Run `ruff check .` and `pytest tests/` before pushing — both are green today and
should stay that way. Contributor and AI-assistant guidance lives in
[`CLAUDE.md`](./CLAUDE.md).

---

## 📁 Project structure

```
fluent-ai/
├── gui_app.py                  # Main Tkinter GUI (+ Meeting Mode)
├── main_whisper.py             # Whisper CLI
├── live_monitor.py             # Real-time monitor (--db enables DuckDB)
├── audio_capture_thread.py     # Mic capture + WebRTC VAD (+ partial snapshots)
├── silence_detector.py         # Silence/pause detection
├── init_database.py            # DuckDB schema initializer
├── view_database.py            # Database viewer/query tool
├── fluentai/                   # Installable core package
│   ├── model_loader.py         # Lazy, LRU-cached model manager
│   ├── meeting_pipeline.py     # Two-stage streaming Meeting Mode
│   ├── streaming_asr.py        # Live captions (LocalAgreement-2)
│   ├── meeting_detector.py     # Mic-in-use auto-detection (CoreAudio)
│   ├── tts_engine.py           # macOS `say` + fallback TTS
│   ├── app_controller.py       # Non-UI translation/text helpers
│   ├── database_logger.py      # DuckDB logging
│   ├── ui/meeting_overlay.py   # Floating Meeting Mode overlay
│   └── cli/translate_rt.py     # Real-time translation CLI
├── conf/languages.yaml         # Language code mappings
├── docs/                       # Architecture, usage, roadmap
├── tests/                      # pytest suite
└── pyproject.toml / uv.lock    # Project metadata + lockfile
```

---

## 📚 Documentation

- [Usage guide](./docs/USAGE.md) — running the app and meeting setup
- [Architecture](./docs/architecture.md) — pipeline and threading design
- [Roadmap](./docs/roadmap.md) — menu-bar agent, branding, sequencing
- [Database logging](./docs/database-logging.md) — DuckDB schema and analytics
- [BlackHole setup](./docs/blackhole-setup.md) — virtual audio device config
- [Silence detection](./docs/silence-detection.md) — VAD presets and tuning
- [Meeting testing](./docs/meeting-testing.md) — verifying translated audio in calls
- [Demo recording](./docs/DEMO_RECORDING.md) — producing demo videos

---

## 🗺️ Roadmap (next phase)

The north star is a **background macOS menu-bar agent** that auto-detects calls
and shows a refined, branded floating overlay. See [`docs/roadmap.md`](./docs/roadmap.md).

- [x] Streaming Meeting Mode (live captions + per-sentence audio)
- [x] Low-latency streaming TTS (`say --audio-device`) + feedback-loop fix
- [x] Mic-in-use auto-detection (CoreAudio)
- [ ] Menu-bar agent (`rumps`) running the detector headless
- [ ] Decouple the pipeline from Tkinter to run under the menu bar
- [ ] Overlay redesign + `fluent ai` branding (electric blue / electric green)
- [ ] Dark mode
- [ ] More language pairs (Italian, Portuguese, …)

---

## 📄 License

Open source under the MIT License.

## 🙏 Acknowledgments

- **OpenAI** — the Whisper speech-recognition model
- **Helsinki-NLP** — the OPUS-MT translation models
- **The open-source community** — the audio and ML tooling that makes this possible

---

**Made with ❤️ by Sebastian Minaya**
