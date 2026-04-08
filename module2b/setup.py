"""
Module 2b setup — run once per machine before using acquire_extended.py.

Checks dependencies, prompts for credentials, writes env vars via setx,
verifies QGIS bat file and local_datasets.json, then writes setup_complete.txt.
"""

import os
import sys
import subprocess
import importlib.util

SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_COMPLETE = os.path.join(SETUP_DIR, "setup_complete.txt")
QGIS_BAT = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
REQUIREMENTS = os.path.join(SETUP_DIR, "requirements.txt")
LOCAL_DATASETS_JSON = r"E:\TerrainTool\datasets\local_datasets.json"


def step(label):
    print(f"\n[{label}]")


def fail(msg):
    print(f"\nERROR: {msg}")
    print("Setup did not complete. Fix the issue above and run setup.py again.")
    sys.exit(1)


# ── 1. Python version ────────────────────────────────────────────────────────

step("Checking Python version")
major, minor = sys.version_info[:2]
if (major, minor) != (3, 11):
    print(f"  Found Python {major}.{minor}.")
    print("  This project requires Python 3.11.")
    print("  Install it with:  winget install Python.Python.3.11")
    fail("Wrong Python version.")
print(f"  Python {major}.{minor} — OK")


# ── 2. Pip packages ──────────────────────────────────────────────────────────

step("Installing pip packages")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS],
    capture_output=False,
)
if result.returncode != 0:
    fail("pip install failed. Check the error above.")
print("  Packages installed — OK")


# ── 3. Verify imports ────────────────────────────────────────────────────────

step("Verifying imports")
missing = []
for pkg in ("googleapiclient", "google.auth", "requests"):
    if importlib.util.find_spec(pkg.split(".")[0]) is None:
        missing.append(pkg)
if missing:
    fail(f"These packages failed to import after install: {missing}")
print("  All imports OK")


# ── 4. QGIS bat file ─────────────────────────────────────────────────────────

step("Checking QGIS Python executable")
if not os.path.isfile(QGIS_BAT):
    print(f"  Not found: {QGIS_BAT}")
    print("  Install QGIS 3.44.8 LTS from https://qgis.org/")
    fail("QGIS bat file missing.")
print(f"  Found: {QGIS_BAT} — OK")


# ── 5. Verify local_datasets.json ────────────────────────────────────────────

step("Checking local_datasets.json")
if not os.path.isfile(LOCAL_DATASETS_JSON):
    print(f"  Not found: {LOCAL_DATASETS_JSON}")
    print("  This file is the registry of local raster datasets for Module 2b.")
    print("  Create it at the path above before running setup.")
    print("  See README.txt for the required format.")
    fail("local_datasets.json missing.")
print(f"  Found: {LOCAL_DATASETS_JSON} — OK")


# ── 6. Environment variables ─────────────────────────────────────────────────
# Only the two vars Module 2b needs — GDRIVE_KEY_PATH and GDRIVE_ORDERS_DRIVE_ID.
# OPENTOPO and Copernicus credentials live in Module 2 — not needed here.

ENV_VARS = {
    "GDRIVE_KEY_PATH": {
        "prompt": "Path to Google Drive service account JSON key file",
        "example": r"E:\TerrainTool\credentials\gdrive_key.json",
        "validate": os.path.isfile,
        "validate_msg": "File not found. Provide the full path to an existing .json key file.",
    },
    "GDRIVE_ORDERS_DRIVE_ID": {
        "prompt": "Google Shared Drive ID for the 'orders' drive",
        "example": "0ABCxyz123...",
        "validate": None,
    },
}

step("Configuring environment variables")
written = []
skipped = []

for var, cfg in ENV_VARS.items():
    current = os.environ.get(var, "")
    if current:
        print(f"  {var} already set — skipping")
        skipped.append(var)
        continue

    print(f"\n  {var}")
    print(f"  {cfg['prompt']}")
    print(f"  Example: {cfg['example']}")
    value = input("  Value: ").strip()

    if not value:
        fail(f"{var} cannot be empty.")

    if cfg["validate"] and not cfg["validate"](value):
        fail(cfg["validate_msg"])

    result = subprocess.run(
        ["setx", var, value],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f"setx failed for {var}: {result.stderr.strip()}")
    print(f"  {var} saved — OK")
    written.append(var)

print("\n  Environment variables:")
print(f"    Set now : {written if written else 'none (all already set)'}")
print(f"    Skipped : {skipped if skipped else 'none'}")
if written:
    print("\n  NOTE: Restart your terminal for new env vars to take effect.")


# ── 7. Write setup_complete.txt ───────────────────────────────────────────────

step("Writing setup_complete.txt")
with open(SETUP_COMPLETE, "w") as f:
    f.write("Setup completed successfully.\n")
print(f"  Written: {SETUP_COMPLETE}")


# ── Done ──────────────────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("Setup complete. You can now run:  python acquire_extended.py")
print("=" * 50)
