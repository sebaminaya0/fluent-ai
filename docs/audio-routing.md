# Automated audio routing (Meeting Mode)

This document explains how fluent ai sends your translation into a call so the
**other person hears only the translation while your original voice stays
private** — and how the app sets this up for you automatically.

## The goal

```
you speak ─► fluent ai captures your REAL mic ─► Whisper + translate ─► `say` ─► BlackHole
                                                                                    │
                              system default INPUT = BlackHole ◄────────────────────┘
                                                                                    │
                                          the call app reads the default input ─────┘ ─► remote party
```

- The **call app's microphone** is BlackHole, so it transmits our translated
  TTS — not your voice.
- fluent ai captures your **real hardware mic explicitly**, so it still hears you
  even though the system default input is now BlackHole.
- The system default **output is left untouched**, so you keep hearing the other
  person normally.
- You do **not** hear your own translation (by design); use the **Test setup**
  button to confirm it's flowing.

This works for apps with no microphone picker (WhatsApp, FaceTime) as well as
those that have one (Zoom, Meet, Teams) — see the per-app note below.

## What the app automates

Implemented in [`fluentai/audio_setup.py`](../fluentai/audio_setup.py), wired
into Meeting Mode in `gui_app.py`:

1. **Install BlackHole on first use.** If the BlackHole device isn't present,
   `ensure_blackhole_installed()` downloads the official **signed `.pkg`** and
   runs it with a single macOS admin authorization (one native password
   dialog), then restarts `coreaudiod`. No Terminal, no reboot.
2. **Route on start.** `enter_meeting_routing()` records your current default
   input, switches the **system default input to BlackHole**, and returns your
   real mic's index so capture stays on the real mic.
3. **Restore on stop / quit.** `exit_meeting_routing()` puts your original
   default input back. This also runs from `on_close()` as a safety net, so the
   app never leaves your mic hijacked.

### Why one password prompt is unavoidable

BlackHole is a **user-space CoreAudio HAL plugin**, not a kernel/system
extension — so it does *not* trigger the multi-step "Privacy & Security → Allow"
flow or a reboot. But macOS still requires admin authorization to add a
system-wide audio device. That single prompt is the only manual step, it happens
once, and it's true of any solution (BlackHole, Loopback, a custom driver).

## Verifying it works ("Test setup")

The **Test setup** button runs two checks without needing a real call:

- **Microphone** — records ~2 s from your real mic and confirms signal.
- **Translation routing** — plays a phrase to BlackHole while recording
  BlackHole's input (it loops back), confirming the call path works.

If both pass, start Meeting Mode and call.

## Per-app note

| App | What you need to do |
|---|---|
| WhatsApp, FaceTime | Nothing — they follow the system default input. |
| Zoom, Meet, Teams | If you previously **pinned** a specific mic in their settings, set it to **BlackHole 2ch** (or "Same as System"). Otherwise nothing. |

## Platform support

macOS only. `audio_setup.is_macos()` is `False` elsewhere and every routine is a
safe no-op, so the rest of the app still runs. The CoreAudio / CoreFoundation
calls use `ctypes` directly (no extra dependency), mirroring
[`fluentai/meeting_detector.py`](../fluentai/meeting_detector.py).

## Auto-detection

When **Auto-detect calls** is on, `MicMonitor` watches for any app grabbing the
mic and prompts "Call detected — start live translation?". Accepting runs the
same routing described above. See the roadmap for the menu-bar agent that will
make this fully background.
