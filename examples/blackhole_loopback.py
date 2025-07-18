import sounddevice as sd

RATE = 16000; CHUNK = 1024
in_dev  = sd.default.device[0]      # Mic
out_dev = [d['name'] for d in sd.query_devices()].index('BlackHole 2ch')
sd.default.samplerate = RATE

def callback(indata, frames, t, status):
    if status: print(status, flush=True)
    sd.play(indata.copy(), device=out_dev)

with sd.InputStream(channels=1, callback=callback, blocksize=CHUNK):
    print("Ctrl-C para salir"); sd.sleep(60_000)
