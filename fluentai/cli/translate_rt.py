#!/usr/bin/env python3
"""
Real-time Translation CLI (translate_rt.py)

This CLI application provides real-time voice translation with the following features:
• Loads language configurations from YAML
• Initializes and starts 3 processing threads
• Displays stats overlay: fps capture, queue sizes, end-to-end latency

Usage:
    uv python -m fluentai.cli.translate_rt \
        --src es --dst en \
        --voice female --vad 2
"""

import argparse
import logging
import queue
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from fluentai.asr_translation_synthesis_thread import ASRTranslationSynthesisThread
from fluentai.blackhole_reproduction_thread import BlackHoleReproductionThread

# FluentAI imports
from fluentai.model_loader import LazyModelLoader

# Check if audio_capture_thread is available
try:
    import sys
    import os
    # Add the parent directory to the path so we can import the audio_capture_thread module
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from audio_capture_thread import AudioCaptureThread
except ImportError:
    print("Warning: audio_capture_thread not found. Audio capture will be disabled.")
    AudioCaptureThread = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class StatsData:
    """Statistics data for the overlay display."""
    # Capture stats
    capture_fps: float = 0.0
    capture_queue_size: int = 0

    # Processing stats
    processing_queue_size: int = 0
    processing_fps: float = 0.0

    # Output stats
    output_queue_size: int = 0
    output_fps: float = 0.0

    # End-to-end latency
    end_to_end_latency_ms: float = 0.0

    # Timestamps for FPS calculation
    capture_timestamps: list = field(default_factory=list)
    processing_timestamps: list = field(default_factory=list)
    output_timestamps: list = field(default_factory=list)

    def update_capture_fps(self):
        """Update capture FPS based on recent timestamps."""
        now = time.time()
        self.capture_timestamps.append(now)
        # Keep only last 5 seconds of timestamps
        cutoff = now - 5.0
        self.capture_timestamps = [t for t in self.capture_timestamps if t > cutoff]

        if len(self.capture_timestamps) > 1:
            duration = self.capture_timestamps[-1] - self.capture_timestamps[0]
            self.capture_fps = (len(self.capture_timestamps) - 1) / duration if duration > 0 else 0.0

    def update_processing_fps(self):
        """Update processing FPS based on recent timestamps."""
        now = time.time()
        self.processing_timestamps.append(now)
        # Keep only last 5 seconds of timestamps
        cutoff = now - 5.0
        self.processing_timestamps = [t for t in self.processing_timestamps if t > cutoff]

        if len(self.processing_timestamps) > 1:
            duration = self.processing_timestamps[-1] - self.processing_timestamps[0]
            self.processing_fps = (len(self.processing_timestamps) - 1) / duration if duration > 0 else 0.0

    def update_output_fps(self):
        """Update output FPS based on recent timestamps."""
        now = time.time()
        self.output_timestamps.append(now)
        # Keep only last 5 seconds of timestamps
        cutoff = now - 5.0
        self.output_timestamps = [t for t in self.output_timestamps if t > cutoff]

        if len(self.output_timestamps) > 1:
            duration = self.output_timestamps[-1] - self.output_timestamps[0]
            self.output_fps = (len(self.output_timestamps) - 1) / duration if duration > 0 else 0.0


class StatsOverlay:
    """Thread-safe stats overlay display."""

    def __init__(self, update_interval: float = 1.0):
        self.stats = StatsData()
        self.update_interval = update_interval
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.start_time = time.time()

    def start(self):
        """Start the stats overlay display thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._display_loop, daemon=True)
        self.thread.start()
        logger.info("Stats overlay started")

    def stop(self):
        """Stop the stats overlay display thread."""
        if not self.running:
            return

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        logger.info("Stats overlay stopped")

    def update_stats(self, **kwargs):
        """Update stats data thread-safely."""
        with self.lock:
            for key, value in kwargs.items():
                if hasattr(self.stats, key):
                    setattr(self.stats, key, value)

    def record_capture_event(self):
        """Record a capture event for FPS calculation."""
        with self.lock:
            self.stats.update_capture_fps()

    def record_processing_event(self):
        """Record a processing event for FPS calculation."""
        with self.lock:
            self.stats.update_processing_fps()

    def record_output_event(self):
        """Record an output event for FPS calculation."""
        with self.lock:
            self.stats.update_output_fps()

    def _display_loop(self):
        """Main display loop running in a separate thread."""
        while self.running:
            try:
                with self.lock:
                    stats_copy = StatsData(
                        capture_fps=self.stats.capture_fps,
                        capture_queue_size=self.stats.capture_queue_size,
                        processing_queue_size=self.stats.processing_queue_size,
                        processing_fps=self.stats.processing_fps,
                        output_queue_size=self.stats.output_queue_size,
                        output_fps=self.stats.output_fps,
                        end_to_end_latency_ms=self.stats.end_to_end_latency_ms
                    )

                # Clear screen and display stats
                print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
                print("=" * 80)
                print("FluentAI Real-time Translation - Stats Overlay")
                print("=" * 80)

                # Runtime
                runtime = time.time() - self.start_time
                hours, remainder = divmod(runtime, 3600)
                minutes, seconds = divmod(remainder, 60)
                print(f"Runtime: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
                print()

                # Thread stats
                print("Thread Performance:")
                print("  Audio Capture:")
                print(f"    FPS: {stats_copy.capture_fps:.2f}")
                print(f"    Queue Size: {stats_copy.capture_queue_size}")
                print()

                print("  ASR + Translation:")
                print(f"    FPS: {stats_copy.processing_fps:.2f}")
                print(f"    Queue Size: {stats_copy.processing_queue_size}")
                print()

                print("  Audio Output:")
                print(f"    FPS: {stats_copy.output_fps:.2f}")
                print(f"    Queue Size: {stats_copy.output_queue_size}")
                print()

                # End-to-end latency
                print(f"End-to-End Latency: {stats_copy.end_to_end_latency_ms:.1f}ms")
                print()

                # System info
                print("System:")
                print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print()

                print("Press Ctrl+C to stop")
                print("=" * 80)

            except Exception as e:
                logger.error(f"Error in stats display loop: {e}")

            time.sleep(self.update_interval)


class RealTimeTranslator:
    """Main real-time translation coordinator."""

    def __init__(self, src_lang: str, dst_lang: str, voice: str, vad_aggressiveness: int):
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.voice = voice
        self.vad_aggressiveness = vad_aggressiveness

        # Load language configuration
        self.language_config = self._load_language_config()

        # Initialize model loader
        self.model_loader = LazyModelLoader()

        # Initialize queues
        self.asr_queue = queue.Queue(maxsize=10)
        self.output_queue = queue.Queue(maxsize=10)

        # Initialize stats overlay
        self.stats_overlay = StatsOverlay()

        # Initialize threads
        self.capture_thread = None
        self.processing_thread = None
        self.output_thread = None

        # Control flags
        self.running = False
        self.stop_event = threading.Event()

        logger.info(f"RealTimeTranslator initialized: {src_lang} -> {dst_lang}")

    def _load_language_config(self) -> dict[str, Any]:
        """Load language configuration from YAML file."""
        config_path = Path("conf/languages.yaml")

        if not config_path.exists():
            logger.error(f"Language configuration file not found: {config_path}")
            raise FileNotFoundError(f"Language configuration file not found: {config_path}")

        try:
            with open(config_path, encoding='utf-8') as f:
                config = yaml.safe_load(f)

            logger.info(f"Loaded language configuration from {config_path}")
            logger.info(f"Available languages: {list(config.keys())}")

            # Validate that source and destination languages exist
            if self.src_lang not in config:
                raise ValueError(f"Source language '{self.src_lang}' not found in configuration")
            if self.dst_lang not in config:
                raise ValueError(f"Destination language '{self.dst_lang}' not found in configuration")

            return config

        except Exception as e:
            logger.error(f"Error loading language configuration: {e}")
            raise

    def _init_capture_thread(self):
        """Initialize the audio capture thread."""
        if AudioCaptureThread is None:
            logger.error("AudioCaptureThread not available")
            return None

        try:
            # Create audio capture thread with VAD settings
            capture_thread = AudioCaptureThread(
                asr_queue=self.asr_queue,
                sample_rate=16000,
                vad_aggressiveness=self.vad_aggressiveness,
                voice_threshold_ms=200,
                silence_threshold_ms=400
            )

            logger.info("Audio capture thread initialized")
            return capture_thread

        except Exception as e:
            logger.error(f"Error initializing capture thread: {e}")
            return None

    def _init_processing_thread(self):
        """Initialize the ASR + translation + synthesis thread."""
        try:
            # Get language mappings from config
            src_whisper_lang = self.language_config[self.src_lang]['whisper']
            dst_tts_lang = self.language_config[self.dst_lang]['tts']

            # Create processing thread
            processing_thread = ASRTranslationSynthesisThread(
                queue_in=self.asr_queue,
                queue_out=self.output_queue,
                src_lang=self.src_lang,
                dst_lang=self.dst_lang,
                whisper_model='base'
            )

            logger.info("ASR + Translation + Synthesis thread initialized")
            return processing_thread

        except Exception as e:
            logger.error(f"Error initializing processing thread: {e}")
            if "SparseMPS" in str(e) or "MPS" in str(e):
                logger.warning("MPS backend error detected. This may be due to PyTorch version incompatibility.")
                logger.warning("Consider using CPU backend or updating PyTorch for MPS support.")
            return None

    def _init_output_thread(self):
        """Initialize the BlackHole reproduction thread."""
        try:
            # Create output thread with BlackHole device ID 1 (from device list)
            output_thread = BlackHoleReproductionThread(
                output_device=1,  # BlackHole 2ch device ID
                input_queue=self.output_queue,  # Connect to output queue
                sample_rate=44100
            )

            logger.info("BlackHole reproduction thread initialized")
            return output_thread

        except Exception as e:
            logger.error(f"Error initializing output thread: {e}")
            return None

    def _monitor_queues(self):
        """Monitor queue sizes and update stats."""
        while self.running:
            try:
                # Update queue sizes
                self.stats_overlay.update_stats(
                    capture_queue_size=self.asr_queue.qsize(),
                    processing_queue_size=self.output_queue.qsize(),
                    output_queue_size=0  # BlackHole thread doesn't have a traditional queue
                )

                # Monitor capture thread stats
                if self.capture_thread:
                    capture_stats = self.capture_thread.get_stats()
                    # Record capture events based on voice frames detected
                    if capture_stats.get('voice_frames', 0) > 0:
                        self.stats_overlay.record_capture_event()

                # Monitor processing thread activity
                if self.processing_thread:
                    try:
                        # Check if there's output audio (non-blocking)
                        if not self.output_queue.empty():
                            self.stats_overlay.record_processing_event()
                            self.stats_overlay.record_output_event()
                    except queue.Empty:
                        pass
                    
                    # Check for ASR queue activity
                    if not self.asr_queue.empty():
                        self.stats_overlay.record_processing_event()

                time.sleep(0.1)  # Update every 100ms

            except Exception as e:
                logger.error(f"Error in queue monitoring: {e}")

            if self.stop_event.is_set():
                break

    def start(self):
        """Start all threads and begin real-time translation."""
        if self.running:
            logger.warning("Real-time translator already running")
            return

        logger.info("Starting real-time translator...")

        # Pre-load models
        logger.info("Pre-loading translation models...")
        self.model_loader.preload_models_threaded([self.src_lang, self.dst_lang])

        # Initialize threads
        logger.info("Initializing threads...")

        self.capture_thread = self._init_capture_thread()
        self.processing_thread = self._init_processing_thread()
        self.output_thread = self._init_output_thread()

        # Check if all threads were initialized successfully
        if not all([self.capture_thread, self.processing_thread, self.output_thread]):
            logger.error("Failed to initialize all threads")
            return False

        # Start threads
        logger.info("Starting threads...")

        try:
            # Start capture thread
            if self.capture_thread:
                self.capture_thread.start()

            # Start processing thread
            if self.processing_thread:
                self.processing_thread.start()

            # Start output thread
            if self.output_thread:
                self.output_thread.start()

            # Start stats overlay
            self.stats_overlay.start()

            # Start queue monitoring
            self.running = True
            self.stop_event.clear()

            monitor_thread = threading.Thread(target=self._monitor_queues, daemon=True)
            monitor_thread.start()

            logger.info("All threads started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting threads: {e}")
            self.stop()
            return False

    def stop(self):
        """Stop all threads and cleanup."""
        if not self.running:
            return

        logger.info("Stopping real-time translator...")

        # Set stop flag
        self.running = False
        self.stop_event.set()

        # Stop threads
        if self.capture_thread:
            self.capture_thread.stop()

        if self.processing_thread:
            self.processing_thread.stop()

        if self.output_thread:
            self.output_thread.stop()

        # Stop stats overlay
        self.stats_overlay.stop()

        # Cleanup model loader
        self.model_loader.shutdown()

        logger.info("Real-time translator stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, stopping...")
    if hasattr(signal_handler, 'translator'):
        signal_handler.translator.stop()
    sys.exit(0)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FluentAI Real-time Translation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Spanish to English with female voice
    uv python -m fluentai.cli.translate_rt --src es --dst en --voice female --vad 2
    
    # English to Spanish with male voice
    uv python -m fluentai.cli.translate_rt --src en --dst es --voice male --vad 1
    
    # German to French with default settings
    uv python -m fluentai.cli.translate_rt --src de --dst fr
        """
    )

    parser.add_argument(
        '--src',
        required=True,
        help='Source language code (e.g., es, en, de, fr)'
    )

    parser.add_argument(
        '--dst',
        required=True,
        help='Destination language code (e.g., es, en, de, fr)'
    )

    parser.add_argument(
        '--voice',
        default='female',
        choices=['female', 'male'],
        help='Voice type for synthesis (default: female)'
    )

    parser.add_argument(
        '--vad',
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help='Voice Activity Detection aggressiveness (0-3, default: 2)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if args.src == args.dst:
        logger.error("Source and destination languages cannot be the same")
        sys.exit(1)

    try:
        # Create translator
        translator = RealTimeTranslator(
            src_lang=args.src,
            dst_lang=args.dst,
            voice=args.voice,
            vad_aggressiveness=args.vad
        )

        # Set up signal handlers
        signal_handler.translator = translator
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start translation
        logger.info(f"Starting real-time translation: {args.src} -> {args.dst}")
        logger.info(f"Voice: {args.voice}, VAD: {args.vad}")

        if translator.start():
            logger.info("Real-time translation started successfully")
            logger.info("Speak into the microphone to begin translation")

            # Keep the main thread alive
            try:
                while translator.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            logger.error("Failed to start real-time translation")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

    finally:
        if 'translator' in locals():
            translator.stop()


if __name__ == "__main__":
    main()
