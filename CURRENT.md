# Current Work State

## Active Module
**Module 2b — NL-AHN4 (first api_wcs dataset)**

## What Is Built

### Module 4 — COMPLETE
### Module 3 — COMPLETE
### Module 2 — COMPLETE
### Module 2b
- FO-DEM (local_raster): COMPLETE
- ArcticDEM (api_tiled): COMPLETE
  - acquire_tiled.py: STAC query, vsicurl VRT, gdalwarp, VRT cleanup
  - api_datasets.json created
  - acquire_extended.py updated: loads both registries, routes by type
  - pystac-client added to requirements.txt
### Module 1
- Stages 1–3 + slider + full bbox containment + coverage modal + multi-dataset priority loop
- ArcticDEM GeoJSON built and live
- Coverage system fully live with FO-DEM + ArcticDEM
### Operator Tool — Full end-to-end working

## Key Lessons from ArcticDEM Implementation

- vsicurl: passes GDAL HTTP config vars in subprocess; s3:// → https:// URL conversion needed
- gdal.BuildVRT (capital V) — BuildVrt does not exist, throws AttributeError
- Coverage GeoJSON must be FeatureCollection of Polygon features — NOT MultiPolygon
  (turf.booleanContains throws AttributeError on MultiPolygon)
- Dissolve tile indexes in EPSG:4326, NOT in polar CRS (antimeridian wrapping)
- Pre-simplify coverage GeoJSONs before deployment (complex polygons = unusable map)
- _coverageReady flag in coverage.js is essential — guards all coverage check entry points
  until Promise.all fetches complete (without it: feedback loop on slider init)

## Next: NL-AHN4 (first api_wcs)

Add to api_datasets.json:
```json
"NL-AHN4": {
  "wcs_url": "https://service.pdok.nl/rws/ahn/wcs/v1_0",
  "wcs_layer": "dsm_05m",
  "coverage": "E:\\TerrainTool\\datasets\\nl\\nl_coverage.geojson",
  "resolution_m": 0.5, "epsg": 28992,
  "nodata": 3.4028235e+38,
  "nodata_fill": "interpolate",
  "type": "api_wcs", "dsm": true, "priority": 11
}
```

Build acquire_wcs.py handler. Add Netherlands coverage GeoJSON to widget /docs/.
Author NL coverage GeoJSON in QGIS (simple country outline, ~500m tolerance, EPSG:4326).

## Remaining Work

### Module 2b datasets
- Offline QGIS: LU, BE (one QGIS session each)
- api_wcs: NL-AHN4 → NO-DOM → DK-DHM
- api_tiled: NZ-DSM, EN-EA (bbox check already done in widget)
- LiDAR pipeline: SE-LiDAR + US-3DEP bundle

### Operator Tool
- Status auto-refresh after Blender closes
- Headless Blender export (--background)
- Manual order entry, archive tab, PyInstaller .exe

---
*Update this file at the end of every Claude Code session.*
