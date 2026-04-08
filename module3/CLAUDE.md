# Module 3 — Data Refinement (extends terrain_export addon)

**STATUS: COMPLETE.**

## What This Module Does

Extends terrain_export from Module 4. Refinement and live preview before full-resolution bake.
Output is resampled.tif — feeds into the single Bake & Export operation.

## CRITICAL RULE

**Never import osgeo inside the Blender addon.**
All GDAL work via subprocess using QGIS Python.
QGIS bat path stored in qgis_config.json — not hardcoded.

## Files

```
module3/terrain_export/
  resample.py       standalone GDAL script — subprocess only
  preview.py        subprocess calls, preview mesh, debounce timer
  refinement.py     three operators: LoadOrder, BakeResampled, SaveSettings
  qgis_config.json  QGIS bat file path
  __init__.py       unified panel, sliders, update callbacks
```

## QGIS Python

```
C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat
```

## processing_status Guard

TERRAIN_OT_LoadOrder.execute() checks params.json processing_status:
- "pending_lidar_review" → block with message
- "needs_manual_processing" → block with message
- absent or "ready" → proceed normally

## resample.py Interface

```
python-qgis-ltr.bat resample.py --input raw_dem.tif --output out.tif
  --bbox "min_lon,min_lat,max_lon,max_lat" --resolution 256
  --min_clamp 0.0 --max_clamp 1.0 --gamma 1.0
```
Stdout: {"elevation_min_m": ..., "elevation_max_m": ..., "status": "ok"}

## resample.py Processing Order (load-bearing — do not change)

1. gdal_fillnodata — with nodata guard (see below)
2. gdalwarp — two-pass: padded warp (5% bbox + dstNodata=-9999.0), then crop to exact bbox
2b. Edge fill: copy nearest valid row/column to fill invalid edges
3. Normalise → 0–1 (record elevation_min_m, elevation_max_m)
4. Clamp to [min_clamp, max_clamp]
5. Re-normalise → 0–1 (floor exactly 0)
6. Gamma: value = value ^ (1.0 / gamma)
7. Save float32 GeoTIFF

## ⚠ Nodata Guard in fill_nodata()

If the band's declared nodata value is 0.0, skip gdal.FillNodata entirely.
Reason: 0.0 is valid sea level elevation for island/coastal DEMs (e.g. Faroe Islands).
Without this guard, fill_nodata re-interpolates correctly zero-filled ocean pixels,
creating jagged coastline artefacts in Blender.

## Key Design Decisions

- TerrainPreview uses unapplied modifier — texture-only refresh on slider change
- elevation_min/max come from DEM (resample.py stdout), not params.json
- Print height: displacement_scale × print_size_mm ÷ 10 = terrain relief mm
- LoadOrder accepts optional folder property for operator tool launch
- REGISTER removed from bl_options — suppresses popup
