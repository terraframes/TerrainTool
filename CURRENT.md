# Current Work State

## Active Module
No active build. Next: offline QGIS pre-processing (LU, BE) or widget bbox upgrade.

## What Is Built

### Module 4 — COMPLETE
### Module 3 — COMPLETE
### Module 2 — COMPLETE
### Module 2b — COMPLETE (FO-DEM local_raster)
### Module 1 — Stages 1–3 + slider built
### Operator Tool — Full end-to-end working

## Dataset Architecture Decisions Made

- Priority register finalised (see root CLAUDE.md)
- Two registry files: local_datasets.json (exists) + api_datasets.json (to create)
- Offline pre-processing for LU and BE: local_raster entries, one-time QGIS work
- Tiled local datasets (SE if LiDAR not yet built): 100×100km tiles, SW corner naming convention
- Priority integers must stay in sync between both registries and widget

## Immediate Next Steps

### Option A: Offline pre-processing (no code changes needed)
1. Luxembourg: download source, rasterise/reproject/compress → LU_2m_merged.tif
   Add entry to local_datasets.json with priority=18
2. Belgium: download Flanders + Wallonia + Brussels, mosaic → BE_2m_merged.tif
   Add entry to local_datasets.json with priority=17
3. Denmark: assess local_raster vs api_wcs based on file size

### Option B: Widget bbox upgrade (prerequisite for NZ-DSM + multi-dataset)
1. Compute bbox live in coverage.js on every map move + slider change
2. Switch to turf.booleanContains(coveragePolygon, bboxPolygon)
3. Load all coverage GeoJSONs on init, iterate in priority order
4. Display winning dataset name in UI
5. Write winning dataset to confirm payload (no recomputation)

### Option C: First api_wcs dataset (NL-AHN4)
- Create api_datasets.json
- Build api_wcs handler in acquire_extended.py
- WCS endpoint: https://service.pdok.nl/rws/ahn/wcs/v1_0
- Coverage: dsm_05m, EPSG:28992, nodata 3.4028235e+38, CC-0

## Research Still Required

- NO-DOM: confirm DSM (not DTM) endpoint; confirm CC-BY-4.0 for commercial derived products
- EN-EA: confirm OGL commercial use; confirm programmatic tile access still works
- DK-DHM: set up Datafordeler API key before June 2026 web login phaseout
- BE-DHMV: confirm Wallonia + Brussels available for mosaic
- CZ-DMP, ES-PNOA, FI-MML, LU-LIDAR: confirm commercial licence
- Switzerland, France: likely blocked — verify
- Scotland/Wales: confirm same EA pattern as England
- NZ coverage GeoJSON: author in QGIS before NZ-DSM launches

## Remaining Operator Tool Work

- Status auto-refresh after Blender closes
- Manual order entry
- Archive tab
- PyInstaller .exe
- Headless Blender export (--background)
- Show which dataset was used per order (useful once multi-dataset live)
- Dataset column width (80 → 110px, cosmetic)

---
*Update this file at the end of every Claude Code session.*
