"""
settings_tab.py — Builds the Settings tab and handles all its logic.

Each field maps to one key in config.json.
Path fields have a Browse button to open a file/folder picker.
API key fields are plain text entries with no Browse button.
The Save button at the bottom writes everything to config.json.
"""

import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import customtkinter as ctk

from config import load_config, save_config


# --- Field definitions --------------------------------------------------
# Each entry is a dict describing one row in the settings form.
#
# Keys:
#   label        — human-readable label shown to the left of the entry
#   config_key   — key used in config.json
#   browse       — "file" | "folder" | None
#                  "file"   → Browse opens a file picker
#                  "folder" → Browse opens a folder picker
#                  None     → no Browse button (API keys etc.)
#   placeholder  — hint text shown inside an empty entry box

FIELDS = [
    {
        "label": "Blender executable",
        "config_key": "blender_path",
        "browse": "file",
        "placeholder": r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    },
    {
        "label": "QGIS Python bat",
        "config_key": "qgis_bat_path",
        "browse": "file",
        "placeholder": r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat",
    },
    {
        "label": "Local orders folder",
        "config_key": "orders_folder",
        "browse": "folder",
        "placeholder": r"E:\TerrainTool\orders",
    },
    {
        "label": "Google Drive credentials JSON",
        "config_key": "gdrive_key_path",
        "browse": "file",
        "placeholder": r"E:\TerrainTool\credentials\gdrive_key.json",
    },
    {
        "label": "Google Shared Drive ID",
        "config_key": "gdrive_drive_id",
        "browse": None,
        "placeholder": "e.g. 0ABCxyz123...",
    },
    {
        "label": "OpenTopography API key",
        "config_key": "opentopo_api_key",
        "browse": None,
        "placeholder": "Your OpenTopography key",
    },
    {
        "label": "Mapbox token",
        "config_key": "mapbox_token",
        "browse": None,
        "placeholder": "pk.eyJ1...",
    },
]


class SettingsTab:
    """
    Builds and manages the Settings tab content inside a given parent frame.
    Call build(parent) once after creating the instance.
    """

    def __init__(self):
        # Will hold {config_key: ctk.StringVar} once built
        self._vars: dict[str, ctk.StringVar] = {}

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def build(self, parent: ctk.CTkFrame) -> None:
        """
        Populate the parent frame with all settings widgets.
        Loads existing config values so fields are pre-filled on launch.
        """
        existing = load_config()

        # Plain frame — content fits without scrolling
        scroll = ctk.CTkFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Section heading
        ctk.CTkLabel(
            scroll,
            text="Application Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))

        # Build one row per field definition
        for row_index, field in enumerate(FIELDS, start=1):
            self._add_field_row(scroll, row_index, field, existing)

        # Separator line (just vertical padding acts as visual break)
        ctk.CTkFrame(scroll, height=2, fg_color="gray40").grid(
            row=len(FIELDS) + 1, column=0, columnspan=3, sticky="ew", pady=(20, 12)
        )

        # Save button outside the scrollable area so it's always visible
        save_btn = ctk.CTkButton(
            parent,
            text="Save Settings",
            width=160,
            command=self._on_save,
        )
        save_btn.pack(pady=(6, 16))

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _add_field_row(
        self,
        parent: ctk.CTkFrame,
        row: int,
        field: dict,
        existing: dict,
    ) -> None:
        """
        Add a single label + entry (+ optional Browse button) row to the grid.
        Stores the StringVar in self._vars keyed by config_key.
        """
        key = field["config_key"]

        # StringVar pre-populated from existing config (or empty string)
        var = ctk.StringVar(value=existing.get(key, ""))
        self._vars[key] = var

        # Label — right-aligned so it sits flush against the entry
        ctk.CTkLabel(
            parent,
            text=field["label"] + ":",
            anchor="e",
            width=220,
        ).grid(row=row, column=0, sticky="e", padx=(0, 10), pady=6)

        # Text entry — expands horizontally to fill available space
        entry = ctk.CTkEntry(
            parent,
            textvariable=var,
            placeholder_text=field["placeholder"],
            width=420,
        )
        entry.grid(row=row, column=1, sticky="ew", pady=6)

        # Configure column 1 to stretch with the window
        parent.grid_columnconfigure(1, weight=1)

        # Browse button — only for path fields
        if field["browse"] is not None:
            browse_type = field["browse"]
            ctk.CTkButton(
                parent,
                text="Browse",
                width=80,
                # Use default-arg capture so each lambda closes over its own var/type
                command=lambda v=var, t=browse_type: self._browse(v, t),
            ).grid(row=row, column=2, padx=(8, 0), pady=6)
        else:
            # Empty cell so the grid stays aligned
            ctk.CTkLabel(parent, text="", width=80).grid(row=row, column=2)

    def _browse(self, var: ctk.StringVar, browse_type: str) -> None:
        """
        Open a file or folder picker and write the chosen path into var.
        Does nothing if the user cancels the dialog.
        """
        if browse_type == "file":
            path = filedialog.askopenfilename(title="Select file")
        else:  # "folder"
            path = filedialog.askdirectory(title="Select folder")

        # filedialog returns an empty string on cancel — don't overwrite
        if path:
            var.set(path)

    def _on_save(self) -> None:
        """
        Collect current field values and write them to config.json.
        Shows a success confirmation or an error popup (from save_config).
        """
        values = {key: var.get().strip() for key, var in self._vars.items()}

        if save_config(values):
            messagebox.showinfo("Saved", "Settings saved to config.json.")
