# CLAUDE.md — Fluent AI Codebase Guide

This file provides guidance for AI assistants (Claude, Copilot, etc.) working on the Fluent AI codebase.

---

## Project Overview

**Fluent AI** is a real-time, offline-capable bidirectional speech translation desktop application. It captures microphone audio, transcribes it with OpenAI Whisper, translates using Helsinki-NLP MarianMT models, synthesizes the translation via gTTS, and plays the output audio — all in a multi-threaded pipeline.

- **Primary interface**: Tkinter GUI (`gui_app.py`)
- **Python version**: 3.13+
- **Package manager**: `uv`
- **Database**: DuckDB (`translation_logs.duckdb`)

---

## Repository Layout

```
fluent-ai/
├── gui_app.py                  # Main GUI entry point (Tkinter, ~1,970 lines — God class, slated for decomposition)
├── main_whisper.py             # CLI entry point — Whisper ASR (~940 lines)
├── main.py                     # CLI entry point — Google Speech Recognition
├── live_monitor_with_db.py     # Real-time monitor with DB logging
├── live_monitor.py             # Real-time monitor (no DB)
├── audio_capture_thread.py     # Continuous mic capture + WebRTC VAD
├── silence_detector.py         # Silence/pause detection module
├── init_database.py            # DuckDB schema initializer
├── view_database.py            # Database viewer/query tool
│
├── fluentai/                   # Installable core package
│   ├── __init__.py             # Exports LazyModelLoader
│   ├── model_loader.py         # Lazy-loading, LRU-cached model manager
│   ├── database_logger.py      # DuckDB logging (sessions, steps, latency)
│   ├── asr_translation_synthesis_thread.py  # ASR → Translation → TTS thread
│   ├── blackhole_reproduction_thread.py     # Audio output thread (jitter buffer)
│   └── cli/
│       ├── translate_rt.py     # Real-time translation CLI (multi-threaded)
│       └── README.md
│
├── conf/
│   └── languages.yaml          # Whisper/TTS language code mappings
│
├── tests/                      # pytest test suite
│   ├── test_lazy_model_loader.py
│   ├── test_benchmarks.py
│   ├── test_silence_detection.py
│   └── test_asr_roundtrip.py
│
├── docs/                       # Architecture and usage documentation
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

# CLI (Google Speech backend)
uv run main.py

# Real-time CLI translation
python -m fluentai.cli.translate_rt --src es --dst en

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

> **Known-failing baseline (as of this writing):** the suite is not currently
> green. `tests/test_silence_detection.py` (WebRTC VAD frame-size mismatch),
> the mocked `tests/test_lazy_model_loader.py` cases (`Mock` no longer matches
> the `model_loader` API), and `tests/test_benchmarks.py` (missing `psutil`
> dependency) all fail. The non-mocked `tests/test_loader_metadata.py` passes.
> Fixing the suite is tracked cleanup — don't assume a green baseline.

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

All inter-thread communication uses `queue.Queue` (non-blocking with timeout). The GUI orchestrates threads and receives updates via callbacks.

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

> **Note:** DB logging is currently wired into the CLI / `live_monitor_with_db.py`
> path and the pipeline threads only. The flagship GUI (`gui_app.py`) does **not**
> yet import `database_logger`, so GUI sessions are not logged. Wiring this into the
> GUI is planned cleanup.

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

These steps are the intended gate, but the CI is currently aspirational: the
lint baseline was only recently greened, and several test files fail today (see
the known-failing note under **Testing**). Treat green CI as a goal, not a
guarantee, until the suite is repaired.

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
| `gTTS` | Google Text-to-Speech synthesis |
| `sounddevice` / `pyaudio` | Audio capture and playback |
| `webrtcvad` | Voice Activity Detection |
| `pydub` | Audio manipulation (format conversion, normalization) |
| `librosa` | Audio feature extraction |
| `duckdb` | Embedded analytical database for logging |
| `sentencepiece` | Tokenization for MarianMT |
| `numpy` | Numerical array operations |

---

## Files to Be Aware Of

| File | Why it matters |
|---|---|
| `gui_app.py` | Largest and most complex file (~1,970 lines); main user-facing code |
| `fluentai/model_loader.py` | Central to performance; touch carefully (thread safety, caching) |
| `fluentai/database_logger.py` | Only writer to DuckDB; schema is defined implicitly here |
| `audio_capture_thread.py` | Audio quality begins here; VAD tuning impacts the entire pipeline |
| `silence_detector.py` | Controls when recordings auto-stop; has preset modes |
| `conf/languages.yaml` | Must stay in sync with `model_loader.py` language pair definitions |
| `uv.lock` | Do not edit manually; regenerate with `uv lock` |
