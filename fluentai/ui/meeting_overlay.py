"""Floating always-on-top overlay shown during Meeting Mode.

Extracted from ``gui_app.py`` as a self-contained widget so it can be reused
and tested independently of the main ``FluentAIGUI`` window. Styled with the
fluent ai design system (see ``fluentai/ui/theme.py``).
"""

import tkinter as tk

from fluentai.ui import theme

_BG = theme.DARK_SURFACE
_TEXT = theme.DARK_TEXT
_MUTED = theme.DARK_MUTED


class MeetingOverlay:
    """Small always-on-top floating window shown during active Meeting Mode."""

    def __init__(self, root: tk.Tk, direction_text: str):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.96)
        self.win.geometry("340x104+80+80")
        self.win.configure(bg=_BG)

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        # ── Header row: drag handle + LIVE dot + wordmark + direction ──
        header = tk.Frame(self.win, bg=_BG)
        header.pack(fill=tk.X, padx=14, pady=(10, 2))

        drag_handle = tk.Label(
            header,
            text="⠿",
            font=theme.font(12),
            bg=_BG,
            fg=_MUTED,
            cursor="fleur",
        )
        drag_handle.pack(side=tk.LEFT)
        drag_handle.bind("<ButtonPress-1>", self._on_drag_start)
        drag_handle.bind("<B1-Motion>", self._on_drag_motion)

        self._dot_label = tk.Label(
            header, text="●", font=theme.font(10), bg=_BG, fg=theme.ACCENT
        )
        self._dot_label.pack(side=tk.LEFT, padx=(8, 4))

        tk.Label(
            header,
            text="fluent ai",
            font=theme.font(11, "bold"),
            bg=_BG,
            fg=theme.PRIMARY,
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text=direction_text,
            font=theme.font(10),
            bg=_BG,
            fg=_MUTED,
        ).pack(side=tk.RIGHT)

        # ── Translation text ──
        self._text_label = tk.Label(
            self.win,
            text="Waiting for speech…",
            font=theme.font(13),
            bg=_BG,
            fg=_TEXT,
            wraplength=312,
            justify=tk.LEFT,
            anchor=tk.W,
        )
        self._text_label.pack(fill=tk.BOTH, expand=True, padx=14, pady=(2, 12))

        # Start pulsing dot animation
        self._dot_visible = True
        self._animate_dot()

    def _animate_dot(self):
        if not self.win.winfo_exists():
            return
        self._dot_visible = not self._dot_visible
        color = theme.ACCENT if self._dot_visible else _BG
        self._dot_label.config(fg=color)
        self.win.after(600, self._animate_dot)

    def _on_drag_start(self, event):
        self._drag_x = event.x_root - self.win.winfo_x()
        self._drag_y = event.y_root - self.win.winfo_y()

    def _on_drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.win.geometry(f"+{x}+{y}")

    def update_text(self, text: str):
        if self.win.winfo_exists():
            display = text[:80] + "…" if len(text) > 80 else text
            self._text_label.config(text=display)

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()
