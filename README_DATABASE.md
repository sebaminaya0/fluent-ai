# FluentAI Database Logging System

## Overview

The FluentAI real-time translation pipeline now includes comprehensive database logging using DuckDB. All translation operations are logged across three main threads with detailed timing, error tracking, and metadata.

## Database Schema

### Tables Created

1. **`translation_logs`** - Detailed logs for each thread step
2. **`translations`** - Summary records for complete translation sessions

### Schema Details

#### translation_logs Table
- `id` (BIGINT) - Unique log identifier
- `session_id` (VARCHAR) - Session identifier linking related logs
- `thread_id` (INTEGER) - Thread identifier (1=Audio, 2=ASR, 3=Output)
- `timestamp` (TIMESTAMP) - When the log was created
- `step_type` (VARCHAR) - Type of operation (audio_capture, asr_translation, audio_playback)
- `channel` (VARCHAR) - Input/output channel or device name
- `message` (TEXT) - Log message describing the operation
- `latency_ms` (FLOAT) - Processing latency in milliseconds
- `model_used` (VARCHAR) - Model identifier used
- `language` (VARCHAR) - Language information
- `errors` (VARCHAR[]) - Array of error messages
- `metadata` (JSON) - Additional metadata (duration, samples, etc.)

#### translations Table
- `id` (BIGINT) - Unique translation identifier
- `session_id` (VARCHAR) - Session identifier
- `timestamp` (TIMESTAMP) - When the translation was completed
- `input_language` (VARCHAR) - Source language code
- `output_language` (VARCHAR) - Target language code
- `input_channel` (VARCHAR) - Input device/channel
- `output_channel` (VARCHAR) - Output device/channel
- `full_message_input` (TEXT) - Complete input message
- `full_message_translated` (TEXT) - Complete translated message
- `total_segments_audio` (INTEGER) - Number of audio segments captured
- `total_segments_asr` (INTEGER) - Number of segments processed by ASR
- `total_segments_output` (INTEGER) - Number of segments output
- `model_used` (VARCHAR) - Primary model used
- `total_latency_ms` (FLOAT) - Total end-to-end latency
- `errors` (VARCHAR[]) - Array of accumulated errors
- `metadata` (JSON) - Additional session metadata

## Files Created

### Core Database Module
- `fluentai/database_logger.py` - Main database logging functionality
  - `DatabaseLogger` class with thread-safe logging
  - Logging methods for each thread type
  - Query methods for retrieving logs
  - Database initialization and cleanup

### Scripts
- `init_database.py` - Initialize database and run tests
- `view_database.py` - View and analyze database contents
- `live_monitor_with_db.py` - Enhanced live monitor with database logging

### Updated Threads
- `audio_capture_thread.py` - Now logs audio capture operations
- `fluentai/asr_translation_synthesis_thread.py` - Now logs ASR and translation operations
- `fluentai/blackhole_reproduction_thread.py` - Now logs audio playback operations

## Usage

### 1. Initialize Database
```bash
uv run init_database.py
```

### 2. Run Live Monitor with Database Logging
```bash
uv run live_monitor_with_db.py
```

### 3. View Database Contents
```bash
# View all data
uv run view_database.py

# View specific session
uv run view_database.py <session_id>
```

### 4. Direct Database Queries
```bash
# Open DuckDB CLI
duckdb translation_logs.duckdb

# Example queries
SELECT * FROM translation_logs ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM translations WHERE total_latency_ms > 1000;
SELECT session_id, COUNT(*) FROM translation_logs GROUP BY session_id;
```

## What Gets Logged

### Thread 1: Audio Capture
- Audio segment capture with duration and sample count
- Voice activity detection events
- Queue full errors and dropped recordings
- Processing latency and metadata

### Thread 2: ASR Translation Synthesis
- Whisper transcription results
- Translation operations (when languages differ)
- Text-to-speech synthesis
- Model loading and processing errors
- Full processing latency

### Thread 3: Audio Playback
- Audio chunks played through output device
- Playback latency and chunk sizes
- Audio format conversion operations
- Device-specific errors

## Features

### Logging Capabilities
- **Thread-safe**: All logging operations are thread-safe
- **Session tracking**: Each run gets a unique session ID
- **Error aggregation**: Multiple errors are collected in arrays
- **Metadata storage**: Rich metadata in JSON format
- **Timing precision**: Millisecond-level latency tracking

### Query Capabilities
- **Session logs**: Get all logs for a specific session
- **Translation summaries**: Get complete translation records
- **Recent activity**: View recent logs and translations
- **Error analysis**: Filter and analyze error patterns
- **Performance metrics**: Calculate average latencies

### Database Features
- **Indexes**: Optimized indexes for common queries
- **Cleanup**: Built-in log cleanup functionality
- **Portability**: Single DuckDB file for easy sharing
- **SQL compatibility**: Standard SQL queries supported

## Example Log Flow

1. **Audio Capture**: User speaks → VAD triggers → audio segment captured → logged
2. **ASR Translation**: Audio processed → Whisper transcribes → MarianMT translates → logged
3. **Audio Playback**: TTS generates audio → played through BlackHole → logged
4. **Complete Translation**: Full session summary logged

## Testing

The system includes comprehensive tests:
- Database initialization verification
- All logging methods tested
- Query functionality verified
- Error handling tested
- Sample data generation

## Benefits

1. **Debugging**: Detailed logs help identify issues in the pipeline
2. **Performance**: Latency tracking helps optimize performance
3. **Analytics**: Historical data for usage patterns
4. **Reliability**: Error tracking helps improve system reliability
5. **Audit Trail**: Complete record of all translation operations

## Database File

The database is stored as `translation_logs.duckdb` in the project root. This file:
- Contains all logs and translations
- Can be backed up and restored easily
- Can be analyzed with any DuckDB-compatible tool
- Grows automatically as data is added

## Next Steps

1. Run the live monitor with database logging
2. Speak in Spanish to generate real translation logs
3. Use the database viewer to analyze the results
4. Query the database directly for detailed analysis

The system is now ready for production use with comprehensive logging and analysis capabilities!
