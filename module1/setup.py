"""
Module 1 Stage 2 setup — run once per machine before using webhook.py.

Checks Python version, installs packages, prompts for env vars, writes
setup_complete.txt and README.txt.
"""

import importlib.metadata
import importlib.util
import os
import subprocess
import sys

SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_COMPLETE = os.path.join(SETUP_DIR, "setup_complete.txt")
README = os.path.join(SETUP_DIR, "README.txt")
REQUIREMENTS = os.path.join(SETUP_DIR, "requirements.txt")


def step(label):
    print(f"\n[{label}]")


def fail(msg):
    print(f"\nERROR: {msg}")
    print("Setup did not complete. Fix the issue above and run setup.py again.")
    sys.exit(1)


# ── 1. Python version ─────────────────────────────────────────────────────────

step("Checking Python version")
major, minor = sys.version_info[:2]
if (major, minor) != (3, 11):
    print(f"  Found Python {major}.{minor}.")
    print("  This project requires Python 3.11.")
    print("  Install it with:  winget install Python.Python.3.11")
    fail("Wrong Python version.")
print(f"  Python {major}.{minor} — OK")


# ── 2. Pip packages ───────────────────────────────────────────────────────────

step("Installing pip packages")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS],
    capture_output=False,
)
if result.returncode != 0:
    fail("pip install failed. Check the error above.")
print("  Packages installed — OK")


# ── 3. Verify imports ─────────────────────────────────────────────────────────

step("Verifying imports")
missing = []
for pkg in ("flask", "googleapiclient", "google.auth", "requests"):
    if importlib.util.find_spec(pkg.split(".")[0]) is None:
        missing.append(pkg)
if missing:
    fail(f"These packages failed to import after install: {missing}")
print("  All imports OK")


# ── 4. Environment variables ──────────────────────────────────────────────────

ENV_VARS = {
    "GDRIVE_KEY_PATH": {
        "prompt": "Path to Google Drive service account JSON key file",
        "example": r"E:\TerrainTool\credentials\gdrive_key.json",
        "validate": os.path.isfile,
        "validate_msg": "File not found. Provide the full path to an existing .json key file.",
    },
    "MAPBOX_TOKEN": {
        "prompt": "Mapbox public access token (used to construct Static Images URLs)",
        "example": "pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjbGV4YW1wbGUifQ.example",
        "validate": None,
    },
    "GDRIVE_ORDERS_DRIVE_ID": {
        "prompt": "Google Shared Drive ID for the 'orders' folder",
        "example": "1ABC123xyz_your_shared_drive_id_here",
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

    os.environ[var] = value
    print(f"  {var} saved — OK")
    written.append(var)

print("\n  Environment variables:")
print(f"    Set now : {written if written else 'none (all already set)'}")
print(f"    Skipped : {skipped if skipped else 'none'}")
if written:
    print("\n  NOTE: Restart your terminal for new env vars to take effect.")


# ── 5. Write setup_complete.txt ───────────────────────────────────────────────

step("Writing setup_complete.txt")
with open(SETUP_COMPLETE, "w") as f:
    f.write("Setup completed successfully.\n")
print(f"  Written: {SETUP_COMPLETE}")


# ── 6. Write README.txt ───────────────────────────────────────────────────────

step("Writing README.txt")


def pkg_version(name):
    try:
        return importlib.metadata.version(name)
    except Exception:
        return "unknown"


env_status = {
    var: ("SET" if os.environ.get(var) else "NOT SET (restart terminal if just set)")
    for var in ENV_VARS
}

readme_lines = [
    "Module 1 Stage 2 — Shopify Webhook Receiver",
    "=" * 45,
    "",
    "USAGE",
    "  python webhook.py",
    "  Listens on http://localhost:5000/webhook for Shopify orders/paid webhooks.",
    "  For local testing use ngrok to expose the port, then set the URL in Shopify.",
    "",
    "  python test_webhook.py",
    "  Sends a fake Shopify payload to localhost:5000 for testing without Shopify.",
    "",
    "CLOUD DEPLOYMENT NOTE",
    "  On Railway/Render, set GDRIVE_KEY_JSON (full service account JSON string).",
    "  GDRIVE_KEY_PATH is for local use only and does not need to be set in the cloud.",
    "",
    "SETUP STATUS",
    f"  Python                    : {sys.version.split()[0]}",
    f"  flask                     : {pkg_version('flask')}",
    f"  google-api-python-client  : {pkg_version('google-api-python-client')}",
    f"  google-auth               : {pkg_version('google-auth')}",
    f"  requests                  : {pkg_version('requests')}",
    "",
    "ENVIRONMENT VARIABLES",
]
for var, status in env_status.items():
    readme_lines.append(f"  {var:<20} : {status}")

readme_lines += [
    "",
    "NOTES",
    "  - Google Drive service account must have write access to the 'orders' folder.",
    "  - params.json is written to Drive: orders/{order_number}/params.json",
    "  - order.txt is written locally: E:\\TerrainTool\\orders\\{order_number}\\order.txt",
    "  - Drive writes are async — the 200 response is never delayed.",
    "  - Run setup.py again if env vars change.",
]

with open(README, "w") as f:
    f.write("\n".join(readme_lines) + "\n")
print(f"  Written: {README}")


# ── Done ──────────────────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("Setup complete. You can now run:  python webhook.py")
print("=" * 50)
