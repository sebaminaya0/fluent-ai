"""fluent ai design system — brand palette, fonts, and Tk/ttk theming helpers.

A single source of truth for the look of the app so the GUI and the floating
overlay stay consistent. Minimalist / Granola-like: white base, generous
whitespace, electric blue for primary actions, electric green used sparingly for
"live"/success only. See ``docs/design.md`` for the rationale and usage rules.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ── Light palette (main window) ──────────────────────────────────────────────
PRIMARY = "#0A84FF"  # electric blue — primary buttons, active state, wordmark
PRIMARY_HOVER = "#0060DF"  # blue, pressed/hover
ACCENT = "#00E676"  # electric green — sparingly: LIVE dot, success
SURFACE = "#FFFFFF"  # base background
SURFACE_ALT = "#F1F4F8"  # subtle panels / secondary buttons
TEXT = "#0B0B0F"  # high-contrast text
MUTED = "#8A94A6"  # secondary text, borders, tentative captions
DANGER = "#E5484D"  # stop / destructive
ON_PRIMARY = "#FFFFFF"  # text on colored buttons

# ── Dark palette (floating overlay — the in-meeting surface) ─────────────────
DARK_SURFACE = "#0B0B0F"
DARK_TEXT = "#F5F7FA"
DARK_MUTED = "#5B6472"

FONT_FAMILY = "Helvetica Neue"  # clean macOS system-ish sans


def font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    """A palette font tuple, e.g. ``font(11, "bold")``."""
    return (FONT_FAMILY, size, weight)


def apply_theme(root: tk.Misc) -> ttk.Style:
    """Set the base surface + ttk widget styling. Returns the configured Style."""
    try:
        root.configure(bg=SURFACE)
    except tk.TclError:
        pass

    style = ttk.Style(root)
    try:
        style.theme_use("clam")  # most themeable across platforms
    except tk.TclError:
        pass

    style.configure(
        "Fluent.TCombobox",
        fieldbackground=SURFACE,
        background=SURFACE_ALT,
        foreground=TEXT,
        arrowcolor=TEXT,
        bordercolor=MUTED,
        relief="flat",
    )
    style.configure(
        "Fluent.TCheckbutton",
        background=SURFACE,
        foreground=MUTED,
        focuscolor=SURFACE,
    )
    return style


def style_primary_button(btn: tk.Button) -> None:
    """Electric-blue filled button for the main action."""
    btn.configure(
        bg=PRIMARY,
        fg=ON_PRIMARY,
        activebackground=PRIMARY_HOVER,
        activeforeground=ON_PRIMARY,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        font=font(11, "bold"),
        padx=16,
        pady=8,
        cursor="hand2",
    )


def style_secondary_button(btn: tk.Button) -> None:
    """Quiet neutral button for secondary actions."""
    btn.configure(
        bg=SURFACE_ALT,
        fg=TEXT,
        activebackground="#E2E7EF",
        activeforeground=TEXT,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        font=font(10),
        padx=10,
        pady=6,
        cursor="hand2",
    )


def style_danger_button(btn: tk.Button) -> None:
    """Filled red button for stop/destructive actions."""
    btn.configure(
        bg=DANGER,
        fg=ON_PRIMARY,
        activebackground="#C93C40",
        activeforeground=ON_PRIMARY,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        font=font(11, "bold"),
        padx=16,
        pady=8,
        cursor="hand2",
    )


def recolor_surfaces(
    widget: tk.Misc, old: tuple[str, ...] = ("#f0f0f0",), new: str = SURFACE
) -> None:
    """Recursively repaint legacy frame/label backgrounds onto the new surface.

    Lets us flip the old grey base to the brand white without editing every
    widget literal. Only touches background of layout/text widgets; buttons,
    comboboxes and text areas are left to their explicit styling.
    """
    classes = (tk.Frame, tk.LabelFrame, tk.Label, tk.Checkbutton, tk.Canvas)
    try:
        if isinstance(widget, classes) and str(widget.cget("bg")) in old:
            widget.configure(bg=new)
            if isinstance(widget, tk.Checkbutton):
                widget.configure(activebackground=new, selectcolor=SURFACE_ALT)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        recolor_surfaces(child, old, new)
