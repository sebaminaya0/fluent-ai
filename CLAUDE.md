# CLAUDE.md — Fluent AI Codebase Guide

This file provides guidance for AI assistants (Claude, Copilot, etc.) working on the Fluent AI codebase.

---

## Project Overview

**Fluent AI** (branded **`fluent ai`**, all lowercase) is a real-time,
offline-capable bidirectional speech translation desktop app. It captures
microphone audio, transcribes it with OpenAI Whisper, translates with
Helsinki-NLP MarianMT, synthesizes the translation, and plays the output — all
in a multi-threaded pipeline.

The current focus is **Meeting Mode**: a low-latency streaming pipeline with
live captions and per-sentence audio, plus **mic-in-use auto-detection**
(Granola-style "call detected → start translating"). The north-star direction
is a macOS menu-bar agent + branded floating overlay — see
[`docs/roadmap.md`](docs/roadmap.md).

- **Primary interface**: Tkinter GUI (`gui_app.py`), with a floating Meeting
  Mode overlay (`fluentai/ui/meeting_overlay.py`)
- **TTS**: macOS `say` fast path (~100ms) in the streaming pipeline; gTTS /
  pyttsx3 elsewhere
- **Python version**: 3.13+ · **Package manager**: `uv` · **Version**: 0.2.0
- **Platform**: macOS-first (mic detection + `say` are macOS-only; degrade
  gracefully elsewhere)
- **Database**: DuckDB (`translation_logs.duckdb`)

---

## Repository Layout

```
fluent-ai/
├── gui_app.py                  # Main GUI (Tkinter, ~1,520 lines; delegates to TranslationController + fluentai/ui)
├── main_whisper.py             # CLI entry point — Whisper ASR (~780 lines)
├── live_monitor.py             # Real-time monitor dashboard (--db enables DuckDB logging)
├── audio_capture_thread.py     # Continuous mic capture + WebRTC VAD (+ opt-in partial snapshots)
├── silence_detector.py         # Silence/pause detection module
├── init_database.py            # DuckDB schema initializer
├── view_database.py            # Database viewer/query tool
│
├── fluentai/                   # Installable core package
│   ├── __init__.py             # Exports LazyModelLoader
│   ├── model_loader.py         # Lazy-loading, LRU-cached model manager
│   ├── database_logger.py      # DuckDB logging (sessions, steps, latency)
│   ├── audio_utils.py          # Shared 16-bit PCM DSP (RMS normalize, AGC)
│   ├── transcription.py        # Shared chunked Whisper transcription
│   ├── app_controller.py       # Non-UI translation + text/language helpers (TranslationController)
│   ├── tts_engine.py           # TTS: macOS `say` fast path + synthesize-to-numpy fallback
│   ├── meeting_detector.py     # Mic-in-use auto-detection (CoreAudio, debounced MicMonitor)
│   ├── meeting_pipeline.py     # Two-stage streaming Meeting Mode (MeetingASRThread → MeetingSpeakThread)
│   ├── streaming_asr.py        # StreamingTranscriber: live captions via LocalAgreement-2
│   ├── asr_translation_synthesis_thread.py  # Legacy single ASR → Translation → TTS thread
│   ├── blackhole_reproduction_thread.py     # Audio output thread (jitter buffer)
│   ├── ui/
│   │   └── meeting_overlay.py  # Floating Meeting Mode overlay widget
│   └── cli/
│       ├── translate_rt.py     # Real-time translation CLI (multi-threaded)
│       └── README.md
│
├── conf/
│   └── languages.yaml          # Whisper/TTS language code mappings
│
├── tests/                      # pytest test suite (green: 72 passed, 3 skipped)
│   ├── test_meeting_detector.py
│   ├── test_meeting_pipeline.py
│   ├── test_streaming_asr.py
│   ├── test_tts_engine.py
│   ├── test_app_controller.py
│   ├── test_lazy_model_loader.py
│   ├── test_benchmarks.py
│   ├── test_silence_detection.py
│   └── test_asr_roundtrip.py
│
├── docs/                       # Architecture, usage, and roadmap docs
├── examples/                   # Audio device setup examples
├── scripts/                    # CI and demo scripts
├── bench/                      # Latency benchmarks
│
├── pyproject.toml              # Project metadata and deps
├── uv.lock                     # Pinned dependency lock file
└── .github/workflows/ci.yml    # CI/CD pipeline
```

---

## Development Environment

### Setup

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (including dev tools)
uv sync --extra dev
```

### Running the Application

```bash
# Recommended: GUI
uv run gui_app.py

# CLI (Whisper backend)
uv run main_whisper.py

# Real-time CLI translation (installed entry point, or run as a module)
uv run fluentai-rt --src es --dst en
python -m fluentai.cli.translate_rt --src es --dst en

# Live monitor dashboard (--db enables DuckDB logging)
uv run live_monitor.py
uv run live_monitor.py --db

# Initialize / view database
uv run init_database.py
uv run view_database.py [session_id]
```

---

## Commands Reference

### Linting & Formatting

```bash
# Lint
uv run ruff check .

# Format check
uv run ruff format --check .

# Auto-fix formatting
uv run ruff format .

# Type checking
uv run mypy fluentai/
```

### Testing

```bash
# Run all tests
uv run pytest tests/

# Run a specific file
uv run pytest tests/test_lazy_model_loader.py

# Run with verbose output
uv run pytest tests/ -v

# Run benchmarks
uv run pytest tests/test_benchmarks.py
```

Tests use `pytest` and `pytest-asyncio`. New code should pass before merging.

> **Baseline:** the suite is **green** — `uv run pytest tests/` reports
> **72 passed, 3 skipped** (the skips are environment-gated, e.g. hardware audio
> devices). `ruff check .` passes too. Keep it that way: run both before
> committing.

---

## Architecture

### Processing Pipeline

```
Microphone
    ↓
audio_capture_thread.py  (CircularAudioBuffer + WebRTC VAD)
    ↓  [queue: WAV segments]
asr_translation_synthesis_thread.py
    ├── Whisper ASR  →  transcript text
    ├── Helsinki-NLP MarianMT  →  translated text
    └── gTTS  →  synthesized audio
    ↓  [queue: audio bytes]
blackhole_reproduction_thread.py  (JitterBuffer → sounddevice output)
    ↓
Speaker / BlackHole virtual device
```

All inter-thread communication uses `queue.Queue` (non-blocking with timeout). The GUI orchestrates threads and receives updates via callbacks. The diagram above is the **legacy single-thread path** (`asr_translation_synthesis_thread.py`), still used by the basic translator.

### Meeting Mode (streaming, low-latency)

Meeting Mode is the current primary path. It's a **two-stage pipeline**
(`fluentai/meeting_pipeline.py`) so the next utterance is transcribed while the
current one is still being spoken:

```
audio_capture_thread.py  (emits WAV segments + opt-in growing snapshots)
    ↓ asr_queue
MeetingASRThread     Whisper (numpy in, no temp-WAV) → MarianMT translate
    ↓ speak_queue
MeetingSpeakThread   streams TTS via `say --audio-device` (blocking)
    ↓
Output device / BlackHole
```

- **Streaming captions** (`fluentai/streaming_asr.py`): `StreamingTranscriber`
  re-transcribes growing audio snapshots and commits only the word-prefix two
  consecutive passes agree on (**LocalAgreement-2**) — stable, flicker-free
  live text. Each completed sentence is translated and spoken immediately.
- **Streaming TTS** (`fluentai/tts_engine.py`): macOS `say --audio-device`
  starts audio in ~ms; `synthesize_to_numpy` + `sounddevice` is the non-macOS
  fallback.
- **Anti-hallucination**: Whisper runs with `condition_on_previous_text=False`,
  `temperature=0.0`, and no-speech/compression-ratio thresholds to curb looping
  on short clips.
- **Feedback-loop control**: a shared `mute_event` is held while speaking (plus
  a short echo-tail cooldown) so the capture thread never re-records our own TTS
  output (half-duplex).

### Meeting auto-detection (`fluentai/meeting_detector.py`)

macOS-only, dependency-free (pure ctypes into CoreAudio). Polls
`kAudioDevicePropertyDeviceIsRunningSomewhere` on the default input device —
True whenever *any* app grabs the mic (Zoom, Teams, browser Google Meet). A
debounced `MicMonitor` thread turns that into `on_call_started` /
`on_call_ended` callbacks (default 3s debounce each way). `is_available()` is
False off macOS and the monitor no-ops. The state machine (`_Debounce`) is pure
and deterministically unit-tested.

### Model Loading (`fluentai/model_loader.py`)

- Models are loaded **lazily** on first use.
- An **LRU cache** (default size 128) evicts least-recently-used models.
- Thread-safe: internal locks prevent duplicate loading.
- Supports progress callbacks for GUI loading bars.
- Whisper models: `base`, `small`, `medium`, `large`
- Translation models: 10 Helsinki-NLP OPUS-MT pairs across ES/EN/DE/FR.

```python
from fluentai import LazyModelLoader

loader = LazyModelLoader(progress_callback=my_callback)
model, tokenizer = loader.get_translation_model('es', 'en')
whisper_model = loader.get_whisper_model('base')
```

### Database Logging (`fluentai/database_logger.py`)

Two DuckDB tables:

| Table | Purpose |
|---|---|
| `translation_logs` | Per-step events (audio, ASR, translation, playback) |
| `translations` | Complete session summaries |

Both tables are auto-created on first connection. Use `view_database.py` for inspection.

Key fields: `session_id`, `step_type`, `latency_ms`, `model_used`, `errors[]`, `metadata` (JSON).

> **Note:** DB logging is active in `gui_app.py` (each completed translation is
> recorded via `log_complete_translation`, and Meeting Mode threads receive the
> GUI's `session_id`), in `live_monitor.py --db`, and in the pipeline threads.
> Logging is best-effort: if the logger can't initialize, the GUI still runs.

---

## Supported Language Pairs

The application supports bidirectional translation between:

| Pair | Model |
|---|---|
| Spanish ↔ English | `Helsinki-NLP/opus-mt-es-en`, `opus-mt-en-es` |
| Spanish ↔ German | `Helsinki-NLP/opus-mt-es-de`, `opus-mt-de-es` |
| Spanish ↔ French | `Helsinki-NLP/opus-mt-es-fr`, `opus-mt-fr-es` |
| English ↔ German | `Helsinki-NLP/opus-mt-en-de`, `opus-mt-de-en` |
| English ↔ French | `Helsinki-NLP/opus-mt-en-fr`, `opus-mt-fr-en` |

Language codes are configured in `conf/languages.yaml`.

---

## Key Conventions

### Code Style

- **Formatter/Linter**: Ruff (configured in `pyproject.toml`). Run `ruff format .` before committing.
- **Type hints**: Used throughout `fluentai/`. Add type hints to all new public functions. Run `mypy fluentai/` to check.
- **Docstrings**: Module-level and class-level docstrings are expected. Method docstrings for non-trivial logic.

### Threading

- All threads extend `threading.Thread` and override `run()`.
- Use `queue.Queue` for data passing — never shared mutable state without a lock.
- Use `threading.Event` for stop signals (see `self._stop_event.set()`).
- Timeouts on `queue.get()` calls prevent indefinite blocking.

### Error Handling

- Each thread catches exceptions internally and logs them to the database.
- Errors are stored as `errors: list[str]` in database rows, not raised to callers.
- Use `try/except` around all model inference calls (Whisper, translation, TTS).

### Audio

- Default sample rate: **16,000 Hz** (Whisper-optimized).
- Audio is stored as WAV bytes when passed through queues.
- `pydub.AudioSegment` is used for audio manipulation; `sounddevice` for I/O.
- VAD aggressiveness ranges 0–3 (WebRTC); default is 2.

### Database

- Never alter the DuckDB schema directly; update `init_database.py` for schema changes.
- `database_logger.py` is the only module that writes to DuckDB; do not query/write from other modules.
- All timestamps use UTC.

---

## CI/CD

**File**: `.github/workflows/ci.yml`

**Triggers**: Push or PR to `main` or `develop` branches.

**Steps**:
1. Install `uv` and Python 3.13
2. Install system deps: `libportaudio2`, `libasound2-dev`
3. `uv sync` all dependencies
4. `ruff check .` — must pass
5. `ruff format --check .` — must pass
6. Run `tests/test_silence_detection.py`
7. Run `tests/test_asr_roundtrip.py`
8. Run `tests/test_lazy_model_loader.py`
9. Run `tests/test_benchmarks.py`

Both lint and the test suite currently pass (see **Testing**), so CI is a real
gate again — keep `ruff check .` and `uv run pytest tests/` green before pushing.
Note the `.github/workflows/ci.yml` step list predates the streaming Meeting
Mode tests; the local `uv run pytest tests/` run is the source of truth.

---

## Common Development Tasks

### Adding a New Language Pair

1. Add the language code to `conf/languages.yaml`.
2. Add the model mapping in `fluentai/model_loader.py` → `TRANSLATION_MODELS` dict.
3. Update the GUI direction selector in `gui_app.py`.
4. Add tests in `tests/test_lazy_model_loader.py`.

### Adding a New Translation Step / Processing Stage

1. Create a new `threading.Thread` subclass following the pattern in `asr_translation_synthesis_thread.py`.
2. Add a new `queue.Queue` for its input/output.
3. Wire it in `gui_app.py` alongside existing threads.
4. Add logging calls via `database_logger.py`.

### Modifying the Database Schema

1. Update `init_database.py` with the new `CREATE TABLE` or `ALTER TABLE` statement.
2. Update `database_logger.py` to include the new fields in insert statements.
3. Update `view_database.py` if you want to display the new fields.
4. Increment the schema version comment at the top of `init_database.py`.

### Running a Benchmark

```bash
uv run pytest tests/test_benchmarks.py -v -s
```

Results include ASR latency, translation latency, TTS latency, and end-to-end latency per model size.

---

## External Dependencies Summary

| Library | Role |
|---|---|
| `openai-whisper` | Offline ASR (speech → text) |
| `transformers` | Helsinki-NLP MarianMT translation models |
| `torch` | PyTorch runtime for ML models |
| macOS `say` | Fast streaming TTS in Meeting Mode (built-in, no dep) |
| `gTTS` / `pyttsx3` | Text-to-Speech fallbacks (non-streaming / non-macOS) |
| `sounddevice` / `pyaudio` | Audio capture and playback |
| `soundfile` | Decode WAV bytes → numpy (no temp files) |
| `webrtcvad` | Voice Activity Detection |
| `pydub` | Audio manipulation (format conversion, normalization) |
| `librosa` | Audio feature extraction |
| `duckdb` | Embedded analytical database for logging |
| `sentencepiece` | Tokenization for MarianMT |
| `numpy` | Numerical array operations |
| CoreAudio (ctypes) | Mic-in-use auto-detection (macOS, no dep) |

---

## Files to Be Aware Of

| File | Why it matters |
|---|---|
| `gui_app.py` | Largest and most complex file (~1,520 lines); main user-facing code |
| `fluentai/meeting_pipeline.py` | The streaming Meeting Mode path (current focus); two-stage threads |
| `fluentai/streaming_asr.py` | Live captions; LocalAgreement-2 commit logic is subtle |
| `fluentai/meeting_detector.py` | Auto-trigger; raw CoreAudio ctypes — touch carefully |
| `fluentai/tts_engine.py` | Voice resolution + `say`/fallback selection per language |
| `fluentai/model_loader.py` | Central to performance; touch carefully (thread safety, caching) |
| `fluentai/database_logger.py` | Only writer to DuckDB; schema is defined implicitly here |
| `audio_capture_thread.py` | Audio quality begins here; VAD tuning impacts the entire pipeline |
| `silence_detector.py` | Controls when recordings auto-stop; has preset modes |
| `conf/languages.yaml` | Must stay in sync with `model_loader.py` language pair definitions |
| `docs/roadmap.md` | Product direction (menu-bar agent, branding, sequencing) |
| `uv.lock` | Do not edit manually; regenerate with `uv lock` |
