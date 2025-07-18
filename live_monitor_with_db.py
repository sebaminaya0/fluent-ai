#!/usr/bin/env python3
"""
Enhanced Live monitoring dashboard for FluentAI real-time translation pipeline
Shows queue states, processing activity, and logs all data to DuckDB
"""
import time
import threading
import queue
import os
import sys
from datetime import datetime
from audio_capture_thread import AudioCaptureThread
from fluentai.asr_translation_synthesis_thread import ASRTranslationSynthesisThread
from fluentai.blackhole_reproduction_thread import BlackHoleReproductionThread
from fluentai.database_logger import db_logger, generate_session_id

class LiveMonitorWithDB:
    def __init__(self):
        self.running = True
        self.asr_queue = queue.Queue(maxsize=10)
        self.output_queue = queue.Queue(maxsize=10)
        
        # Generate session ID for this run
        self.session_id = generate_session_id()
        
        # Performance counters
        self.audio_segments_captured = 0
        self.audio_segments_processed = 0
        self.audio_segments_played = 0
        self.last_transcription = ""
        self.last_translation = ""
        self.last_activity = "Starting..."
        self.current_audio_length = 0
        self.is_recording = False
        
        # Thread references
        self.capture_thread = None
        self.asr_thread = None
        self.blackhole_thread = None
        
        # Lock for thread-safe updates
        self.stats_lock = threading.Lock()
        
        # Complete translation tracking
        self.complete_translations = []
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def create_progress_bar(self, current, max_val, width=20):
        """Create a simple progress bar"""
        if max_val == 0:
            return "█" * width
        
        filled = int(width * current / max_val)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {current}/{max_val}"
        
    def get_queue_visual(self, queue_obj, max_size=10):
        """Create a visual representation of queue state"""
        current_size = queue_obj.qsize()
        return self.create_progress_bar(current_size, max_size, width=15)
        
    def start_threads(self):
        """Start all processing threads"""
        try:
            # Audio capture thread
            self.capture_thread = AudioCaptureThread(
                asr_queue=self.asr_queue,
                sample_rate=16000,
                vad_aggressiveness=2,
                voice_threshold_ms=200,
                silence_threshold_ms=400
            )
            self.capture_thread.set_session_id(self.session_id)
            self.capture_thread.start()
            
            # ASR + Translation + Synthesis thread
            self.asr_thread = ASRTranslationSynthesisThread(
                queue_in=self.asr_queue,
                queue_out=self.output_queue,
                src_lang='es',
                dst_lang='en',
                whisper_model='base'
            )
            self.asr_thread.set_session_id(self.session_id)
            self.asr_thread.start()
            
            # BlackHole reproduction thread
            self.blackhole_thread = BlackHoleReproductionThread(
                output_device=1,  # BlackHole device
                input_queue=self.output_queue,
                sample_rate=44100
            )
            self.blackhole_thread.set_session_id(self.session_id)
            self.blackhole_thread.start()
            
            self.last_activity = "All threads started successfully"
            return True
            
        except Exception as e:
            self.last_activity = f"Error starting threads: {e}"
            return False
            
    def stop_threads(self):
        """Stop all threads"""
        if self.capture_thread:
            self.capture_thread.stop()
        if self.asr_thread:
            self.asr_thread.stop()
        if self.blackhole_thread:
            self.blackhole_thread.stop()
            
    def update_stats(self):
        """Update performance statistics"""
        # These would be updated by thread callbacks in a real implementation
        # For now, we'll estimate based on queue changes
        pass
        
    def render_dashboard(self):
        """Render the live dashboard"""
        self.clear_screen()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("=" * 80)
        print("🎙️  FluentAI Real-time Translation - Live Monitor with Database")
        print("=" * 80)
        print(f"⏰ Time: {now}")
        print(f"🗄️  Session ID: {self.session_id}")
        print(f"📊 Status: {self.last_activity}")
        print()
        
        # Queue visualization
        print("📋 QUEUE STATES:")
        print("-" * 40)
        asr_size = self.asr_queue.qsize()
        output_size = self.output_queue.qsize()
        
        print(f"🎤 Audio Capture → ASR Queue:")
        print(f"   Size: {asr_size}/10  {self.get_queue_visual(self.asr_queue)}")
        print(f"   📈 Segments captured: {self.audio_segments_captured}")
        print()
        
        print(f"🧠 ASR → Audio Output Queue:")
        print(f"   Size: {output_size}/10  {self.get_queue_visual(self.output_queue)}")
        print(f"   📈 Segments processed: {self.audio_segments_processed}")
        print()
        
        print(f"🔊 BlackHole Audio Output:")
        print(f"   📈 Segments played: {self.audio_segments_played}")
        print()
        
        # Processing activity
        print("🔄 PROCESSING ACTIVITY:")
        print("-" * 40)
        
        # Show queue activity indicators
        activity_indicators = {
            "🎤 Audio Capture": "🟢 ACTIVE" if asr_size > 0 or self.audio_segments_captured > 0 else "🔴 WAITING",
            "🧠 ASR Processing": "🟢 ACTIVE" if output_size > 0 or self.audio_segments_processed > 0 else "🔴 WAITING", 
            "🔊 Audio Output": "🟢 ACTIVE" if self.audio_segments_played > 0 else "🔴 WAITING"
        }
        
        for process, status in activity_indicators.items():
            print(f"{process}: {status}")
        print()
        
        # Latest transcription/translation
        print("📝 LATEST RESULTS:")
        print("-" * 40)
        print(f"🗣️  Transcription: {self.last_transcription or 'Waiting for speech...'}")
        print(f"🌍 Translation: {self.last_translation or 'Waiting for speech...'}")
        print()
        
        # Database information
        print("🗄️  DATABASE LOGGING:")
        print("-" * 40)
        recent_logs = db_logger.get_session_logs(self.session_id)
        if recent_logs:
            print(f"📈 Total logs this session: {len(recent_logs)}")
            # Show last few logs
            for log in recent_logs[-3:]:
                timestamp = log['timestamp']
                thread_name = {1: "Audio", 2: "ASR", 3: "Output"}[log['thread_id']]
                print(f"   {timestamp}: {thread_name} - {log['message'][:50]}...")
        else:
            print("📈 No logs recorded yet")
        print()
        
        # Instructions
        print("💡 INSTRUCTIONS:")
        print("-" * 40)
        print("• Speak in Spanish to see real-time translation")
        print("• All operations are logged to DuckDB database")
        print("• Watch the queue bars fill up as audio is processed")
        print("• Audio will play through BlackHole device")
        print("• Press Ctrl+C to stop")
        print()
        
        # Real-time queue flow animation
        flow_chars = ["▶", "▶▶", "▶▶▶", "▶▶▶▶"]
        flow_idx = int(time.time() * 3) % len(flow_chars)
        
        # Add pulsing effect for active queues
        asr_pulse = "🟡" if asr_size > 0 else "⚪"
        output_pulse = "🟡" if output_size > 0 else "⚪"
        
        print("🔄 REAL-TIME FLOW:")
        print("-" * 40)
        flow_visual = f"🎤 Audio {flow_chars[flow_idx]} {asr_pulse} ASR {flow_chars[flow_idx]} {output_pulse} Output"
        print(flow_visual)
        print()
        
        # Add instant queue change indicator
        if asr_size > 0:
            print("⚡ LIVE ACTIVITY: Audio being processed...")
        elif output_size > 0:
            print("⚡ LIVE ACTIVITY: Playing translated audio...")
        else:
            print("⚡ LIVE ACTIVITY: Waiting for speech...")
        print()
        
        print("=" * 80)
        
    def count_segments(self):
        """Background thread to count processed segments"""
        last_asr_size = 0
        last_output_size = 0
        
        while self.running:
            try:
                current_asr = self.asr_queue.qsize()
                current_output = self.output_queue.qsize()
                
                # Count segments based on queue changes
                with self.stats_lock:
                    # Audio segments captured (when ASR queue increases)
                    if current_asr > last_asr_size:
                        self.audio_segments_captured += (current_asr - last_asr_size)
                        self.last_activity = f"Audio segment captured! Queue size: {current_asr}"
                        
                    # Audio segments processed (when output queue increases)
                    if current_output > last_output_size:
                        self.audio_segments_processed += (current_output - last_output_size)
                        self.last_activity = f"Audio processed! Output queue size: {current_output}"
                        
                    # Audio segments played (when output queue decreases)
                    if current_output < last_output_size:
                        self.audio_segments_played += (last_output_size - current_output)
                        self.last_activity = f"Audio played! Queue size: {current_output}"
                
                last_asr_size = current_asr
                last_output_size = current_output
                
                time.sleep(0.1)
                
            except:
                break
    
    def log_complete_translation(self, input_text, translated_text):
        """Log a complete translation to the database"""
        try:
            db_logger.log_complete_translation(
                session_id=self.session_id,
                input_language='es',
                output_language='en',
                input_channel='MacBook Pro Microphone',
                output_channel='BlackHole 2ch',
                full_message_input=input_text,
                full_message_translated=translated_text,
                total_segments_audio=self.audio_segments_captured,
                total_segments_asr=self.audio_segments_processed,
                total_segments_output=self.audio_segments_played,
                model_used='whisper-base',
                total_latency_ms=0,  # This would be calculated from actual timings
                metadata={
                    'source_language': 'es',
                    'target_language': 'en',
                    'session_start': datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Error logging complete translation: {e}")
                
    def run(self):
        """Run the live monitor"""
        print("🚀 Starting FluentAI Live Monitor with Database Logging...")
        print("Loading models and initializing threads...")
        
        if not self.start_threads():
            print("❌ Failed to start threads")
            return
            
        # Start background counter thread
        counter_thread = threading.Thread(target=self.count_segments, daemon=True)
        counter_thread.start()
        
        try:
            while self.running:
                self.render_dashboard()
                time.sleep(0.5)  # Update every 0.5 seconds for more responsiveness
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping live monitor...")
            self.running = False
            self.stop_threads()
            
            # Show final database summary
            print("\n📊 Final Database Summary:")
            print("-" * 40)
            session_logs = db_logger.get_session_logs(self.session_id)
            if session_logs:
                print(f"Total logs recorded: {len(session_logs)}")
                audio_logs = [log for log in session_logs if log['thread_id'] == 1]
                asr_logs = [log for log in session_logs if log['thread_id'] == 2]
                output_logs = [log for log in session_logs if log['thread_id'] == 3]
                
                print(f"Audio capture logs: {len(audio_logs)}")
                print(f"ASR/Translation logs: {len(asr_logs)}")
                print(f"Audio output logs: {len(output_logs)}")
                
                # Show any errors
                error_logs = [log for log in session_logs if log['errors']]
                if error_logs:
                    print(f"Errors encountered: {len(error_logs)}")
                    for log in error_logs[-3:]:  # Show last 3 errors
                        print(f"   {log['timestamp']}: {log['errors']}")
                
            print(f"\nSession ID: {self.session_id}")
            print("Database file: translation_logs.duckdb")
            print("Use the database viewer to analyze detailed logs.")
            
            self.clear_screen()
            print("✅ Live monitor stopped")

if __name__ == "__main__":
    monitor = LiveMonitorWithDB()
    monitor.run()
