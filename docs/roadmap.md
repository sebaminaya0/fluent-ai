# Fluent AI — Product Roadmap (next phase)

## North star
Turn Fluent AI into a **background macOS menu-bar agent** that **auto-detects
calls** and shows a **refined, branded floating translator overlay** — start
translating a meeting with one click (or automatically), like Granola prompts to
record.

## Decisions (agreed)
- **Detection:** mic-in-use is the primary trigger (CoreAudio).
- **App shape:** macOS menu-bar agent (`rumps`) + the floating overlay as the
  main in-meeting surface.
- **Branding:** name is **`fluent ai`** (all lowercase). Minimalist, Granola-like
  layout; palette = electric blue (primary), electric green (sparing accent for
  live/active states), white base. Dark mode: swap white → black later.

## Brand palette (starting point — refine in design)
| Role | Light | Dark | Notes |
|---|---|---|---|
| Primary (electric blue) | `#0A84FF` | `#0A84FF` | buttons, active state, logo |
| Accent (electric green) | `#00E676` | `#00E676` | small highlights only: "LIVE" dot, success |
| Base / surface | `#FFFFFF` | `#0B0B0F` | background |
| Text | `#0B0B0F` | `#F5F7FA` | high contrast |
| Muted text / borders | `#8A94A6` | `#5B6472` | secondary text, tentative captions |

Wordmark: "fluent ai" lowercase, tight tracking; electric-blue dot/glyph as the
app + menu-bar icon. Keep whitespace generous (Granola-minimal).

## Workstreams

### 1. Meeting auto-detection (mic-in-use)
- New `fluentai/meeting_detector.py`: poll CoreAudio
  `kAudioDevicePropertyDeviceIsRunningSomewhere` on the default input device
  (via `pyobjc-framework-CoreAudio` or ctypes). Fires the instant any app grabs
  the mic — Zoom, Teams, **and browser Google Meet**.
- Debounce (require a few seconds "in use") to ignore brief mic access /
  notification sounds.
- On detection → prompt "Call detected — start live translation?" → one-click
  start of the existing Meeting Mode pipeline.
- Optional enrichment: NSWorkspace running-apps (name the meeting app),
  EventKit calendar (proactive "meeting in 2 min" prompt; needs permission).

### 2. Menu-bar agent (`rumps`)
- New entry point `fluentai/menubar_app.py`: status item + menu (Start/Stop,
  direction, output device, Settings, Quit). Runs the detector in the
  background; native notifications.
- Decouple the pipeline (already in `fluentai/`: capture → streaming ASR →
  speak) from the Tkinter window so it can run headless under the menu bar.
- Dep: `rumps`.

### 3. Overlay redesign + branding (`fluent ai`)
- Redesign `fluentai/ui/meeting_overlay.py` as the primary surface: cleaner
  layout, the palette above, live caption + translation areas, a green "LIVE"
  dot, generous whitespace.
- Assets: app icon + menu-bar icon (electric-blue glyph), `fluent ai` wordmark.
- Settings UI: small CustomTkinter or `pywebview` popover (later).
- Dark mode: white → black swap using the palette's Dark column.

## Suggested sequencing
1. Mic-in-use detector (standalone, testable) — proves the trigger.
2. `rumps` menu-bar shell that uses it (prompt → start current Meeting Mode).
3. Decouple pipeline from Tkinter so it runs under the menu bar.
4. Overlay redesign + branding (once the name/identity is set).

## Open items
- Permissions: device-in-use state needs no special permission; calendar
  (EventKit) does, if used.
- Packaging: eventual `.app` bundle (e.g. py2app) for a real menu-bar agent.
- Dark mode timing (palette ready; wire when the overlay is redesigned).

## Done already (foundation this builds on)
- Streaming Meeting Mode: live captions (LocalAgreement-2) + per-sentence audio.
- Low-latency streaming TTS (`say --audio-device`), half/full-duplex handling.
- Whisper `small` + 700ms segmentation for quality; feedback-loop fix.
