#!/usr/bin/env python3
"""
Demonstration of Silence Detection Features

This script shows how to use the new silence detection capabilities
in the Fluent AI system. It demonstrates both CLI and programmatic usage.
"""

import argparse
import time

from silence_detector import SILENCE_DETECTION_PRESETS, create_silence_detector


def demo_cli_usage():
    """Demonstrate CLI usage of silence detection."""
    print("=== CLI Usage Examples ===")
    print("\nBasic usage with silence detection:")
    print("python main_whisper.py --silence-detection")

    print("\nWith custom parameters:")
    print("python main_whisper.py --silence-detection --min-silence-len 1000 --silence-thresh -35")

    print("\nWith different presets:")
    for preset in SILENCE_DETECTION_PRESETS.keys():
        print(f"python main_whisper.py --silence-detection --silence-preset {preset}")

    print("\nWith specific detection method:")
    print("python main_whisper.py --silence-detection --silence-method webrtcvad")
    print("python main_whisper.py --silence-detection --silence-method pydub")

    print("\nAll parameters combined:")
    print("python main_whisper.py --silence-detection --silence-preset aggressive --min-silence-len 1200 --silence-thresh -45 --vad-aggressiveness 3")

def demo_programmatic_usage():
    """Demonstrate programmatic usage of silence detection."""
    print("\n=== Programmatic Usage Examples ===")

    # Create detector with different presets
    print("\n1. Creating detectors with different presets:")
    for preset_name, config in SILENCE_DETECTION_PRESETS.items():
        try:
            detector = create_silence_detector(preset=preset_name)
            print(f"✓ {preset_name}: min_silence_len={config['min_silence_len']}ms, "
                  f"silence_thresh={config['silence_thresh']}dBFS, "
                  f"method={detector.active_method}")
        except Exception as e:
            print(f"✗ {preset_name}: Error - {e}")

    # Show configuration options
    print("\n2. Available configuration options:")
    print("- min_silence_len: 200-2000ms (default: 800ms)")
    print("- silence_thresh: -60 to -20 dBFS (default: -40dBFS)")
    print("- method: 'auto', 'webrtcvad', 'pydub' (default: 'auto')")
    print("- aggressiveness: 0-3 for WebRTC VAD (default: 2)")

    # Show callback system
    print("\n3. Callback system example:")
    print("""
def on_silence_detected(timestamp):
    print(f"Silence detected at {timestamp}")

def on_speech_detected(timestamp):
    print(f"Speech detected at {timestamp}")

def on_silence_threshold_exceeded(duration_ms):
    print(f"Auto-stop triggered after {duration_ms:.0f}ms of silence")

detector = create_silence_detector()
detector.set_callbacks(
    on_silence_detected=on_silence_detected,
    on_speech_detected=on_speech_detected,
    on_silence_threshold_exceeded=on_silence_threshold_exceeded
)
""")

def demo_real_time_detection():
    """Demonstrate real-time silence detection."""
    print("\n=== Real-time Detection Demo ===")

    # Check if dependencies are available
    try:
        detector = create_silence_detector(preset='balanced')
        print(f"✓ Using detection method: {detector.active_method}")
    except Exception as e:
        print(f"✗ Cannot initialize detector: {e}")
        print("Install dependencies: pip install webrtcvad pydub")
        return

    # Set up callbacks for demonstration
    events = []

    def on_silence_detected(timestamp):
        events.append(f"[{time.strftime('%H:%M:%S')}] 🔇 Silence detected")
        print(events[-1])

    def on_speech_detected(timestamp):
        events.append(f"[{time.strftime('%H:%M:%S')}] 🎤 Speech detected")
        print(events[-1])

    def on_silence_threshold_exceeded(duration_ms):
        events.append(f"[{time.strftime('%H:%M:%S')}] ⏹️ Auto-stop: {duration_ms:.0f}ms silence")
        print(events[-1])

    detector.set_callbacks(
        on_silence_detected=on_silence_detected,
        on_speech_detected=on_speech_detected,
        on_silence_threshold_exceeded=on_silence_threshold_exceeded
    )

    print("\nDemo configuration:")
    stats = detector.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\nNote: This demo shows the silence detection setup.")
    print("For full real-time detection, integrate with speech_recognition microphone stream.")
    print("See main_whisper.py for complete implementation.")

def demo_gui_features():
    """Demonstrate GUI features."""
    print("\n=== GUI Features ===")

    print("The GUI application (gui_app.py) includes:")
    print("✓ Checkbox to enable/disable silence detection")
    print("✓ Preset selector (sensitive, balanced, aggressive, very_aggressive)")
    print("✓ Slider for minimum silence length (200-2000ms)")
    print("✓ Slider for silence threshold (-60 to -20 dBFS)")
    print("✓ Real-time status updates showing silence/speech detection")
    print("✓ Auto-stop notifications when silence threshold is exceeded")

    print("\nTo run the GUI:")
    print("python gui_app.py")

    print("\nGUI Controls:")
    print("- Check '🔇 Detección de silencio automática' to enable")
    print("- Use preset dropdown for quick configuration")
    print("- Adjust sliders for fine-tuning")
    print("- Status bar shows real-time detection events")

def demo_integration_examples():
    """Show integration examples."""
    print("\n=== Integration Examples ===")

    print("1. Basic integration with speech recognition:")
    print("""
import speech_recognition as sr
from silence_detector import create_silence_detector, SilenceDetectorIntegration

# Create components
recognizer = sr.Recognizer()
detector = create_silence_detector(preset='balanced')
integration = SilenceDetectorIntegration(recognizer, detector)

# Set up auto-stop callback
def on_auto_stop(duration_ms):
    print(f"Auto-stopping after {duration_ms:.0f}ms of silence")
    # Implement your auto-stop logic here
    
integration.set_transcription_callback(on_auto_stop)

# Use with microphone
with sr.Microphone() as source:
    audio = integration.listen_with_silence_detection(source, timeout=30)
    if audio:
        # Process audio with Whisper or other transcription
        pass
""")

    print("\n2. Custom silence detection parameters:")
    print("""
# For noisy environments
noisy_detector = create_silence_detector(
    min_silence_len=1200,  # Longer silence required
    silence_thresh=-50,    # Lower threshold for noisy environments
    method='webrtcvad',    # More robust for speech detection
    aggressiveness=3       # Most aggressive VAD setting
)

# For quiet environments
quiet_detector = create_silence_detector(
    min_silence_len=600,   # Shorter silence acceptable
    silence_thresh=-30,    # Higher threshold for quiet environments
    method='pydub',        # Good for general audio analysis
    aggressiveness=1       # Less aggressive VAD setting
)
""")

def main():
    parser = argparse.ArgumentParser(
        description="Demonstrate silence detection features",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--cli', action='store_true',
                       help='Show CLI usage examples')
    parser.add_argument('--programmatic', action='store_true',
                       help='Show programmatic usage examples')
    parser.add_argument('--realtime', action='store_true',
                       help='Demonstrate real-time detection')
    parser.add_argument('--gui', action='store_true',
                       help='Show GUI features')
    parser.add_argument('--integration', action='store_true',
                       help='Show integration examples')
    parser.add_argument('--all', action='store_true',
                       help='Show all demonstrations')

    args = parser.parse_args()

    if not any(vars(args).values()):
        args.all = True

    print("🔇 Fluent AI - Silence Detection Demonstration")
    print("=" * 50)

    if args.cli or args.all:
        demo_cli_usage()

    if args.programmatic or args.all:
        demo_programmatic_usage()

    if args.realtime or args.all:
        demo_real_time_detection()

    if args.gui or args.all:
        demo_gui_features()

    if args.integration or args.all:
        demo_integration_examples()

    print("\n=== Summary ===")
    print("The silence detection system provides:")
    print("• Real-time audio energy monitoring")
    print("• Configurable silence parameters (duration, threshold)")
    print("• Multiple detection methods (webrtcvad, pydub)")
    print("• Auto-stop transcription on sustained silence")
    print("• Timer reset when speech resumes")
    print("• GUI controls for easy configuration")
    print("• CLI flags for power users")
    print("• Integration with existing speech recognition")

    print("\nFor more information, see:")
    print("• silence_detector.py - Core implementation")
    print("• main_whisper.py - CLI integration")
    print("• gui_app.py - GUI integration")

if __name__ == "__main__":
    main()
