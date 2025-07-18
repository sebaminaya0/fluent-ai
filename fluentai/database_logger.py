"""
Database Logger for FluentAI Translation Pipeline

This module provides logging capabilities to DuckDB for tracking all translation
operations across threads. It includes two main tables:
1. translation_logs - Detailed logs for each thread step
2. translations - Summary records for complete translation sessions
"""

import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import duckdb


class DatabaseLogger:
    """Thread-safe database logger for translation pipeline operations."""
    
    def __init__(self, db_path: str = "translation_logs.duckdb"):
        """
        Initialize the database logger.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize the database and create tables if they don't exist."""
        with self.lock:
            conn = duckdb.connect(self.db_path)
            try:
                # Create translation_logs table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS translation_logs (
                        id BIGINT PRIMARY KEY,
                        session_id VARCHAR NOT NULL,
                        thread_id INTEGER NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        step_type VARCHAR NOT NULL,
                        channel VARCHAR,
                        message TEXT,
                        latency_ms FLOAT,
                        model_used VARCHAR,
                        language VARCHAR,
                        errors VARCHAR[],
                        metadata JSON
                    )
                """)
                
                # Create translations table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS translations (
                        id BIGINT PRIMARY KEY,
                        session_id VARCHAR NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        input_language VARCHAR NOT NULL,
                        output_language VARCHAR NOT NULL,
                        input_channel VARCHAR,
                        output_channel VARCHAR,
                        full_message_input TEXT,
                        full_message_translated TEXT,
                        total_segments_audio INTEGER DEFAULT 0,
                        total_segments_asr INTEGER DEFAULT 0,
                        total_segments_output INTEGER DEFAULT 0,
                        model_used VARCHAR,
                        total_latency_ms FLOAT,
                        errors VARCHAR[],
                        metadata JSON
                    )
                """)
                
                # Create indexes for better query performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_translation_logs_session_id ON translation_logs(session_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_translation_logs_timestamp ON translation_logs(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_translations_session_id ON translations(session_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_translations_timestamp ON translations(timestamp)")
                
                print(f"Database initialized successfully at {self.db_path}")
                
            except Exception as e:
                print(f"Error initializing database: {e}")
                raise
            finally:
                conn.close()
    
    def log_audio_capture(self, 
                         session_id: str,
                         channel: str,
                         message: str,
                         latency_ms: float,
                         language: str = None,
                         errors: List[str] = None,
                         metadata: Dict[str, Any] = None):
        """
        Log audio capture thread activity.
        
        Args:
            session_id: Unique session identifier
            channel: Audio input channel/device
            message: Captured audio info or transcript
            latency_ms: Processing latency in milliseconds
            language: Detected or configured language
            errors: List of errors encountered
            metadata: Additional metadata (sample rate, duration, etc.)
        """
        self._log_thread_activity(
            session_id=session_id,
            thread_id=1,
            step_type="audio_capture",
            channel=channel,
            message=message,
            latency_ms=latency_ms,
            language=language,
            errors=errors or [],
            metadata=metadata or {}
        )
    
    def log_asr_translation(self,
                           session_id: str,
                           input_lang: str,
                           output_lang: str,
                           original_text: str,
                           translated_text: str,
                           model_used: str,
                           latency_ms: float,
                           errors: List[str] = None,
                           metadata: Dict[str, Any] = None):
        """
        Log ASR and translation thread activity.
        
        Args:
            session_id: Unique session identifier
            input_lang: Source language
            output_lang: Target language
            original_text: Original transcribed text
            translated_text: Translated text
            model_used: Model identifier used
            latency_ms: Processing latency in milliseconds
            errors: List of errors encountered
            metadata: Additional metadata
        """
        self._log_thread_activity(
            session_id=session_id,
            thread_id=2,
            step_type="asr_translation",
            channel=f"{input_lang}->{output_lang}",
            message=f"Original: {original_text} | Translated: {translated_text}",
            latency_ms=latency_ms,
            model_used=model_used,
            language=f"{input_lang}->{output_lang}",
            errors=errors or [],
            metadata=metadata or {}
        )
    
    def log_audio_playback(self,
                          session_id: str,
                          output_channel: str,
                          message: str,
                          latency_ms: float,
                          language: str = None,
                          errors: List[str] = None,
                          metadata: Dict[str, Any] = None):
        """
        Log audio playback thread activity.
        
        Args:
            session_id: Unique session identifier
            output_channel: Audio output channel/device
            message: Playback info or content
            latency_ms: Processing latency in milliseconds
            language: Audio language
            errors: List of errors encountered
            metadata: Additional metadata
        """
        self._log_thread_activity(
            session_id=session_id,
            thread_id=3,
            step_type="audio_playback",
            channel=output_channel,
            message=message,
            latency_ms=latency_ms,
            language=language,
            errors=errors or [],
            metadata=metadata or {}
        )
    
    def log_complete_translation(self,
                               session_id: str,
                               input_language: str,
                               output_language: str,
                               input_channel: str,
                               output_channel: str,
                               full_message_input: str,
                               full_message_translated: str,
                               total_segments_audio: int,
                               total_segments_asr: int,
                               total_segments_output: int,
                               model_used: str,
                               total_latency_ms: float,
                               errors: List[str] = None,
                               metadata: Dict[str, Any] = None):
        """
        Log a complete translation session.
        
        Args:
            session_id: Unique session identifier
            input_language: Source language
            output_language: Target language
            input_channel: Audio input channel
            output_channel: Audio output channel
            full_message_input: Complete input message
            full_message_translated: Complete translated message
            total_segments_audio: Number of audio segments captured
            total_segments_asr: Number of segments processed by ASR
            total_segments_output: Number of segments output
            model_used: Model identifier used
            total_latency_ms: Total end-to-end latency
            errors: List of errors encountered
            metadata: Additional metadata
        """
        with self.lock:
            conn = duckdb.connect(self.db_path)
            try:
                log_id = int(time.time() * 1000000)  # Microsecond timestamp as ID
                
                conn.execute("""
                    INSERT INTO translations (
                        id, session_id, input_language, output_language, input_channel, output_channel,
                        full_message_input, full_message_translated, total_segments_audio,
                        total_segments_asr, total_segments_output, model_used, total_latency_ms,
                        errors, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    log_id, session_id, input_language, output_language, input_channel, output_channel,
                    full_message_input, full_message_translated, total_segments_audio,
                    total_segments_asr, total_segments_output, model_used, total_latency_ms,
                    errors or [], metadata or {}
                ])
                
            except Exception as e:
                print(f"Error logging complete translation: {e}")
                raise
            finally:
                conn.close()
    
    def _log_thread_activity(self,
                           session_id: str,
                           thread_id: int,
                           step_type: str,
                           channel: str = None,
                           message: str = None,
                           latency_ms: float = None,
                           model_used: str = None,
                           language: str = None,
                           errors: List[str] = None,
                           metadata: Dict[str, Any] = None):
        """
        Internal method to log thread activity.
        
        Args:
            session_id: Unique session identifier
            thread_id: Thread identifier (1=capture, 2=asr/translation, 3=playback)
            step_type: Type of step being logged
            channel: Audio channel or device
            message: Log message
            latency_ms: Processing latency
            model_used: Model identifier
            language: Language information
            errors: List of errors
            metadata: Additional metadata
        """
        with self.lock:
            conn = duckdb.connect(self.db_path)
            try:
                log_id = int(time.time() * 1000000)  # Microsecond timestamp as ID
                
                conn.execute("""
                    INSERT INTO translation_logs (
                        id, session_id, thread_id, step_type, channel, message,
                        latency_ms, model_used, language, errors, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    log_id, session_id, thread_id, step_type, channel, message,
                    latency_ms, model_used, language, errors or [], metadata or {}
                ])
                
            except Exception as e:
                print(f"Error logging thread activity: {e}")
                raise
            finally:
                conn.close()
    
    def get_session_logs(self, session_id: str) -> List[Dict]:
        """
        Get all logs for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of log records
        """
        with self.lock:
            conn = duckdb.connect(self.db_path)
            try:
                result = conn.execute(
                    "SELECT * FROM translation_logs WHERE session_id = ? ORDER BY timestamp",
                    [session_id]
                ).fetchall()
                
                columns = [desc[0] for desc in conn.description]
                return [dict(zip(columns, row)) for row in result]
                
            except Exception as e:
                print(f"Error getting session logs: {e}")
                return []
            finally:
                conn.close()
    
    def get_translation_summary(self, session_id: str) -> Optional[Dict]:
        """
        Get translation summary for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Translation summary record or None
        """
        with self.lock:
            conn = duckdb.connect(self.db_path)
            try:
                result = conn.execute(
                    "SELECT * FROM translations WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1",
                    [session_id]
                ).fetchone()
                
                if result:
                    columns = [desc[0] for desc in conn.description]
                    return dict(zip(columns, result))
                return None
                
            except Exception as e:
                print(f"Error getting translation summary: {e}")
                return None
            finally:
                conn.close()
    
    def get_recent_translations(self, limit: int = 10) -> List[Dict]:
        """
        Get recent translation summaries.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recent translation records
        """
        with self.lock:
            conn = duckdb.connect(self.db_path)
            try:
                result = conn.execute(
                    "SELECT * FROM translations ORDER BY timestamp DESC LIMIT ?",
                    [limit]
                ).fetchall()
                
                columns = [desc[0] for desc in conn.description]
                return [dict(zip(columns, row)) for row in result]
                
            except Exception as e:
                print(f"Error getting recent translations: {e}")
                return []
            finally:
                conn.close()
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up logs older than specified number of days.
        
        Args:
            days_to_keep: Number of days to keep logs
        """
        with self.lock:
            conn = duckdb.connect(self.db_path)
            try:
                # Delete old translation logs
                conn.execute(
                    "DELETE FROM translation_logs WHERE timestamp < NOW() - INTERVAL ? DAY",
                    [days_to_keep]
                )
                
                # Delete old translation summaries
                conn.execute(
                    "DELETE FROM translations WHERE timestamp < NOW() - INTERVAL ? DAY",
                    [days_to_keep]
                )
                
                print(f"Cleaned up logs older than {days_to_keep} days")
                
            except Exception as e:
                print(f"Error cleaning up logs: {e}")
                raise
            finally:
                conn.close()


# Global database logger instance
db_logger = DatabaseLogger()


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def get_device_name(device_id: int) -> str:
    """Get device name from device ID."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if 0 <= device_id < len(devices):
            return devices[device_id]['name']
        return f"Device_{device_id}"
    except Exception:
        return f"Device_{device_id}"
