"""Meeting detection via macOS mic-in-use (the Granola-style trigger).

Polls CoreAudio's ``kAudioDevicePropertyDeviceIsRunningSomewhere`` on the default
input device — it's True whenever *any* process is capturing the mic (Zoom,
Teams, browser Google Meet, ...). A debounced ``MicMonitor`` turns that into
``on_call_started`` / ``on_call_ended`` callbacks.

macOS-only and dependency-free (pure ctypes into the CoreAudio framework). On
other platforms ``is_available()`` is False and the monitor simply does nothing.
"""

import ctypes
import ctypes.util
import logging
import platform
import threading
import time

logger = logging.getLogger(__name__)

_IS_MACOS = platform.system() == "Darwin"


class _Addr(ctypes.Structure):
    _fields_ = [
        ("sel", ctypes.c_uint32),
        ("scope", ctypes.c_uint32),
        ("elem", ctypes.c_uint32),
    ]


def _fourcc(code: str) -> int:
    return int.from_bytes(code.encode("ascii"), "big")


_SYSTEM_OBJECT = 1
_DEFAULT_INPUT = _fourcc("dIn ")
_SCOPE_GLOBAL = _fourcc("glob")
_RUNNING_SOMEWHERE = _fourcc("gone")
_ELEMENT_MAIN = 0

_ca = None


def _coreaudio():
    """Lazily load CoreAudio and bind AudioObjectGetPropertyData. None if N/A."""
    global _ca
    if _ca is None and _IS_MACOS:
        try:
            lib = ctypes.CDLL(ctypes.util.find_library("CoreAudio"))
            lib.AudioObjectGetPropertyData.restype = ctypes.c_int32
            lib.AudioObjectGetPropertyData.argtypes = [
                ctypes.c_uint32,
                ctypes.POINTER(_Addr),
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
                ctypes.c_void_p,
            ]
            _ca = lib
        except Exception as e:  # pragma: no cover - non-macOS / load failure
            logger.warning("CoreAudio unavailable: %s", e)
    return _ca


def _get_uint32(object_id: int, selector: int):
    ca = _coreaudio()
    if ca is None:
        return None
    addr = _Addr(selector, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    out = ctypes.c_uint32(0)
    size = ctypes.c_uint32(4)
    status = ca.AudioObjectGetPropertyData(
        object_id, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(out)
    )
    return out.value if status == 0 else None


def is_available() -> bool:
    """Whether mic-in-use detection is supported here (macOS + CoreAudio)."""
    return _coreaudio() is not None


def is_mic_in_use() -> bool:
    """True if any process is currently capturing the default input device."""
    device = _get_uint32(_SYSTEM_OBJECT, _DEFAULT_INPUT)
    if not device:
        return False
    return bool(_get_uint32(device, _RUNNING_SOMEWHERE))


class _Debounce:
    """Turns a stream of (in_use, timestamp) samples into start/end events.

    Pure state machine (no threads/sleeps) so it's deterministically testable.
    """

    def __init__(self, start_debounce_s: float, end_debounce_s: float):
        self.start_debounce_s = start_debounce_s
        self.end_debounce_s = end_debounce_s
        self.in_call = False
        self._used_since = None
        self._free_since = None

    def step(self, in_use: bool, now: float) -> str | None:
        """Feed one sample; return 'start', 'end', or None."""
        if in_use:
            self._free_since = None
            if self._used_since is None:
                self._used_since = now
            if not self.in_call and now - self._used_since >= self.start_debounce_s:
                self.in_call = True
                return "start"
        else:
            self._used_since = None
            if self._free_since is None:
                self._free_since = now
            if self.in_call and now - self._free_since >= self.end_debounce_s:
                self.in_call = False
                return "end"
        return None


class MicMonitor(threading.Thread):
    """Watch mic-in-use and fire debounced call-started / call-ended callbacks."""

    def __init__(
        self,
        on_call_started=None,
        on_call_ended=None,
        poll_interval_s: float = 1.0,
        start_debounce_s: float = 3.0,
        end_debounce_s: float = 3.0,
    ):
        super().__init__(daemon=True)
        self.on_call_started = on_call_started
        self.on_call_ended = on_call_ended
        self.poll_interval_s = poll_interval_s
        self._debounce = _Debounce(start_debounce_s, end_debounce_s)
        self.stop_event = threading.Event()

    @property
    def in_call(self) -> bool:
        return self._debounce.in_call

    def run(self):
        if not is_available():
            logger.warning("MicMonitor: CoreAudio unavailable; detection disabled")
            return
        while not self.stop_event.is_set():
            event = self._debounce.step(is_mic_in_use(), time.monotonic())
            if event == "start":
                self._fire(self.on_call_started)
            elif event == "end":
                self._fire(self.on_call_ended)
            self.stop_event.wait(self.poll_interval_s)

    @staticmethod
    def _fire(callback):
        if callback:
            try:
                callback()
            except Exception as e:
                logger.error("MicMonitor callback error: %s", e)

    def stop(self):
        self.stop_event.set()


def _demo():  # pragma: no cover - manual tool
    """Run live: prints when a call (mic capture) starts/ends. Ctrl+C to quit."""
    print("Watching the mic… open Zoom/Teams/Meet to see detection. Ctrl+C to stop.")
    print(f"detection available: {is_available()}")
    monitor = MicMonitor(
        on_call_started=lambda: print("📞  call detected (mic in use)"),
        on_call_ended=lambda: print("🔇  call ended (mic free)"),
        start_debounce_s=2.0,
        end_debounce_s=2.0,
    )
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        print("\nstopped.")


if __name__ == "__main__":
    _demo()
