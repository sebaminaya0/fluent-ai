import concurrent.futures
import io
import queue
import threading
import time

import numpy as np
import sounddevice as sd
from gtts import gTTS

# Constants
SAMPLE_RATE = 16000
DURATION = 1  # seconds
OUTPUT_DEVICE = [d['name'] for d in sd.query_devices() if 'BlackHole' in d['name']][0]
VAD_SEGMENT_SIZE = 0.2  # 200ms

# Function to emit a beep
def emit_beep(freq=1000, duration=1):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    x = 0.5 * np.sin(2 * np.pi * freq * t)
    sd.play(x, samplerate=SAMPLE_RATE)
    sd.wait()

# Function to detect the beep
class BeepDetector:
    def __init__(self):
        self.queue = queue.Queue()
        self.stop_event = threading.Event()

    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.queue.put(indata.copy())

    def listen(self, duration):
        with sd.InputStream(channels=1, callback=self.callback, dtype='float32',
                            samplerate=SAMPLE_RATE, blocksize=int(SAMPLE_RATE * VAD_SEGMENT_SIZE)):
            self.stop_event.clear()
            sd.sleep(int(duration * 1000))

    def stop(self):
        self.stop_event.set()

# Function to compress TTS
def compress_tts(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    audio = np.frombuffer(buf.read(), dtype=np.int16)
    pcm_audio = audio.astype(np.float32) / np.iinfo(np.int16).max
    return pcm_audio

# Benchmark latency
if __name__ == "__main__":
    detector = BeepDetector()
    futures = []

    # Emit beep
    emit_beep()
    start_time = time.time()

    # Listen and measure
    detector.listen(DURATION)
    elapsed_time = time.time() - start_time
    print(f"Latency: {elapsed_time:.2f} seconds")

    # Whisper parallel processing (placeholder)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        text_segments = ["Hello"] * 3  # Simulated segments
        futures = [executor.submit(compress_tts, text) for text in text_segments]
        concurrent.futures.wait(futures)

    # Process results
    for future in futures:
        result = future.result()
        # Process TTS result (e.g., save or playback)

    print("Benchmarking complete.")

