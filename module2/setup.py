"""
Module 2 setup — run once per machine before using acquire.py.

Checks dependencies, prompts for credentials, writes env vars via setx,
verifies QGIS bat file, then writes setup_complete.txt and README.txt.
"""

import os
import sys
import subprocess
import importlib.util

SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_COMPLETE = os.path.join(SETUP_DIR, "setup_complete.txt")
README = os.path.join(SETUP_DIR, "README.txt")
QGIS_BAT = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
REQUIREMENTS = os.path.join(SETUP_DIR, "requirements.txt")


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
for pkg in ("googleapiclient", "google.auth", "requests", "boto3"):
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


# ── 5. Environment variables ─────────────────────────────────────────────────

ENV_VARS = {
    "GDRIVE_KEY_PATH": {
        "prompt": "Path to Google Drive service account JSON key file",
        "example": r"C:\keys\terrain-gdrive-key.json",
        "validate": os.path.isfile,
        "validate_msg": "File not found. Provide the full path to an existing .json key file.",
    },
    "OPENTOPO_API_KEY": {
        "prompt": "OpenTopography API key",
        "example": "abc123...",
        "validate": None,
    },
    "CDSE_USER": {
        "prompt": "Copernicus CDSE username (email)",
        "example": "you@example.com",
        "validate": None,
    },
    "CDSE_PASS": {
        "prompt": "Copernicus CDSE password",
        "example": "(your password)",
        "validate": None,
        "secret": True,
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

    if cfg.get("secret"):
        import getpass
        value = getpass.getpass("  Value: ").strip()
    else:
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


# ── 6. Write setup_complete.txt ───────────────────────────────────────────────

step("Writing setup_complete.txt")
with open(SETUP_COMPLETE, "w") as f:
    f.write("Setup completed successfully.\n")
print(f"  Written: {SETUP_COMPLETE}")


# ── 7. Write README.txt ───────────────────────────────────────────────────────

step("Writing README.txt")

import importlib.metadata

def pkg_version(name):
    try:
        return importlib.metadata.version(name)
    except Exception:
        return "unknown"

env_status = {var: ("SET" if os.environ.get(var) else "NOT SET (restart terminal if just set)")
              for var in ENV_VARS}

readme_lines = [
    "Module 2 — DEM Data Acquisition",
    "=" * 40,
    "",
    "USAGE",
    "  python acquire.py",
    "  Scans Google Drive for pending orders and downloads params.json locally.",
    "  Run from E:\\TerrainTool\\module2\\",
    "",
    "SETUP STATUS",
    f"  Python         : {sys.version.split()[0]}",
    f"  google-api     : {pkg_version('google-api-python-client')}",
    f"  google-auth    : {pkg_version('google-auth')}",
    f"  requests       : {pkg_version('requests')}",
    f"  boto3          : {pkg_version('boto3')}",
    f"  QGIS bat       : {'OK' if os.path.isfile(QGIS_BAT) else 'MISSING'}",
    "",
    "ENVIRONMENT VARIABLES",
]
for var, status in env_status.items():
    readme_lines.append(f"  {var:<20} : {status}")

readme_lines += [
    "",
    "NOTES",
    "  - Google Drive service account must be shared on the 'orders' folder.",
    "  - params.json downloaded to E:\\TerrainTool\\orders\\{order_number}\\",
    "  - raw_dem.tif is NEVER written to Google Drive.",
    "  - Run setup.py again if env vars change.",
]

with open(README, "w") as f:
    f.write("\n".join(readme_lines) + "\n")
print(f"  Written: {README}")


# ── Done ──────────────────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("Setup complete. You can now run:  python acquire.py")
print("=" * 50)
