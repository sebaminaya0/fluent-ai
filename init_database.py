#!/usr/bin/env python3
"""
Initialize DuckDB database for FluentAI translation logging
This script creates the database, tables, and tests the logging functionality
"""

import time
from datetime import datetime
from fluentai.database_logger import db_logger, generate_session_id

def test_database_functionality():
    """Test all database logging functionality"""
    print("🚀 Testing FluentAI Database Logging System")
    print("=" * 50)
    
    # Generate a test session ID
    session_id = generate_session_id()
    print(f"📝 Generated test session ID: {session_id}")
    
    # Test 1: Audio capture logging
    print("\n1️⃣ Testing audio capture logging...")
    db_logger.log_audio_capture(
        session_id=session_id,
        channel="MacBook Pro Microphone",
        message="Test audio capture: 2.5s audio (40,000 samples)",
        latency_ms=150.5,
        language="es",
        metadata={
            "duration": 2.5,
            "samples": 40000,
            "sample_rate": 16000,
            "wav_size": 80000
        }
    )
    print("✅ Audio capture log created")
    
    # Test 2: ASR translation logging
    print("\n2️⃣ Testing ASR translation logging...")
    db_logger.log_asr_translation(
        session_id=session_id,
        input_lang="es",
        output_lang="en",
        original_text="Hola, ¿cómo estás?",
        translated_text="Hello, how are you?",
        model_used="whisper-base",
        latency_ms=850.2,
        metadata={
            "audio_duration": 2.5,
            "audio_samples": 40000,
            "output_samples": 132300
        }
    )
    print("✅ ASR translation log created")
    
    # Test 3: Audio playback logging
    print("\n3️⃣ Testing audio playback logging...")
    db_logger.log_audio_playback(
        session_id=session_id,
        output_channel="BlackHole 2ch",
        message="Played 132,300 samples",
        latency_ms=45.8,
        language="en",
        metadata={
            "sample_rate": 44100,
            "audio_samples": 132300,
            "chunk_size": 1024
        }
    )
    print("✅ Audio playback log created")
    
    # Test 4: Complete translation logging
    print("\n4️⃣ Testing complete translation logging...")
    db_logger.log_complete_translation(
        session_id=session_id,
        input_language="es",
        output_language="en",
        input_channel="MacBook Pro Microphone",
        output_channel="BlackHole 2ch",
        full_message_input="Hola, ¿cómo estás?",
        full_message_translated="Hello, how are you?",
        total_segments_audio=1,
        total_segments_asr=1,
        total_segments_output=1,
        model_used="whisper-base",
        total_latency_ms=1046.5,
        metadata={
            "source_language": "es",
            "target_language": "en",
            "session_start": datetime.now().isoformat()
        }
    )
    print("✅ Complete translation log created")
    
    # Test 5: Error logging
    print("\n5️⃣ Testing error logging...")
    db_logger.log_audio_capture(
        session_id=session_id,
        channel="MacBook Pro Microphone",
        message="Queue full, dropped recording",
        latency_ms=0,
        errors=["Queue full - recording dropped", "Timeout after 50ms"]
    )
    print("✅ Error log created")
    
    # Test 6: Retrieve session logs
    print("\n6️⃣ Testing log retrieval...")
    session_logs = db_logger.get_session_logs(session_id)
    print(f"✅ Retrieved {len(session_logs)} logs for session")
    
    # Display the logs
    print("\n📊 Retrieved Logs:")
    print("-" * 40)
    for i, log in enumerate(session_logs, 1):
        thread_name = {1: "Audio", 2: "ASR", 3: "Output"}[log['thread_id']]
        print(f"{i}. [{thread_name}] {log['message']}")
        if log['errors']:
            print(f"   ⚠️  Errors: {log['errors']}")
        print(f"   ⏱️  Latency: {log['latency_ms']}ms")
        print()
    
    # Test 7: Retrieve translation summary
    print("7️⃣ Testing translation summary retrieval...")
    translation_summary = db_logger.get_translation_summary(session_id)
    if translation_summary:
        print("✅ Translation summary retrieved:")
        print(f"   Input: {translation_summary['full_message_input']}")
        print(f"   Output: {translation_summary['full_message_translated']}")
        print(f"   Languages: {translation_summary['input_language']} → {translation_summary['output_language']}")
        print(f"   Total latency: {translation_summary['total_latency_ms']}ms")
    else:
        print("❌ No translation summary found")
    
    # Test 8: Recent translations
    print("\n8️⃣ Testing recent translations retrieval...")
    recent_translations = db_logger.get_recent_translations(limit=5)
    print(f"✅ Retrieved {len(recent_translations)} recent translations")
    
    print("\n🎉 All database tests completed successfully!")
    print(f"📁 Database file: translation_logs.duckdb")
    print(f"🆔 Test session ID: {session_id}")
    
    return session_id

def show_database_info():
    """Show database schema and basic info"""
    print("\n📋 Database Schema Information:")
    print("-" * 40)
    
    try:
        import duckdb
        conn = duckdb.connect('translation_logs.duckdb')
        
        # Show tables
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"📊 Tables: {[table[0] for table in tables]}")
        
        # Show translation_logs schema
        print("\n🗂️  translation_logs table schema:")
        schema = conn.execute("DESCRIBE translation_logs").fetchall()
        for column in schema:
            print(f"   {column[0]}: {column[1]}")
        
        print("\n🗂️  translations table schema:")
        schema = conn.execute("DESCRIBE translations").fetchall()
        for column in schema:
            print(f"   {column[0]}: {column[1]}")
        
        # Show row counts
        log_count = conn.execute("SELECT COUNT(*) FROM translation_logs").fetchone()[0]
        translation_count = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
        
        print(f"\n📈 Current data:")
        print(f"   translation_logs: {log_count} rows")
        print(f"   translations: {translation_count} rows")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")

if __name__ == "__main__":
    print("🔧 Initializing FluentAI Translation Database...")
    print("=" * 50)
    
    # Test database functionality
    test_session_id = test_database_functionality()
    
    # Show database info
    show_database_info()
    
    print("\n✅ Database initialization complete!")
    print("\n💡 Next steps:")
    print("   1. Run: uv run live_monitor_with_db.py")
    print("   2. Speak in Spanish to test the system")
    print("   3. Check the database logs")
    print("\n🔍 To view the database:")
    print("   - Use DuckDB CLI: duckdb translation_logs.duckdb")
    print("   - Query logs: SELECT * FROM translation_logs ORDER BY timestamp DESC LIMIT 10;")
    print("   - Query translations: SELECT * FROM translations ORDER BY timestamp DESC LIMIT 5;")
