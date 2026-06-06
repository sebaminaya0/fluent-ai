"""Automated audio routing for Meeting Mode (BlackHole-based, macOS).

The product goal is: *you speak, the other party hears only the translation, and
your original voice stays private.* To make that work in **any** call app — even
ones with no microphone picker (WhatsApp, FaceTime) — we route audio like this
while a meeting is active:

    real mic ──► fluent ai (capture) ──► Whisper+translate ──► `say` ──► BlackHole
                                                                            │
    system default INPUT = BlackHole ◄──────────────────────────────────────┘
                                                                            │
                                              call app reads default input ─┘ ──► remote party

So we set the **system-default input to BlackHole** (the call app then sends our
translation), while fluent ai captures the user's **real hardware mic
explicitly** and plays TTS into BlackHole. The system-default *output* is left
untouched, so the user still hears the other person. On exit we restore the
original default input.

This module is macOS-only. ``is_macos()`` is False elsewhere and every routine
degrades to a safe no-op. It speaks to CoreAudio / CoreFoundation directly via
``ctypes`` (no extra dependency), mirroring the binding style in
``fluentai/meeting_detector.py``.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import os
import platform
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_IS_MACOS = platform.system() == "Darwin"

# Installer sources (used only if BlackHole isn't already present).
# NOTE: the /blackhole/download/?code=… page is an HTML email-gate, NOT a pkg.
# The real signed pkg lives under /downloads/ with the version in the name.
BLACKHOLE_GITHUB_LATEST = (
    "https://api.github.com/repos/ExistentialAudio/BlackHole/releases/latest"
)
BLACKHOLE_PKG_URL_TEMPLATE = (
    "https://existential.audio/downloads/BlackHole2ch-{version}.pkg"
)
BLACKHOLE_FALLBACK_VERSION = "0.6.1"  # used if the latest-version lookup fails
BLACKHOLE_DEVICE_NAME = "BlackHole"
# Homebrew caches the (correctly signed) pkg here even when the driver install
# itself never completed — reuse it instead of re-downloading.
_CASKROOM_GLOBS = (
    "/opt/homebrew/Caskroom/blackhole-2ch/*/BlackHole*ch-*.pkg",
    "/usr/local/Caskroom/blackhole-2ch/*/BlackHole*ch-*.pkg",
)
_XAR_MAGIC = b"xar!"  # macOS .pkg files are xar archives


def is_macos() -> bool:
    return _IS_MACOS


# ── CoreAudio / CoreFoundation ctypes bindings ───────────────────────────────


class _Addr(ctypes.Structure):
    _fields_ = [
        ("sel", ctypes.c_uint32),
        ("scope", ctypes.c_uint32),
        ("elem", ctypes.c_uint32),
    ]


def _fourcc(code: str) -> int:
    return int.from_bytes(code.encode("ascii"), "big")


_SYSTEM_OBJECT = 1  # kAudioObjectSystemObject
_PROP_DEVICES = _fourcc("dev#")  # kAudioHardwarePropertyDevices
_DEFAULT_INPUT = _fourcc("dIn ")  # kAudioHardwarePropertyDefaultInputDevice
_DEFAULT_OUTPUT = _fourcc("dOut")  # kAudioHardwarePropertyDefaultOutputDevice
_PROP_NAME = _fourcc("lnam")  # kAudioObjectPropertyName (CFStringRef)
_SCOPE_GLOBAL = _fourcc("glob")
_ELEMENT_MAIN = 0
_CFSTRING_UTF8 = 0x08000100  # kCFStringEncodingUTF8

_ca = None
_cf = None


def _frameworks():
    """Lazily load CoreAudio + CoreFoundation. Returns (ca, cf) or (None, None)."""
    global _ca, _cf
    if _ca is None and _IS_MACOS:
        try:
            ca = ctypes.CDLL(ctypes.util.find_library("CoreAudio"))
            cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))

            ca.AudioObjectGetPropertyData.restype = ctypes.c_int32
            ca.AudioObjectGetPropertyData.argtypes = [
                ctypes.c_uint32,
                ctypes.POINTER(_Addr),
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
                ctypes.c_void_p,
            ]
            ca.AudioObjectGetPropertyDataSize.restype = ctypes.c_int32
            ca.AudioObjectGetPropertyDataSize.argtypes = [
                ctypes.c_uint32,
                ctypes.POINTER(_Addr),
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
            ]
            ca.AudioObjectSetPropertyData.restype = ctypes.c_int32
            ca.AudioObjectSetPropertyData.argtypes = [
                ctypes.c_uint32,
                ctypes.POINTER(_Addr),
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_void_p,
            ]

            cf.CFStringGetCString.restype = ctypes.c_bool
            cf.CFStringGetCString.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_long,
                ctypes.c_uint32,
            ]
            cf.CFRelease.restype = None
            cf.CFRelease.argtypes = [ctypes.c_void_p]

            _ca, _cf = ca, cf
        except Exception as e:  # pragma: no cover - load failure / non-macOS
            logger.warning("CoreAudio/CoreFoundation unavailable: %s", e)
    return _ca, _cf


def _cfstring_to_str(cfstr: ctypes.c_void_p) -> str:
    _, cf = _frameworks()
    if not cf or not cfstr:
        return ""
    buf = ctypes.create_string_buffer(512)
    if cf.CFStringGetCString(cfstr, buf, len(buf), _CFSTRING_UTF8):
        return buf.value.decode("utf-8", "replace")
    return ""


def _get_uint32(object_id: int, selector: int) -> int | None:
    ca, _ = _frameworks()
    if ca is None:
        return None
    addr = _Addr(selector, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    out = ctypes.c_uint32(0)
    size = ctypes.c_uint32(4)
    status = ca.AudioObjectGetPropertyData(
        object_id, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(out)
    )
    return out.value if status == 0 else None


def _device_name(device_id: int) -> str:
    ca, cf = _frameworks()
    if ca is None or cf is None:
        return ""
    addr = _Addr(_PROP_NAME, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    cfstr = ctypes.c_void_p(0)
    size = ctypes.c_uint32(ctypes.sizeof(ctypes.c_void_p))
    status = ca.AudioObjectGetPropertyData(
        device_id, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(cfstr)
    )
    if status != 0 or not cfstr:
        return ""
    try:
        return _cfstring_to_str(cfstr)
    finally:
        cf.CFRelease(cfstr)


def _all_device_ids() -> list[int]:
    ca, _ = _frameworks()
    if ca is None:
        return []
    addr = _Addr(_PROP_DEVICES, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    size = ctypes.c_uint32(0)
    if (
        ca.AudioObjectGetPropertyDataSize(
            _SYSTEM_OBJECT, ctypes.byref(addr), 0, None, ctypes.byref(size)
        )
        != 0
    ):
        return []
    count = size.value // ctypes.sizeof(ctypes.c_uint32)
    if count <= 0:
        return []
    arr = (ctypes.c_uint32 * count)()
    if (
        ca.AudioObjectGetPropertyData(
            _SYSTEM_OBJECT, ctypes.byref(addr), 0, None, ctypes.byref(size), arr
        )
        != 0
    ):
        return []
    return list(arr)


def find_device_id_by_name(substring: str) -> int | None:
    """Return the CoreAudio AudioDeviceID whose name contains *substring*."""
    needle = substring.lower()
    for dev_id in _all_device_ids():
        if needle in _device_name(dev_id).lower():
            return dev_id
    return None


def get_default_input_id() -> int | None:
    return _get_uint32(_SYSTEM_OBJECT, _DEFAULT_INPUT)


def get_default_output_id() -> int | None:
    return _get_uint32(_SYSTEM_OBJECT, _DEFAULT_OUTPUT)


def _set_default_device(device_id: int, *, selector: int) -> bool:
    ca, _ = _frameworks()
    if ca is None:
        return False
    addr = _Addr(selector, _SCOPE_GLOBAL, _ELEMENT_MAIN)
    val = ctypes.c_uint32(device_id)
    status = ca.AudioObjectSetPropertyData(
        _SYSTEM_OBJECT, ctypes.byref(addr), 0, None, 4, ctypes.byref(val)
    )
    if status != 0:
        logger.error("Failed to set default device (status=%s)", status)
    return status == 0


def set_default_input_id(device_id: int) -> bool:
    return _set_default_device(device_id, selector=_DEFAULT_INPUT)


def set_default_output_id(device_id: int) -> bool:
    return _set_default_device(device_id, selector=_DEFAULT_OUTPUT)


# ── BlackHole install ────────────────────────────────────────────────────────


def is_blackhole_installed() -> bool:
    """True if a BlackHole audio device is present on the system."""
    if not _IS_MACOS:
        return False
    return find_device_id_by_name(BLACKHOLE_DEVICE_NAME) is not None


def _looks_like_pkg(path: str) -> bool:
    """True if *path* is a real macOS installer (xar archive), not an HTML page."""
    try:
        if os.path.getsize(path) < 10_000:
            return False
        with open(path, "rb") as fh:
            return fh.read(4) == _XAR_MAGIC
    except OSError:
        return False


def _latest_blackhole_version() -> str:
    """Latest BlackHole version (e.g. '0.6.1'), from GitHub; fallback if offline."""
    try:
        import json
        import urllib.request

        with urllib.request.urlopen(BLACKHOLE_GITHUB_LATEST, timeout=15) as resp:
            tag = json.load(resp).get("tag_name", "")
        version = tag.lstrip("vV").strip()
        if version:
            return version
    except Exception as e:
        logger.warning("BlackHole version lookup failed (%s); using fallback", e)
    return BLACKHOLE_FALLBACK_VERSION


def _resolve_installer_pkg(say) -> str | None:
    """Return a path to a valid BlackHole .pkg, reusing a cached one if present.

    Homebrew (and a prior interrupted install) leave the correctly-signed pkg in
    the Caskroom even when the driver itself was never installed — that's the
    common "it says it's downloaded but doesn't work" case, so we reuse it.
    """
    import glob

    for pattern in _CASKROOM_GLOBS:
        for cached in sorted(glob.glob(pattern), reverse=True):
            if _looks_like_pkg(cached):
                say("Using the BlackHole installer already on disk…")
                return cached

    version = _latest_blackhole_version()
    url = BLACKHOLE_PKG_URL_TEMPLATE.format(version=version)
    pkg_path = "/tmp/fluentai_blackhole.pkg"
    say(f"Downloading BlackHole {version}…")
    try:
        subprocess.run(["curl", "-fsSL", "-o", pkg_path, url], check=True, timeout=180)
    except Exception as e:
        logger.error("BlackHole download failed: %s", e)
        return None
    if not _looks_like_pkg(pkg_path):
        logger.error("Downloaded BlackHole file is not a valid .pkg (got HTML?)")
        return None
    return pkg_path


def ensure_blackhole_installed(progress_cb=None) -> bool:
    """Install BlackHole if missing. Returns True if present afterwards.

    Runs the official signed ``.pkg`` with a single macOS admin authorization
    (one native password dialog — no Terminal, no Privacy & Security approval,
    since BlackHole is a user-space CoreAudio HAL plugin, not a kernel/system
    extension). After this one-time install it persists across reboots. Success
    is judged by whether the device actually appears, not by exit codes.
    """
    if not _IS_MACOS:
        return False
    if is_blackhole_installed():
        return True

    def _say(msg: str):
        logger.info(msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    pkg_path = _resolve_installer_pkg(_say)
    if not pkg_path:
        _say("Couldn't obtain the BlackHole installer.")
        return False

    _say("Installing BlackHole (one macOS password prompt)…")
    # One admin authorization via the native dialog; restart coreaudiod so the
    # new device is visible immediately.
    script = (
        f"do shell script \"installer -pkg '{pkg_path}' -target / && "
        f'killall coreaudiod" with administrator privileges'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=True, timeout=300)
    except Exception as e:
        logger.error("BlackHole install failed: %s", e)
        return False
    finally:
        # Only clean up our own temp download, never the Caskroom copy.
        if pkg_path.startswith("/tmp/"):
            try:
                os.remove(pkg_path)
            except OSError:
                pass

    # coreaudiod takes a moment to re-register the new device after the install
    # (the pkg may even say "restart recommended"), so poll instead of checking
    # once. Then refresh PortAudio so the new device is visible to capture.
    ok = _wait_for_blackhole(timeout_s=8.0)
    if ok:
        reinitialize_portaudio()
    _say("BlackHole installed." if ok else "BlackHole install did not complete.")
    return ok


def _wait_for_blackhole(timeout_s: float = 8.0) -> bool:
    """Poll until the BlackHole device appears (or timeout)."""
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if is_blackhole_installed():
            return True
        time.sleep(0.5)
    return is_blackhole_installed()


def reinitialize_portaudio() -> None:
    """Refresh sounddevice/PortAudio's device list after the topology changes.

    PortAudio snapshots the device list at init, so a device added this session
    (e.g. BlackHole we just installed) is invisible and indices go stale —
    causing ``Invalid Property Value`` / PaErrorCode -9986 when opening a stream.
    Terminating and re-initializing rebuilds the list. Safe only when no stream
    is open (we call it before starting capture).
    """
    try:
        import sounddevice as sd

        sd._terminate()
        sd._initialize()
        logger.info("PortAudio reinitialized (device list refreshed)")
    except Exception as e:  # pragma: no cover - backend specific
        logger.warning("PortAudio reinitialize failed: %s", e)


# ── Meeting routing (enter / exit) ───────────────────────────────────────────


@dataclass
class RoutingState:
    """What ``enter_meeting_routing`` set up, so ``exit`` can restore it.

    ``real_mic_index`` is the *sounddevice* index of the user's real microphone
    (a different ID space from CoreAudio device ids) — pass it to
    ``AudioCaptureThread(device=...)`` so capture stays on the real mic after the
    system default is switched to BlackHole.
    """

    real_mic_index: int | None
    real_mic_name: str
    saved_default_input_id: int | None
    blackhole_id: int | None
    active: bool


def _default_input_sounddevice_index() -> tuple[int | None, str]:
    """The sounddevice index + name of the current default INPUT device."""
    try:
        import sounddevice as sd

        info = sd.query_devices(kind="input")
        name = info.get("name", "") if isinstance(info, dict) else ""
        for i, dev in enumerate(sd.query_devices()):
            if dev.get("name") == name and dev.get("max_input_channels", 0) > 0:
                return i, name
        return None, name
    except Exception as e:  # pragma: no cover - no audio backend
        logger.warning("Could not resolve default input device: %s", e)
        return None, ""


def sounddevice_input_index(name_substring: str) -> int | None:
    """sounddevice index of the first INPUT device whose name matches.

    Resolve by name (not a cached index) so it survives device renumbering after
    the list changes (e.g. BlackHole being added).
    """
    try:
        import sounddevice as sd

        needle = name_substring.lower()
        for i, dev in enumerate(sd.query_devices()):
            if needle in dev.get("name", "").lower() and (
                dev.get("max_input_channels", 0) > 0
            ):
                return i
    except Exception as e:  # pragma: no cover - no audio backend
        logger.warning("Could not resolve input device '%s': %s", name_substring, e)
    return None


def enter_meeting_routing() -> RoutingState:
    """Switch the system default input to BlackHole; keep capturing the real mic.

    Captures the real mic's sounddevice index *before* switching. Leaves the
    default output untouched (so the user still hears the other person). If
    BlackHole is missing or we're off macOS, returns an inactive state and
    changes nothing.
    """
    if not _IS_MACOS:
        return RoutingState(None, "", None, None, active=False)

    # Refresh PortAudio first so indices are consistent with the *current* device
    # list (BlackHole may have just been installed this session).
    reinitialize_portaudio()

    # Resolve the real mic BEFORE we change the default.
    real_mic_index, real_mic_name = _default_input_sounddevice_index()
    saved_input = get_default_input_id()
    blackhole_id = find_device_id_by_name(BLACKHOLE_DEVICE_NAME)

    if blackhole_id is None:
        logger.warning("BlackHole not found; routing not applied")
        return RoutingState(
            real_mic_index, real_mic_name, saved_input, None, active=False
        )

    ok = set_default_input_id(blackhole_id)
    if not ok:
        return RoutingState(
            real_mic_index, real_mic_name, saved_input, blackhole_id, active=False
        )

    logger.info(
        "Routing active: default input -> BlackHole; capturing real mic '%s' (idx %s)",
        real_mic_name,
        real_mic_index,
    )
    return RoutingState(
        real_mic_index, real_mic_name, saved_input, blackhole_id, active=True
    )


def exit_meeting_routing(state: RoutingState | None) -> None:
    """Restore the system default input captured by ``enter_meeting_routing``."""
    if not state or not state.active or not _IS_MACOS:
        return
    if state.saved_default_input_id is not None:
        if set_default_input_id(state.saved_default_input_id):
            logger.info("Routing restored: default input -> '%s'", state.real_mic_name)
    state.active = False
