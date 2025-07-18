#!/usr/bin/env python3
"""
VAD Probe - Voice Activity Detection using WebRTC VAD

Captures audio in 30ms chunks at 16kHz/16-bit mono and displays
a real-time voice activity bar in the terminal using ░▒▓ characters.

Usage:
    python examples/vad_probe.py --aggressiveness 2
"""

import argparse
import sys
import threading
import time

import numpy as np
import sounddevice as sd
import webrtcvad

# Audio configuration for WebRTC VAD
RATE = 16000  # 16 kHz sample rate
DURATION_MS = 30  # 30ms chunks
CHUNK_DURATION = DURATION_MS / 1000
CHUNK_SIZE = int(RATE * CHUNK_DURATION)  # 480 samples for 30ms at 16kHz


class VADProbe:
    def __init__(self, aggressiveness=2):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.aggressiveness = aggressiveness
        self.reset_term_colors()

        # Detection tracking
        self.detection_history = []
        self.first_detection_time = None
        self.start_time = time.time()

        # Stats
        self.total_frames = 0
        self.speech_frames = 0

        # Threading for stats display
        self.stats_lock = threading.Lock()

    def reset_term_colors(self):
        sys.stdout.write('\033[0m')

    def get_audio_level(self, audio_data):
        """Calculate audio level for visualization enhancement"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
        # Normalize to 0-1 range (approximate)
        return min(rms / 3000.0, 1.0) if rms > 0 else 0.0

    def process(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}", file=sys.stderr)

        # Convert to bytes for WebRTC VAD
        pcm_data = indata.tobytes()

        # Detect speech
        is_speech = self.vad.is_speech(pcm_data, sample_rate=RATE)

        # Get audio level for enhanced visualization
        audio_level = self.get_audio_level(pcm_data)

        with self.stats_lock:
            self.total_frames += 1
            current_time = time.time()

            if is_speech:
                self.speech_frames += 1
                if self.first_detection_time is None:
                    self.first_detection_time = current_time
                    detection_latency = (current_time - self.start_time) * 1000
                    print(f"\n[FIRST DETECTION] Latency: {detection_latency:.1f}ms", file=sys.stderr)

                # Enhanced visualization based on audio level
                if audio_level > 0.7:
                    sys.stdout.write('▓')  # High activity
                elif audio_level > 0.3:
                    sys.stdout.write('▒')  # Medium activity
                else:
                    sys.stdout.write('▓')  # Low speech activity
            else:
                sys.stdout.write('░')  # No speech

            sys.stdout.flush()

            # Track detection history for validation
            self.detection_history.append({
                'timestamp': current_time,
                'is_speech': is_speech,
                'audio_level': audio_level
            })

            # Keep only last 100 frames in history
            if len(self.detection_history) > 100:
                self.detection_history.pop(0)

    def get_stats(self):
        """Get current detection statistics"""
        with self.stats_lock:
            if self.total_frames == 0:
                return "No frames processed yet"

            speech_percentage = (self.speech_frames / self.total_frames) * 100
            runtime = time.time() - self.start_time

            stats = f"\nFrames: {self.total_frames}, Speech: {self.speech_frames} ({speech_percentage:.1f}%), Runtime: {runtime:.1f}s"

            if self.first_detection_time:
                detection_latency = (self.first_detection_time - self.start_time) * 1000
                stats += f", First detection: {detection_latency:.1f}ms"

            return stats

    def validate_detection_speed(self):
        """Validate that detection occurs within 200ms"""
        if self.first_detection_time is None:
            return False, "No speech detected during session"

        detection_latency = (self.first_detection_time - self.start_time) * 1000

        if detection_latency <= 200:
            return True, f"✓ Detection latency: {detection_latency:.1f}ms (within 200ms requirement)"
        else:
            return False, f"✗ Detection latency: {detection_latency:.1f}ms (exceeds 200ms requirement)"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VAD Probe - Voice Activity Detection using WebRTC VAD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python examples/vad_probe.py --aggressiveness 0  # Less aggressive
  python examples/vad_probe.py --aggressiveness 3  # More aggressive
  
Voice Activity Bar:
  ░ = No speech detected
  ▒ = Medium speech activity  
  ▓ = High speech activity
  
Validation: First speech detection should occur within 200ms"""
    )
    parser.add_argument('--aggressiveness', type=int, choices=range(4), default=2,
                       help='VAD aggressiveness level (0-3). Higher values are more aggressive in detecting speech.')
    args = parser.parse_args()

    print("VAD Probe - Voice Activity Detection")
    print(f"Configuration: 16kHz, 16-bit mono, 30ms chunks, aggressiveness={args.aggressiveness}")
    print("Voice Activity Bar: ░=no speech, ▒=medium, ▓=high")
    print("Validation: First detection should occur within 200ms")
    print("\nPress Ctrl+C to stop and see validation results\n")

    vad_probe = VADProbe(args.aggressiveness)

    try:
        with sd.InputStream(channels=1, samplerate=RATE, blocksize=CHUNK_SIZE, dtype='int16', callback=vad_probe.process):
            while True:
                sd.sleep(1000)  # Keep the stream active
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
    finally:
        vad_probe.reset_term_colors()

        # Show final stats
        print(vad_probe.get_stats())

        # Validate detection speed
        passed, message = vad_probe.validate_detection_speed()
        print(f"\nValidation: {message}")

        if passed:
            print("\n✓ VAD Probe validation PASSED - Detection within 200ms requirement")
        else:
            print("\n✗ VAD Probe validation FAILED - Detection exceeds 200ms requirement")

        print("\nStopped.")

