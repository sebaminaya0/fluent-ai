#!/usr/bin/env python3
"""
Demo script for recording FluentAI real-time translation capabilities.

This script demonstrates:
- Spanish ↔ English translation
- Portuguese ↔ German translation
- Real-time audio processing
- VAD (Voice Activity Detection) functionality

Usage:
    python scripts/demo_recording.py --demo-type es-en
    python scripts/demo_recording.py --demo-type pt-de
    python scripts/demo_recording.py --demo-type interactive
"""

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class DemoRecorder:
    def __init__(self):
        self.processes = []
        self.recording_active = False

    def start_translation_process(self, src_lang, dst_lang, input_device=None, output_device=None):
        """Start a translation process."""
        cmd = [
            sys.executable, "-m", "fluentai.cli.translate_rt",
            "--src-lang", src_lang,
            "--dst-lang", dst_lang,
            "--whisper-model", "base",  # Use base model for faster demo
            "--silence-preset", "balanced"
        ]

        if input_device:
            cmd.extend(["--input-device", str(input_device)])
        if output_device:
            cmd.extend(["--output-device", str(output_device)])

        print(f"Starting translation: {src_lang} → {dst_lang}")
        print(f"Command: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.processes.append(process)
            return process
        except Exception as e:
            print(f"Error starting translation process: {e}")
            return None

    def demo_spanish_english(self):
        """Demonstrate Spanish ↔ English translation."""
        print("\n" + "="*60)
        print("DEMO: Spanish ↔ English Real-time Translation")
        print("="*60)

        print("\n1. Starting Spanish → English translation...")
        process_es_en = self.start_translation_process("es", "en")

        if process_es_en:
            print("\n📢 Demo Instructions:")
            print("- Speak in Spanish into your microphone")
            print("- The system will detect speech using VAD")
            print("- Whisper will transcribe the Spanish audio")
            print("- The text will be translated to English")
            print("- gTTS will synthesize English speech")
            print("- You'll hear the English translation")
            print("\n⏸️  Press Ctrl+C to stop the demo")

            try:
                # Keep the demo running
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nStopping Spanish → English demo...")

        print("\n2. Starting English → Spanish translation...")
        process_en_es = self.start_translation_process("en", "es")

        if process_en_es:
            print("\n📢 Demo Instructions:")
            print("- Now speak in English into your microphone")
            print("- The system will translate to Spanish")
            print("- You'll hear the Spanish translation")
            print("\n⏸️  Press Ctrl+C to stop the demo")

            try:
                # Keep the demo running
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nStopping English → Spanish demo...")

    def demo_portuguese_german(self):
        """Demonstrate Portuguese ↔ German translation."""
        print("\n" + "="*60)
        print("DEMO: Portuguese ↔ German Real-time Translation")
        print("="*60)

        print("\n1. Starting Portuguese → German translation...")
        process_pt_de = self.start_translation_process("pt", "de")

        if process_pt_de:
            print("\n📢 Demo Instructions:")
            print("- Speak in Portuguese into your microphone")
            print("- The system will detect speech using VAD")
            print("- Whisper will transcribe the Portuguese audio")
            print("- The text will be translated to German")
            print("- gTTS will synthesize German speech")
            print("- You'll hear the German translation")
            print("\n⏸️  Press Ctrl+C to stop the demo")

            try:
                # Keep the demo running
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nStopping Portuguese → German demo...")

        print("\n2. Starting German → Portuguese translation...")
        process_de_pt = self.start_translation_process("de", "pt")

        if process_de_pt:
            print("\n📢 Demo Instructions:")
            print("- Now speak in German into your microphone")
            print("- The system will translate to Portuguese")
            print("- You'll hear the Portuguese translation")
            print("\n⏸️  Press Ctrl+C to stop the demo")

            try:
                # Keep the demo running
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nStopping German → Portuguese demo...")

    def demo_interactive(self):
        """Interactive demo with multiple language pairs."""
        print("\n" + "="*60)
        print("DEMO: Interactive Multi-language Translation")
        print("="*60)

        language_pairs = [
            ("es", "en", "Spanish → English"),
            ("en", "es", "English → Spanish"),
            ("pt", "de", "Portuguese → German"),
            ("de", "pt", "German → Portuguese"),
            ("en", "de", "English → German"),
            ("fr", "en", "French → English"),
        ]

        print("\nAvailable language pairs:")
        for i, (src, dst, desc) in enumerate(language_pairs, 1):
            print(f"{i}. {desc}")

        while True:
            try:
                choice = input("\nSelect a language pair (1-6) or 'q' to quit: ").strip()

                if choice.lower() == 'q':
                    break

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(language_pairs):
                        src, dst, desc = language_pairs[idx]
                        print(f"\nStarting {desc}...")

                        process = self.start_translation_process(src, dst)
                        if process:
                            print(f"\n📢 Speak in {src.upper()} - Press Ctrl+C to stop")
                            try:
                                while True:
                                    time.sleep(1)
                            except KeyboardInterrupt:
                                print(f"\nStopping {desc}...")

                    else:
                        print("Invalid choice. Please select 1-6.")

                except ValueError:
                    print("Invalid input. Please enter a number 1-6 or 'q'.")

            except KeyboardInterrupt:
                print("\nExiting interactive demo...")
                break

    def cleanup(self):
        """Clean up all running processes."""
        print("\nCleaning up processes...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except Exception as e:
                print(f"Error cleaning up process: {e}")

        self.processes.clear()

    def signal_handler(self, signum, frame):
        """Handle interrupt signals."""
        print(f"\nReceived signal {signum}")
        self.cleanup()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="FluentAI Demo Recording Script")
    parser.add_argument(
        "--demo-type",
        choices=["es-en", "pt-de", "interactive"],
        default="interactive",
        help="Type of demo to run"
    )
    parser.add_argument(
        "--check-dependencies",
        action="store_true",
        help="Check if all required dependencies are installed"
    )

    args = parser.parse_args()

    # Check dependencies
    if args.check_dependencies:
        print("Checking dependencies...")
        required_modules = [
            "fluentai.cli.translate_rt",
            "whisper",
            "transformers",
            "gtts",
            "sounddevice",
            "webrtcvad"
        ]

        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
                print(f"✓ {module}")
            except ImportError:
                print(f"✗ {module}")
                missing_modules.append(module)

        if missing_modules:
            print(f"\nMissing dependencies: {', '.join(missing_modules)}")
            print("Please install with: uv sync --extra rt")
            sys.exit(1)
        else:
            print("\nAll dependencies are installed! ✓")

    # Initialize demo recorder
    demo = DemoRecorder()

    # Set up signal handlers
    signal.signal(signal.SIGINT, demo.signal_handler)
    signal.signal(signal.SIGTERM, demo.signal_handler)

    try:
        print("\n🎬 FluentAI Real-time Translation Demo")
        print("=====================================")
        print(f"Demo type: {args.demo_type}")
        print("\nPreparation checklist:")
        print("□ BlackHole audio driver installed")
        print("□ Audio aggregate device configured")
        print("□ Microphone and speakers working")
        print("□ Recording software ready (OBS, QuickTime, etc.)")
        print("\nPress Enter to continue...")
        input()

        # Run the selected demo
        if args.demo_type == "es-en":
            demo.demo_spanish_english()
        elif args.demo_type == "pt-de":
            demo.demo_portuguese_german()
        elif args.demo_type == "interactive":
            demo.demo_interactive()

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo error: {e}")
    finally:
        demo.cleanup()
        print("\nDemo complete!")

if __name__ == "__main__":
    main()
