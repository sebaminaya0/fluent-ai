# fluent ai — design system

The look of the app. The single source of truth in code is
[`fluentai/ui/theme.py`](../fluentai/ui/theme.py); use its constants and helpers
rather than hard-coding colors. Direction: **minimalist, Granola-like** — white
base, generous whitespace, one strong accent, color used with restraint.

## Palette

### Light (main window)

| Token | Hex | Use |
|---|---|---|
| `PRIMARY` | `#0A84FF` | Electric blue — primary buttons, active state, the wordmark |
| `PRIMARY_HOVER` | `#0060DF` | Pressed/hover blue |
| `ACCENT` | `#00E676` | Electric green — **sparingly**: LIVE dot, success only |
| `SURFACE` | `#FFFFFF` | Base background |
| `SURFACE_ALT` | `#F1F4F8` | Subtle panels, secondary buttons |
| `TEXT` | `#0B0B0F` | High-contrast text |
| `MUTED` | `#8A94A6` | Secondary text, borders, tentative captions |
| `DANGER` | `#E5484D` | Stop / destructive |
| `ON_PRIMARY` | `#FFFFFF` | Text on colored buttons |

### Dark (floating overlay — the in-meeting surface)

| Token | Hex | Use |
|---|---|---|
| `DARK_SURFACE` | `#0B0B0F` | Overlay background |
| `DARK_TEXT` | `#F5F7FA` | Overlay text |
| `DARK_MUTED` | `#5B6472` | Overlay secondary text |

## Typography

`FONT_FAMILY = "Helvetica Neue"`, via `theme.font(size, weight)`. The wordmark
**"fluent ai"** is always lowercase with tight tracking, in `PRIMARY`.

## Components

- **Primary button** (`style_primary_button`): filled `PRIMARY`, white text,
  flat, rounded padding. One per context (e.g. Load model, Record, Start Meeting
  Mode).
- **Secondary button** (`style_secondary_button`): quiet `SURFACE_ALT` fill,
  dark text (Play, Test setup).
- **Danger button** (`style_danger_button`): filled `DANGER` (Stop Meeting Mode).
- **LIVE dot**: pulsing `ACCENT` green — the only routine use of green.
- **Overlay**: dark surface, lowercase wordmark in blue, green LIVE dot,
  translation in large light text, direction label in muted text.

## Applying the theme

`gui_app.create_ui()` calls, after building widgets:

```python
theme.apply_theme(self.root)        # base surface + ttk styling
theme.recolor_surfaces(self.root)   # flip legacy #f0f0f0 frames -> white
theme.style_primary_button(self.record_btn)   # etc.
```

`recolor_surfaces()` repaints legacy grey frame/label backgrounds to the brand
white in one pass, so we get the clean surface without editing every widget.

## Decisions & rationale (delegated design choices)

- **Kept Tkinter** for now (no new dependency); the palette + helpers give a
  noticeably more refined, consistent look. CustomTkinter / a `pywebview`
  surface remain options for a deeper redesign later.
- **Blue is the single brand accent**; green is reserved for "live/active" so it
  stays meaningful. Stop is red.
- **White base, lots of whitespace, lowercase wordmark** for the Granola-minimal
  feel requested.
- The **overlay is the priority surface** (what you see mid-call), so it got the
  most deliberate styling.

## Backlog (design)

- Full main-window layout redesign (cards, spacing scale, iconography).
- Dark mode for the main window (swap `SURFACE`/`TEXT` to the dark column).
- App + menu-bar icon (electric-blue glyph) and packaged wordmark asset.
