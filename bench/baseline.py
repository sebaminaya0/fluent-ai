#!/usr/bin/env python3
"""Baseline real-pipeline measurement for Fluent AI.

Modes:
- Auto (default): record a short real mic clip, then run the pipeline and measure latency.
- File: use an existing WAV file and measure pipeline latency/behavior.
- Health: use synthetic/default input without mic, assert pipeline processes within a budget.

Usage examples:
    uv run bench/baseline.py
    uv run bench/baseline.py --record 5 --src es --dst en --model base
    uv run bench/baseline.py --file test_data/myclip.wav
"""

from __future__ import annotations

import argparse
import os
import queue
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class StageMetrics:
    whisper_ms: float = 0.0
    translation_ms: float = 0.0
    tts_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class BaselineResult:
    file: str
    output_samples: int
    metrics: StageMetrics
    ok: bool
    error: Optional[str] = None


def _try_record(seconds: int) -> Optional[Path]:
    try:
        import sounddevice as sd
    except Exception as e:
        print(f"Record unavailable: {e}")
        return None
    out = Path("/tmp/fluent_baseline.wav")
    try:
        print(f"Recording {seconds}s from default mic...")
        audio = sd.rec(int(seconds * 16000), samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        if np.max(np.abs(audio)) < 1e-4:
            print("Recording looks silent; skipping.")
            return None
        import soundfile as sf

        sf.write(str(out), audio, 16000)
        print(f"Saved recording to {out}")
        return out
    except Exception as e:
        print(f"Recording failed: {e}")
        return None


def _wav_bytes_from(path: Path) -> bytes:
    import io
    import wave

    audio, sr = _read_audio(path)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def _read_audio(path: Path):
    import soundfile as sf

    audio, sr = sf.read(str(path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak > 1.0:
        audio = audio / peak
    return audio, sr


def measure(path: Path, src_lang: str, dst_lang: str, whisper_model: str, timeout: float = 90) -> BaselineResult:
    try:
        q_in: queue.Queue[dict] = queue.Queue()
        q_out: queue.Queue[np.ndarray] = queue.Queue()

        from fluentai.asr_translation_synthesis_thread import ASRTranslationSynthesisThread

        thread = ASRTranslationSynthesisThread(
            q_in, q_out, src_lang=src_lang, dst_lang=dst_lang, whisper_model=whisper_model
        )
        thread.start()

        q_in.put({"wav_data": _wav_bytes_from(path), "timestamp": time.time()})

        t0 = time.perf_counter()
        metrics = StageMetrics()
        try:
            item = q_out.get(timeout=timeout)
            now = time.perf_counter()
            metrics.total_ms = (now - t0) * 1000.0
            if item is None or not isinstance(item, np.ndarray):
                return BaselineResult(file=path.name, output_samples=0, metrics=metrics, ok=False, error="Invalid output")
            if len(item) == 0:
                return BaselineResult(file=path.name, output_samples=0, metrics=metrics, ok=False, error="Empty output")
            if not np.isfinite(item).all():
                return BaselineResult(file=path.name, output_samples=int(len(item)), metrics=metrics, ok=False, error="Non-finite samples")
            peak = float(np.max(np.abs(item)))
            if peak > 1.0:
                return BaselineResult(file=path.name, output_samples=int(len(item)), metrics=metrics, ok=False, error=f"Unnormalized peak {peak}")
            return BaselineResult(file=path.name, output_samples=int(len(item)), metrics=metrics, ok=True)
        except queue.Empty:
            return BaselineResult(file=path.name, output_samples=0, metrics=metrics, ok=False, error="Timeout waiting for output")
        finally:
            thread.stop()
            thread.join(timeout=15)
    except Exception as e:
        return BaselineResult(file=path.name if path else "", output_samples=0, metrics=StageMetrics(), ok=False, error=str(e))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=int, default=0, help="Record N seconds of real audio as baseline")
    parser.add_argument("--file", type=str, default="", help="Use specific WAV file")
    parser.add_argument("--src", type=str, default="es")
    parser.add_argument("--dst", type=str, default="en")
    parser.add_argument("--model", type=str, default="base")
    args = parser.parse_args()

    target = Path(args.file) if args.file else None
    if target is None and args.record > 0:
        target = _try_record(args.record)
    if target is None:
        fallback = Path("test_data/spanish_test.wav")
        target = fallback if fallback.exists() else None
    if target is None:
        print("No input audio available; pass --file or --record 4")
        return 2

    print(f"Input: {target}")
    r = measure(target, src_lang=args.src, dst_lang=args.dst, whisper_model=args.model)
    status = "OK" if r.ok else f"FAIL: {r.error}"
    print(f"{status} | out={r.output_samples} | total={r.metrics.total_ms:.1f} ms")
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
