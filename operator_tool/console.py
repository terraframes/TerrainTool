"""
console.py — Console pane widget for the TerrainTool Operator app.

Provides a Console class that renders a scrollable, coloured log output area.
Other modules call console.log("message", level="info") to append lines.

All UI updates run on the main thread via the widget's after() method,
so it's safe to call console.log() from background threads.
"""

import tkinter as tk
import customtkinter as ctk


# Colour used for each log level — applied as the text foreground colour
LEVEL_COLOURS = {
    "info":  "#d1d5db",  # light grey / near-white
    "ok":    "#4ade80",  # green
    "warn":  "#fb923c",  # orange
    "error": "#f87171",  # red
}

# Prefix tag prepended to each log line
LEVEL_PREFIX = {
    "info":  "[INFO] ",
    "ok":    "[OK]   ",
    "warn":  "[WARN] ",
    "error": "[ERROR]",
}


class Console:
    """
    A fixed-height console pane that appends coloured log lines.

    Usage:
        console = Console()
        console.build(parent_frame)
        console.log("Ready.", level="info")

    Thread-safe: log() may be called from any thread.
    """

    def __init__(self):
        # The underlying tk.Text widget — set in build()
        self._text: tk.Text | None = None

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def build(self, parent: ctk.CTkFrame) -> None:
        """
        Construct the console pane inside parent.
        Creates a separator, a header bar (label + Clear button), and the
        scrollable text area. Call once from app.py.
        """
        # Thin separator above the console so it's visually distinct from the tabs
        ctk.CTkFrame(parent, height=2, fg_color="gray25").pack(fill="x")

        # Header bar: "Console" label on the left, Clear button on the right
        header = ctk.CTkFrame(parent, fg_color="gray13", corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="Console",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray60",
        ).pack(side="left", padx=10, pady=4)

        ctk.CTkButton(
            header,
            text="Clear",
            width=60,
            height=24,
            font=ctk.CTkFont(size=11),
            command=self._clear,
        ).pack(side="right", padx=8, pady=4)

        # The text widget lives inside a plain tk Frame so we can give it
        # an exact height in pixels (CTk widgets use rows/columns, not pixels).
        text_container = tk.Frame(parent, bg="#0d0d0d", height=250)
        text_container.pack(fill="x")
        text_container.pack_propagate(False)  # lock the height

        # Scrollbar on the right edge
        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side="right", fill="y")

        # The actual text area — read-only, dark background, monospace font
        self._text = tk.Text(
            text_container,
            bg="#0d0d0d",
            fg="#d1d5db",
            insertbackground="#d1d5db",
            font=("Consolas", 11),
            wrap="word",
            state="disabled",        # read-only; we enable briefly to insert
            relief="flat",
            borderwidth=0,
            yscrollcommand=scrollbar.set,
        )
        self._text.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        scrollbar.config(command=self._text.yview)

        # Register a named colour tag for each log level
        for level, colour in LEVEL_COLOURS.items():
            self._text.tag_config(level, foreground=colour)

    def log(self, message: str, level: str = "info") -> None:
        """
        Append a line to the console.

        level must be one of: "info", "ok", "warn", "error".
        Falls back to "info" for unrecognised levels.
        Safe to call from background threads.
        """
        if level not in LEVEL_COLOURS:
            level = "info"

        prefix = LEVEL_PREFIX[level]
        line = f"{prefix} {message}\n"

        # Schedule the UI update on the main thread.
        # after(0, fn) queues fn for the next idle cycle — safe from any thread.
        if self._text is not None:
            self._text.after(0, self._append, line, level)

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    def _append(self, line: str, level: str) -> None:
        """Insert one line into the text widget and scroll to the bottom."""
        self._text.configure(state="normal")
        self._text.insert("end", line, level)
        self._text.configure(state="disabled")
        self._text.see("end")  # auto-scroll to the latest line

    def _clear(self) -> None:
        """Remove all text from the console."""
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
