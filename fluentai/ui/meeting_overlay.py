"""Floating always-on-top overlay shown during Meeting Mode.

Extracted from ``gui_app.py`` as a self-contained widget so it can be reused
and tested independently of the main ``FluentAIGUI`` window.
"""

import tkinter as tk


class MeetingOverlay:
    """Small always-on-top floating window shown during active Meeting Mode."""

    def __init__(self, root: tk.Tk, direction_text: str):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.92)
        self.win.geometry("320x90+80+80")
        self.win.configure(bg="#1a1a2e")

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        # ── Header row: drag handle + direction label ──
        header = tk.Frame(self.win, bg="#1a1a2e")
        header.pack(fill=tk.X, padx=8, pady=(6, 2))

        drag_handle = tk.Label(
            header,
            text="≡",
            font=("Arial", 12),
            bg="#1a1a2e",
            fg="#555577",
            cursor="fleur",
        )
        drag_handle.pack(side=tk.LEFT)
        drag_handle.bind("<ButtonPress-1>", self._on_drag_start)
        drag_handle.bind("<B1-Motion>", self._on_drag_motion)

        self._dot_label = tk.Label(
            header, text="●", font=("Arial", 10), bg="#1a1a2e", fg="#27ae60"
        )
        self._dot_label.pack(side=tk.LEFT, padx=(6, 4))

        tk.Label(
            header,
            text=direction_text,
            font=("Arial", 10, "bold"),
            bg="#1a1a2e",
            fg="#ecf0f1",
        ).pack(side=tk.LEFT)

        # ── Translation text ──
        self._text_label = tk.Label(
            self.win,
            text="Waiting for speech...",
            font=("Arial", 10),
            bg="#1a1a2e",
            fg="#27ae60",
            wraplength=300,
            justify=tk.LEFT,
            anchor=tk.W,
        )
        self._text_label.pack(fill=tk.X, padx=12, pady=(0, 6))

        # Start pulsing dot animation
        self._dot_visible = True
        self._animate_dot()

    def _animate_dot(self):
        if not self.win.winfo_exists():
            return
        self._dot_visible = not self._dot_visible
        color = "#27ae60" if self._dot_visible else "#1a1a2e"
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
            display = text[:50] + "…" if len(text) > 50 else text
            self._text_label.config(text=display)

    def close(self):
        if self.win.winfo_exists():
            self.win.destroy()
