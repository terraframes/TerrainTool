"""
Module 4 setup script.
Run this ONCE before using Module 4. It will:
  - Check Python version
  - Install Blender 4.5 LTS via winget if not already present
  - Create terrain_export.zip ready to install into Blender
  - Write setup_complete.txt and README.txt when done

No pip packages are needed — the addon uses only Blender's bundled Python.
"""

import sys
import os
import subprocess
import shutil

# ── Helpers ────────────────────────────────────────────────────────────────

def banner(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print('='*60)

def step(msg):
    print(f"\n>> {msg}")

def ok(msg):
    print(f"   OK  {msg}")

def warn(msg):
    print(f"  WARN  {msg}")

def fail(msg):
    print(f"\n  ERROR: {msg}")
    print("  Setup did not complete. Fix the problem above and run setup.py again.")
    sys.exit(1)

# ── 1. Python version ──────────────────────────────────────────────────────

banner("Module 4 — Displacement & Export — Setup")

step("Checking Python version...")
major, minor = sys.version_info[:2]
if (major, minor) != (3, 11):
    fail(
        f"Python 3.11 is required, but you are running {major}.{minor}.\n"
        "  Download Python 3.11 from: https://www.python.org/downloads/release/python-3110/\n"
        "  Make sure to tick 'Add Python to PATH' during installation."
    )
ok(f"Python {major}.{minor} — good.")

# ── 2. Blender ─────────────────────────────────────────────────────────────

step("Checking for Blender...")

blender_exe = None

# Common install locations on Windows
BLENDER_LTS_MSI = "https://download.blender.org/release/Blender4.5/blender-4.5.0-windows-x64.msi"

common_locations = [
    r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
]
for loc in common_locations:
    if os.path.isfile(loc):
        blender_exe = loc
        break

# Also check PATH
if blender_exe is None:
    blender_exe = shutil.which("blender")

if blender_exe:
    ok(f"Blender found at: {blender_exe}")
else:
    step("Blender not found. Attempting install via winget (Blender 4.5 LTS)...")
    winget = shutil.which("winget")
    winget_ok = False

    if winget:
        result = subprocess.run(
            [
                "winget", "install", "--id", "BlenderFoundation.Blender.LTS",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            capture_output=False,
        )
        if result.returncode == 0:
            ok("Blender 4.5 LTS installed via winget.")
            warn(
                "You may need to restart your terminal or PC before 'blender' "
                "is available on your PATH."
            )
            winget_ok = True
        else:
            warn(
                "winget install returned a non-zero exit code.\n"
                "  Falling back to direct MSI download..."
            )
    else:
        warn("winget is not available. Falling back to direct MSI download...")

    if not winget_ok:
        # Download and silently install the Blender 4.5 LTS MSI directly
        import urllib.request
        import tempfile

        msi_path = os.path.join(tempfile.gettempdir(), "blender-4.5.0-windows-x64.msi")
        step(f"Downloading Blender 4.5 LTS MSI (~350 MB)...")
        step(f"  From: {BLENDER_LTS_MSI}")
        step(f"  To:   {msi_path}")

        try:
            urllib.request.urlretrieve(BLENDER_LTS_MSI, msi_path)
            ok("Download complete.")
        except Exception as e:
            warn(
                f"Download failed: {e}\n"
                "  Please install Blender 4.5 LTS manually:\n"
                f"    {BLENDER_LTS_MSI}"
            )
            msi_path = None

        if msi_path and os.path.isfile(msi_path):
            step("Running Blender installer silently (may request admin rights)...")
            result = subprocess.run(
                ["msiexec", "/i", msi_path, "/quiet", "/norestart"],
                capture_output=False,
            )
            if result.returncode == 0:
                ok("Blender 4.5 LTS installed via MSI.")
                warn(
                    "You may need to restart your terminal before 'blender' "
                    "is available on your PATH."
                )
            else:
                warn(
                    f"MSI installer exited with code {result.returncode}.\n"
                    "  Try running the installer manually:\n"
                    f"    msiexec /i \"{msi_path}\""
                )

# ── 4. Create terrain_export.zip for Blender installation ─────────────────

step("Creating terrain_export.zip for Blender installation...")

import zipfile

module_dir  = os.path.dirname(os.path.abspath(__file__))
addon_dir   = os.path.join(module_dir, "terrain_export")
zip_path    = os.path.join(module_dir, "terrain_export.zip")

# Files to include — only the Python source files, no caches or temp files
addon_files = [f for f in os.listdir(addon_dir)
               if f.endswith(".py") and not f.startswith("__pycache__")]

if not addon_files:
    warn("No .py files found in terrain_export/ — zip was not created.")
else:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in addon_files:
            full_path = os.path.join(addon_dir, filename)
            # Store as terrain_export/<filename> so Blender unpacks it as a package
            zf.write(full_path, os.path.join("terrain_export", filename))
    ok(f"terrain_export.zip created: {zip_path}")
    ok(f"  Contains: {', '.join(sorted(addon_files))}")

# ── 6. Write README.txt ────────────────────────────────────────────────────

step("Writing README.txt...")

readme_lines = [
    "Module 4 — Displacement & Export",
    "=" * 50,
    "",
    "STATUS: Setup complete",
    f"Python: {sys.version.split()[0]}",
    f"Blender: {'Found at ' + blender_exe if blender_exe else 'Not found on PATH — install manually'}",
    "Dependencies: none (addon uses only Blender's bundled Python)",
    "",
    "HOW TO USE",
    "-" * 50,
    "",
    "Step 1 — Install the Blender addon:",
    "   Open Blender > Edit > Preferences > Add-ons > Install",
    "   Select:  module4\\terrain_export.zip   (created by this setup.py)",
    "   IMPORTANT: select the .zip, NOT the __init__.py file directly.",
    "   Installing the zip keeps bake.py and base_export.py together as a package.",
    "   Enable the addon: search for 'Terrain Export'",
    "",
    "Step 2 — Run the export pipeline:",
    "   In Blender, press N to open the sidebar",
    "   Find the 'Terrain Export' tab",
    "   Set the Order Folder to the full path of your order folder",
    "   e.g.  E:\\TerrainTool\\orders\\TEST001",
    "   The folder must contain:  resampled.tif  and  params.json",
    "   Click 'Bake Full Res'       — generates displaced.obj and simplified.obj",
    "   Click 'Add Base and Export' — generates final.stl",
    "",
    "OUTPUT FILES (written to the order folder):",
    "   displaced.obj   — full resolution mesh",
    "   simplified.obj  — decimated to ~1M triangles",
    "   final.stl       — watertight, flat base added, print-ready",
    "",
    "TROUBLESHOOTING",
    "-" * 50,
    "- If the addon fails to load: check Blender's Python console for errors",
    "- If displacement looks wrong: confirm resampled.tif is float32 with values in [0, 1]",
    "- If params.json is missing: create it in the order folder (see CLAUDE.md for schema)",
    "",
]

readme_path = os.path.join(os.path.dirname(__file__), "README.txt")
with open(readme_path, "w", encoding="utf-8") as f:
    f.write("\n".join(readme_lines))
ok("README.txt written.")

# ── 7. Write setup_complete.txt ────────────────────────────────────────────

step("Writing setup_complete.txt...")

marker_path = os.path.join(os.path.dirname(__file__), "setup_complete.txt")
with open(marker_path, "w", encoding="utf-8") as f:
    f.write("Setup completed successfully.\n")
ok("setup_complete.txt written.")

# ── Done ───────────────────────────────────────────────────────────────────

banner("Setup complete! Read README.txt for next steps.")
