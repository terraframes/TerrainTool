# Current Work State

## Active Module
**Widget — Phase 1 (unlock 5×5km globally)**

## Status
Module 2b complete and tested. Widget coverage polygon work is next.

## What Is Built

### Module 4 — COMPLETE
### Module 3 — COMPLETE (processing_status guard added)
### Module 2 — COMPLETE (four-line filter skips non-GLO-30 orders)
### Module 2b — COMPLETE
- local_clip.py, acquire_extended.py, setup.py, requirements.txt
- FO-DEM dataset: 2m DSM, EPSG:5316, nodata 3.4e+38
- TEST_FO_001 passed: raw_dem.tif verified in QGIS, Blender preview correct
- Operator tool: Download DEM routes correctly per dataset
### Module 1 — Pipeline working (Stage 4 deferred)
### Operator Tool — Full end-to-end working

## What To Build Next

### Phase 1 — Unlock 5×5km globally (widget.html)
Find and remove the restriction disabling 5×5km in widget.html.
No coverage polygon logic yet. GLO-30 used for all orders.
Goal: full customer flow testable with small orders.

### Phase 2 — Coverage polygon system (widget)
- Bundle faroe_islands_coverage.geojson with widget files
- Load Turf.js
- On every map move: turf.booleanIntersects(selectionBbox, faroePolygon)
- If intersects AND area_km <= 25: dataset = "FO-DEM"
- Otherwise: dataset = "GLO-30"
- Write dataset value into Shopify line item properties at checkout

### Phase 3 — Widget UX (after Phase 2)
- Green/red square contour by coverage
- Greyed buttons with tooltip
- Coverage info overlay

## Operator Tool Remaining

- Status auto-refresh after Blender closes
- Manual order entry
- Archive tab
- PyInstaller .exe

## Key Decisions Made

- acquire_extended.py writes processing_status: "ready" on success
- Module 3 guards against processing orders with non-ready status
- Operator tool routes Download DEM to correct script per dataset
- 'ready' status added to STATUS_META and Open in Blender enable condition
- Column width fix: order number column 200px

---
*Update this file at the end of every Claude Code session.*
