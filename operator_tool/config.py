"""
config.py — Read and write config.json for the operator tool.
Config file lives in the same folder as this script.
"""

import json
import os
import tkinter.messagebox as messagebox

# Path to config.json, always next to this file
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# All keys used in config.json, in order
CONFIG_KEYS = [
    "blender_path",
    "qgis_bat_path",
    "orders_folder",
    "gdrive_key_path",
    "gdrive_drive_id",
    "opentopo_api_key",
    "mapbox_token",
]


def load_config() -> dict:
    """
    Read config.json and return its contents as a dict.
    Returns an empty dict if the file doesn't exist yet.
    Shows a popup and returns empty dict if the file exists but can't be parsed.
    """
    if not os.path.exists(CONFIG_PATH):
        # First run — no config yet, that's fine
        return {}

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        messagebox.showerror(
            "Config Error",
            f"config.json exists but could not be parsed:\n\n{e}\n\n"
            f"File: {CONFIG_PATH}\n\nFix or delete the file and restart.",
        )
        return {}
    except OSError as e:
        messagebox.showerror(
            "Config Error",
            f"Could not read config.json:\n\n{e}\n\nFile: {CONFIG_PATH}",
        )
        return {}


def save_config(values: dict) -> bool:
    """
    Write the given dict to config.json.
    Only saves keys listed in CONFIG_KEYS — ignores anything extra.
    Returns True on success, False on failure (after showing an error popup).
    """
    # Filter to only known keys so stale keys don't accumulate
    data = {key: values.get(key, "") for key in CONFIG_KEYS}

    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError as e:
        messagebox.showerror(
            "Save Error",
            f"Could not write config.json:\n\n{e}\n\nFile: {CONFIG_PATH}",
        )
        return False
