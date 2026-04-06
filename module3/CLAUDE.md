# Module 3 — Data Refinement (extends terrain_export addon)

**STATUS: In progress — Session 1 complete. Session 2 to add Blender panel.**

## What This Module Does

Extends the existing terrain_export addon from Module 4. Adds a refinement panel
above the existing export controls in the same N-panel tab. Loads raw_dem.tif,
runs GDAL resampling via QGIS Python subprocess, provides live 3D preview with
sliders, saves settings to params.json for Module 4 to use.

## CRITICAL RULE

**Never import osgeo inside the Blender addon.**
All GDAL work is in resample.py, called via subprocess using the QGIS Python executable.
GDAL is NOT available in system Python on this machine — do not attempt pip install gdal.

## QGIS Python Executable

All subprocess calls to resample.py must use this executable:
```
C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat
```
QGIS Python is version 3.12. This is acceptable for resample.py only.

## Files In This Folder

```
/module3/
  setup.py                   checks Blender + QGIS bat path + osgeo import
  requirements.txt           pip packages (numpy only — no gdal)
  README.txt                 auto-written by setup.py
  setup_complete.txt         written by setup.py on success
  terrain_export/            extends Module 4's addon folder
    __init__.py              adds refinement panel above existing export controls
    resample.py              BUILT AND TESTED — do not modify without reason
```

## resample.py — Already Built (Session 1)

Location: module3/terrain_export/resample.py

Arguments:
```
python-qgis-ltr.bat resample.py --input raw_dem.tif --output out.tif
  --bbox "min_lon,min_lat,max_lon,max_lat" --resolution 256
  --min_clamp 0.0 --max_clamp 1.0 --gamma 1.0
```

Pipeline: gdal_fillnodata → gdalwarp (EPSG:4326, N×N float32) →
          normalise → clamp → re-normalise → gamma → save float32 GeoTIFF

Stdout on success: {"elevation_min_m": ..., "elevation_max_m": ..., "status": "ok"}
Stdout on failure: {"status": "error", "message": "..."}

Always parse stdout as JSON. Never use stderr for control flow.

## Session 2 — What To Build

Add to terrain_export/__init__.py above the existing Module 4 buttons:

1. 'Load Order' button:
   - Read params.json from order folder
   - Call resample.py via QGIS subprocess at 256×256 (Steps 1–3: fillnodata + warp + normalise)
   - Store elevation_min_m and elevation_max_m from stdout JSON
   - Create 256×256 subdivided plane, apply displacement modifier using output TIF

2. Four sliders — on change re-run Steps 4–7 via subprocess, refresh texture:
   - min_clamp: float 0.0–1.0 (label shows metres equivalent)
   - max_clamp: float 0.0–1.0 (label shows metres equivalent)
   - gamma: float 0.5–3.0
   - displacement_scale: float, ratio of plane width

3. 'Save Settings' button:
   - Write min_clamp, max_clamp, gamma, displacement_scale,
     elevation_min_m, elevation_max_m to params.json

4. 'Bake Full Res' button:
   - Call resample.py at subdivision_level resolution
   - Save output as resampled.tif in order folder

## Processing Order (inside resample.py — do not change)

1. gdal_fillnodata
2. gdalwarp → EPSG:4326, bbox crop, N×N pixels, float32
3. Normalise full range to 0–1 (record elevation_min_m, elevation_max_m)
4. Clamp to [min_clamp, max_clamp]
5. Re-normalise back to 0–1 (floor = exactly 0)
6. Gamma: value = value ^ (1.0 / gamma)
7. Save as float32 GeoTIFF

## Setup Requirements (setup.py must handle)

- Check Blender 4.5 LTS installed — winget install BlenderFoundation.Blender.LTS if not
- Check QGIS bat file exists at expected path
- Run a quick subprocess test: python-qgis-ltr.bat -c "from osgeo import gdal; print('ok')"
- If either check fails: print manual QGIS download instructions (qgis.org), exit
- pip packages: numpy only (no gdal)
