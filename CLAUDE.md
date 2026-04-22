# TerrainTool — Root CLAUDE.md

## Project

E2E pipeline: customer map selection → 3D-printable terrain STL.
Windows 11. Python 3.11. Blender 4.5 LTS. GDAL via QGIS only.

## Critical Rules (never break these)

- **GDAL via subprocess only** — `C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat`
- **Google Shared Drive** — all Drive calls need:
  `supportsAllDrives=True, includeItemsFromAllDrives=True, driveId, corpora='drive'`
- **params.json is single source of truth** across all modules
- **Drive holds params.json only** — all other files local at `E:\TerrainTool\orders\{order_number}\`
- **Blender 4.5 LTS only** — not 5.x
- **Files < 300 lines**
- **Mapbox GL JS uses 512px tiles** → constant `78271.516`, NOT `156543.03392`

## Module Status

| Module | Status |
|--------|--------|
| Module 4 — Blender displacement & export | COMPLETE |
| Module 3 — Refinement addon | COMPLETE |
| Module 2 — GLO-30 acquisition | COMPLETE |
| Module 2b — Extended datasets (Faroe Islands) | COMPLETE |
| Module 1 — Widget + webhook | In progress |
| Operator Tool | In progress |

## Dataset Priority Register

| Priority | Key | Pipeline | Notes |
|----------|-----|----------|-------|
| 1 | ArcticDEM | api_tiled | Best Arctic, no local storage |
| 10 | FO-DEM | local_raster | Complete |
| 11 | NL-AHN4 | api_wcs | First to build |
| 12 | NZ-DSM | api_tiled | Widget bbox check required first |
| 13 | EN-EA | api_tiled | |
| 14 | DK-DHM | api_wcs | API key needed |
| 15 | NO-DOM | api_wcs | |
| 16 | SE-LiDAR | LiDAR pipeline | |
| 17 | BE-merged | local_raster | Offline QGIS mosaic |
| 18 | LU | local_raster | Offline QGIS mosaic |
| 19 | ES-PNOA | LiDAR pipeline | |
| 20 | FI-MML | LiDAR pipeline | |
| 21 | CZ-DMP | api_tiled | |
| 99 | GLO-30 | Module 2 | Global fallback |

Priority integers must stay in sync between local_datasets.json, api_datasets.json, and widget.

## Dataset Registry Files

- **local_datasets.json** — local_raster type. Fields: path, coverage, resolution_m, epsg, nodata, nodata_fill, type, dsm, priority.
- **api_datasets.json** (to be created) — api_wcs and api_tiled types. Fields: endpoint/bucket, coverage, resolution_m, crs, nodata, type, dsm, priority, plus type-specific (wcs_layer / stac_catalog_url).

## Coverage GeoJSON Authoring — Two Types

**Simple survey union** (continental datasets): tile index → union → simplify ~500m → EPSG:4326.
**Island/coastal** (NZ, Faroe Islands done): QGIS manual — survey index union + ocean buffer (50km OK) + dissolve + simplify + export. Stay in vector.

## Widget Coverage Check — Planned Upgrade

Current: centre-point-in-polygon.
Required before NZ-DSM or any fragmented dataset:
- Compute bbox live on every map move + slider change
- Switch to `turf.booleanContains(coveragePolygon, bboxPolygon)`
- Iterate datasets in priority order, display winning dataset name in UI
Hard prerequisite — do not skip.

## Key Technical Decisions

### Mapbox Tile Constant
Formula: `pixel_size = (area_km * 1000) / ((78271.516 * cos(lat)) / 2^zoom)`

### nodata Handling
- Exact float: `3.3999999521443642e+38` for FO-DEM (not 3.4e+38)
- `repr(nodata_value)` in subprocess strings
- `nodata_fill: "zero"` for coastal DEMs; `"interpolate"` for land DEMs
- resample.py guard: skip gdal.FillNodata if band nodata == 0.0

### processing_status
- absent or `"ready"` → proceed; `"pending_lidar_review"` or `"needs_manual_processing"` → block

### Slider (Module 1)
- `HIGH_RES_THRESHOLD_KM = 25`, `LEFT_SEGMENT_END_PCT = 25`
- `SNAP_LIST` defines all sizes — 25 must always be present
- update event: no auto-zoom. change event: snap + auto-zoom.
