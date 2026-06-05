#!/usr/bin/env python3
"""
Database viewer for FluentAI translation logs
View and analyze data stored in the DuckDB database
"""

import json

import duckdb


def connect_to_database(db_path: str = "translation_logs.duckdb"):
    """Connect to the DuckDB database"""
    return duckdb.connect(db_path)


def view_recent_logs(limit: int = 10):
    """View recent translation logs"""
    conn = connect_to_database()
    try:
        print(f"📊 Recent {limit} Translation Logs:")
        print("=" * 80)

        logs = conn.execute(f"""
            SELECT session_id, thread_id, timestamp, step_type, channel, message,
                   latency_ms, model_used, language, errors, metadata
            FROM translation_logs
            ORDER BY timestamp DESC
            LIMIT {limit}
        """).fetchall()

        for log in logs:
            (
                session_id,
                thread_id,
                timestamp,
                step_type,
                channel,
                message,
                latency_ms,
                model_used,
                language,
                errors,
                metadata,
            ) = log
            thread_name = {1: "🎤 Audio", 2: "🧠 ASR", 3: "🔊 Output"}[thread_id]

            print(f"\n{thread_name} | {timestamp}")
            print(f"Session: {session_id}")
            print(f"Message: {message}")
            if channel:
                print(f"Channel: {channel}")
            if language:
                print(f"Language: {language}")
            if model_used:
                print(f"Model: {model_used}")
            if latency_ms:
                print(f"Latency: {latency_ms:.2f}ms")
            if errors:
                print(f"⚠️  Errors: {errors}")
            if metadata:
                print(f"Metadata: {json.dumps(metadata, indent=2)}")
            print("-" * 40)

    finally:
        conn.close()


def view_recent_translations(limit: int = 5):
    """View recent complete translations"""
    conn = connect_to_database()
    try:
        print(f"\n🌍 Recent {limit} Complete Translations:")
        print("=" * 80)

        translations = conn.execute(f"""
            SELECT session_id, timestamp, input_language, output_language,
                   input_channel, output_channel, full_message_input,
                   full_message_translated, total_segments_audio,
                   total_segments_asr, total_segments_output, model_used,
                   total_latency_ms, errors, metadata
            FROM translations
            ORDER BY timestamp DESC
            LIMIT {limit}
        """).fetchall()

        for i, translation in enumerate(translations, 1):
            (
                session_id,
                timestamp,
                input_lang,
                output_lang,
                input_channel,
                output_channel,
                input_msg,
                output_msg,
                seg_audio,
                seg_asr,
                seg_output,
                model,
                latency,
                errors,
                metadata,
            ) = translation

            print(f"\n{i}. Translation | {timestamp}")
            print(f"Session: {session_id}")
            print(f"🗣️  Input ({input_lang}): {input_msg}")
            print(f"🌍 Output ({output_lang}): {output_msg}")
            print(f"📥 Input Channel: {input_channel}")
            print(f"📤 Output Channel: {output_channel}")
            print(f"🔧 Model: {model}")
            print(f"⏱️  Total Latency: {latency:.2f}ms")
            print(f"📊 Segments: Audio={seg_audio}, ASR={seg_asr}, Output={seg_output}")
            if errors:
                print(f"⚠️  Errors: {errors}")
            print("-" * 40)

    finally:
        conn.close()


def view_session_summary(session_id: str):
    """View detailed summary for a specific session"""
    conn = connect_to_database()
    try:
        print(f"📋 Session Summary: {session_id}")
        print("=" * 80)

        # Get session logs
        logs = conn.execute(
            """
            SELECT thread_id, step_type, timestamp, message, latency_ms, errors
            FROM translation_logs
            WHERE session_id = ?
            ORDER BY timestamp
        """,
            [session_id],
        ).fetchall()

        if not logs:
            print("❌ No logs found for this session")
            return

        # Group by thread
        audio_logs = [log for log in logs if log[0] == 1]
        asr_logs = [log for log in logs if log[0] == 2]
        output_logs = [log for log in logs if log[0] == 3]

        print("📊 Log Summary:")
        print(f"   🎤 Audio Capture: {len(audio_logs)} logs")
        print(f"   🧠 ASR/Translation: {len(asr_logs)} logs")
        print(f"   🔊 Audio Output: {len(output_logs)} logs")

        # Calculate average latencies
        if audio_logs:
            avg_audio_latency = sum(log[4] or 0 for log in audio_logs) / len(audio_logs)
            print(f"   🎤 Avg Audio Latency: {avg_audio_latency:.2f}ms")

        if asr_logs:
            avg_asr_latency = sum(log[4] or 0 for log in asr_logs) / len(asr_logs)
            print(f"   🧠 Avg ASR Latency: {avg_asr_latency:.2f}ms")

        if output_logs:
            avg_output_latency = sum(log[4] or 0 for log in output_logs) / len(
                output_logs
            )
            print(f"   🔊 Avg Output Latency: {avg_output_latency:.2f}ms")

        # Show errors
        error_logs = [log for log in logs if log[5]]
        if error_logs:
            print(f"\n⚠️  Errors ({len(error_logs)}):")
            for log in error_logs:
                thread_name = {1: "Audio", 2: "ASR", 3: "Output"}[log[0]]
                print(f"   [{thread_name}] {log[5]}")

        # Get translation summary
        translation = conn.execute(
            """
            SELECT input_language, output_language, full_message_input,
                   full_message_translated, total_latency_ms
            FROM translations
            WHERE session_id = ?
        """,
            [session_id],
        ).fetchone()

        if translation:
            print("\n🌍 Translation Summary:")
            print(f"   Languages: {translation[0]} → {translation[1]}")
            print(f"   Input: {translation[2]}")
            print(f"   Output: {translation[3]}")
            print(f"   Total Latency: {translation[4]:.2f}ms")

    finally:
        conn.close()


def view_statistics():
    """View overall database statistics"""
    conn = connect_to_database()
    try:
        print("📈 Database Statistics:")
        print("=" * 80)

        # Total counts
        total_logs = conn.execute("SELECT COUNT(*) FROM translation_logs").fetchone()[0]
        total_translations = conn.execute(
            "SELECT COUNT(*) FROM translations"
        ).fetchone()[0]
        total_sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM translation_logs"
        ).fetchone()[0]

        print("📊 Total Records:")
        print(f"   Translation Logs: {total_logs}")
        print(f"   Complete Translations: {total_translations}")
        print(f"   Unique Sessions: {total_sessions}")

        # Language pairs
        lang_pairs = conn.execute("""
            SELECT input_language || ' → ' || output_language as lang_pair, COUNT(*) as count
            FROM translations
            GROUP BY input_language, output_language
            ORDER BY count DESC
        """).fetchall()

        if lang_pairs:
            print("\n🌍 Language Pairs:")
            for pair, count in lang_pairs:
                print(f"   {pair}: {count} translations")

        # Error statistics
        error_count = conn.execute(
            "SELECT COUNT(*) FROM translation_logs WHERE errors IS NOT NULL AND array_length(errors) > 0"
        ).fetchone()[0]
        if error_count > 0:
            print(f"\n⚠️  Errors: {error_count} logs with errors")

        # Recent activity
        recent_activity = conn.execute("""
            SELECT DATE_TRUNC('day', timestamp) as date, COUNT(*) as count
            FROM translation_logs
            WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE_TRUNC('day', timestamp)
            ORDER BY date DESC
        """).fetchall()

        if recent_activity:
            print("\n📅 Recent Activity (last 7 days):")
            for date, count in recent_activity:
                print(f"   {date}: {count} logs")

    finally:
        conn.close()


def main():
    """Main function to run the database viewer"""
    print("🗄️  FluentAI Translation Database Viewer")
    print("=" * 50)

    # Check if database exists
    try:
        conn = connect_to_database()
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Run 'uv run init_database.py' to create the database")
        return

    # Show statistics
    view_statistics()

    # Show recent logs
    view_recent_logs(limit=10)

    # Show recent translations
    view_recent_translations(limit=5)

    print("\n💡 Usage:")
    print("   - View specific session: python view_database.py <session_id>")
    print("   - Direct SQL queries: duckdb translation_logs.duckdb")
    print("   - Example queries:")
    print("     SELECT * FROM translation_logs WHERE thread_id = 2;")
    print("     SELECT session_id, COUNT(*) FROM translation_logs GROUP BY session_id;")
    print("     SELECT * FROM translations WHERE total_latency_ms > 1000;")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        view_session_summary(session_id)
    else:
        main()
