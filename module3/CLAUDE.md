# Module 3 — Data Refinement (extends terrain_export addon)

**STATUS: COMPLETE.**

## What This Module Does

Extends terrain_export from Module 4. Adds a refinement and live preview stage
before the full-resolution bake. Output is resampled.tif — the exact file Module 4
Step 1 and Step 2 have always expected.

## CRITICAL RULE

**Never import osgeo inside the Blender addon.**
All GDAL work runs through resample.py via subprocess using QGIS Python.
QGIS bat file path is read from qgis_config.json at addon load time.

## Files

```
module3/terrain_export/
  resample.py       standalone GDAL script — never import, always subprocess
  preview.py        subprocess calls, preview mesh creation, debounce timer
  refinement.py     three operators: LoadOrder, BakeResampled, SaveSettings
  qgis_config.json  stores QGIS bat file path — update if QGIS path changes
  __init__.py       modified from Module 4 — panel, sliders, update callbacks
```

## QGIS Python

```
C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat
```
Path stored in qgis_config.json — do not hardcode in Python files.

## resample.py Interface

```
python-qgis-ltr.bat resample.py --input raw_dem.tif --output out.tif
  --bbox "min_lon,min_lat,max_lon,max_lat" --resolution 256
  --min_clamp 0.0 --max_clamp 1.0 --gamma 1.0
```
Stdout success: {"elevation_min_m": ..., "elevation_max_m": ..., "status": "ok"}
Stdout failure: {"status": "error", "message": "..."}
Always parse stdout as JSON. Never use stderr for control flow.

## resample.py Processing Order (do not change)

1. gdal_fillnodata on input
2. gdalwarp — TWO-PASS: first warp with 5% bbox padding + dstNodata=-9999.0,
   then crop back to exact bbox. dstNodata=-9999.0 must be set on BOTH passes.
2b. Edge fill: detect invalid edge rows/columns, fill by copying nearest valid
    row/column inward. Update valid mask after fill.
3. Normalise → 0–1 (record elevation_min_m, elevation_max_m)
4. Clamp to [min_clamp, max_clamp]
5. Re-normalise → 0–1 (floor exactly 0)
6. Gamma: value = value ^ (1.0 / gamma)
7. Save float32 GeoTIFF

## ⚠ Load-Bearing Fixes — Do Not Remove

These fixes were found during real DEM testing. Do not simplify or remove them:

**Bug 1 fixed — Wrong elevation_min_m:**
gdalwarp was filling edge pixels with 0.0 without flagging them as NoData.
Normalisation then treated 0.0 as valid terrain, making min appear as 0.
Fix: dstNodata=-9999.0 on the warp call.

**Bug 2 fixed — Edge wall artefacts:**
Source DEM didn't fully cover bbox, gdalwarp was extrapolating at edges.
Fix: two-pass warp (padded then crop) + edge fill copying nearest valid row/column.

**Bug 3 fixed — Jagged crop boundary:**
Bicubic resampling interpolated between real terrain and nodata at crop edge.
Resolved as part of Bug 2 fix.

## Key Design Decisions

- TerrainPreview uses unapplied Displace modifier — texture-only refresh on slider change
- elevation_min/max come from DEM (resample.py stdout), not from params.json
- Print height estimate: displacement_scale × print_size_mm ÷ 10 = terrain relief mm
- Step 1 (BakeFullRes) hides TerrainPreview automatically after bake

## params.json Fields Written by SaveSettings

min_clamp, max_clamp, gamma, displacement_scale, elevation_min_m, elevation_max_m,
print_size_mm, base_thickness_mm
