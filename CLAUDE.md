# Terrain Print Tool

A pipeline that converts a customer's geographic map selection into a 3D-printable terrain model.
Windows 11 only. Python 3.11. See CURRENT.md for active module status.

## Project Structure

```
E:\TerrainTool\
  CLAUDE.md              ← you are here
  CURRENT.md             ← active module, current task, known issues
  credentials\           ← service account keys (never commit)
  orders\                ← one subfolder per order (local files only)
  module1\               ← Mapbox widget + Shopify webhook
  module2\               ← DEM data acquisition
  module3\               ← Blender refinement addon
  module4\               ← Blender displacement + export addon
```

## File Storage — Drive vs Local

**Google Drive holds params.json only.** All other files are local only.

| File | Location |
|------|----------|
| params.json | Google Drive: orders/{order_number}/ |
| raw_dem.tif | Local: E:\TerrainTool\orders\{order_number}\ |
| resampled.tif | Local: E:\TerrainTool\orders\{order_number}\ |
| displaced.obj | Local: E:\TerrainTool\orders\{order_number}\ |
| simplified.obj | Local: E:\TerrainTool\orders\{order_number}\ |
| final.stl | Local: E:\TerrainTool\orders\{order_number}\ |

**Pending order detection:** params.json on Drive AND raw_dem.tif absent locally.

## Build Order

| Priority | Module | Status |
|----------|--------|--------|
| 1st | Module 4 — Blender displacement & export | COMPLETE |
| 2nd | Module 3 — Blender refinement addon | COMPLETE |
| 3rd | Module 2 — DEM acquisition | In progress — Sessions 1 & 2 done |
| 4th | Module 1 — Widget + Shopify | Not started |

## Non-Negotiable Technical Rules

- **NEVER import osgeo anywhere.** GDAL is never installed via pip on this machine.
  All GDAL operations call the QGIS Python executable via subprocess:
  `C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat`
- **NEVER write raw_dem.tif (or any processed file) to Google Drive.**
  Drive holds params.json only.
- **params.json is the single source of truth.** Never hardcode values from it.
- **setup.py runs first on every machine.** Check for setup_complete.txt at startup.
- **Print clear plain-English error messages. Never fail silently.**
- **Keep files under 300 lines.** Split into helper files if needed.

## params.json Schema (contract between all modules)

```json
{
  "order_number": "10042",
  "bbox": { "min_lat": 0.0, "max_lat": 0.0, "min_lon": 0.0, "max_lon": 0.0 },
  "center_lat": 0.0,
  "center_lon": 0.0,
  "area_km": 50,
  "dataset": "GLO-30",
  "dem_resolution_m": 30,
  "elevation_min_m": 0.0,
  "elevation_max_m": 0.0,
  "min_clamp": 0.0,
  "max_clamp": 1.0,
  "gamma": 1.0,
  "displacement_scale": 0.3,
  "print_size_mm": 200,
  "base_thickness_mm": 10,
  "subdivision_level": 1024,
  "target_triangles": 1000000
}
```

## Credentials & Services

- Google Cloud project: terraintool
- Service account: terraintool-orders@terraintool.iam.gserviceaccount.com
- Credentials file: E:\TerrainTool\credentials\gdrive_key.json
- Copernicus S3 endpoint: https://eodata.dataspace.copernicus.eu, bucket: eodata
- S3 credentials page: s3-credentials.dataspace.copernicus.eu (regenerate before expiry)

## Environment Variables

Set via setx in setup.py. Never hardcode.
- `GDRIVE_KEY_PATH` — E:\TerrainTool\credentials\gdrive_key.json
- `OPENTOPO_API_KEY` — OpenTopography API key
- `CDSE_S3_KEY` — Copernicus S3 access key ID (replaces CDSE_USER)
- `CDSE_S3_SECRET` — Copernicus S3 secret access key (replaces CDSE_PASS)
- Mapbox token — JS constant in widget HTML only, not an env var

Note: CDSE_USER and CDSE_PASS are no longer used anywhere.

## EEA-39 Dataset Threshold

European detection uses bounding box approximation (eea39_bbox.py — no GeoJSON needed).
- European AND area_km <= 25 → GLO-10 (Copernicus S3, 10m)
- European AND area_km > 25 → GLO-30 (OpenTopography, 30m)
- Non-European → GLO-30

## Setup System

Each module: setup.py + requirements.txt + README.txt.
setup.py uses winget for Python 3.11, Blender 4.5 LTS (modules 3/4), Node.js (module 1).
Modules 2/3 setup.py also verifies QGIS bat file exists and osgeo imports from it.

@CURRENT.md

## Future High-Resolution Dataset Architecture

When high-res datasets are added (LiDAR, national DEMs), these rules apply:

### Coverage Polygons
- Each dataset has a coverage GeoJSON bundled with the widget
- Derived from the dataset's tile index (not country boundary) — handles partial coverage correctly
- Water tiles included in coverage (treated as elevation 0 by gdal_fillnodata)
- Manually editable in QGIS at any time — just replace the file
- Widget checks union of all coverage polygons at the requested resolution tier
- Turf.js handles polygon union client-side on every camera move

### Cross-Border Orders
- If bbox spans two different high-res dataset areas: set processing_status = "needs_manual_processing" in params.json
- Do NOT fall back to GLO-30 silently — customer paid for a specific resolution
- Operator handles manually until automated multi-source merge is built

### params.json Status Field (future)
"processing_status": "ready" | "pending_lidar_review" | "needs_manual_processing"
Module 3 will check this and refuse to process until status = "ready"

### Dataset Routing (future)
Priority-ordered selector, not if/else chains:
1. Check high-res coverage (LiDAR etc.) for bbox — all four corners in union polygon?
2. Check medium-res national DEM coverage
3. Fall back to GLO-30

### LiDAR Pipeline (Sweden, when built)
Module 2: download LAZ tiles → flag pending_lidar_review
QGIS step: operator reviews point cloud, rasterises full tile area → raw_dem_full.tif
gdalwarp crops to bbox → raw_dem.tif → normal Module 3/4 flow
Coordinate system: SWEREF99TM (EPSG:3006) → resample.py reprojects to EPSG:4326 already
