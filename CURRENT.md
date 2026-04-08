# Current Work State

## Active Module
No active module — full pipeline working with real Faroe Islands orders.
Next: coverage info overlay, or operator tool improvements.

## What Is Built

### Module 4 — COMPLETE
### Module 3 — COMPLETE
- processing_status guard in LoadOrder
- nodata guard in fill_nodata(): skip gdal.FillNodata if band nodata == 0.0
### Module 2 — COMPLETE
### Module 2b — COMPLETE
- nodata_fill field in local_datasets.json (zero/interpolate)
- Exact nodata float: 3.3999999521443642e+38 (not 3.4e+38)
- repr(nodata_value) in subprocess strings for full precision
- FO-DEM: ocean = 0.0 (sea level), not interpolated
- Real order end-to-end confirmed, clean terrain, no coastline artefacts
### Module 1 — Stages 1–3 + Widget Phases 1–3 complete
- coverage.js: map centre vs polygon, sets dataset field
- Unavailable state UX: red overlay, disabled Select
- dataset in Shopify line item properties (six fields total)
- webhook.py: reads dataset from line item properties (defaults GLO-30)
### Operator Tool — Full end-to-end working

## Key Decisions / Bug Fixes

- nodata must use exact float — 3.3999999521443642e+38, NOT 3.4e+38
- srcNodata in gdalwarp subprocess must use repr(nodata_value)
- nodata_fill: "zero" for coastal/island DEMs, "interpolate" for land DEMs
- resample.py guard: if band nodata == 0.0, skip fill_nodata entirely
- webhook.py now reads dataset from Shopify line item properties

## Remaining Work

### Widget
1. Coverage info overlay (Section 8.3) — tooltip → overlay with dataset info
2. Stage 4: real Shopify checkout (low priority)

### Operator Tool
1. Status auto-refresh after Blender closes
2. Manual order entry
3. Archive tab
4. PyInstaller .exe
5. Headless Blender export (--background, Step 3)
6. Dataset column width (80 → 110px, cosmetic)

### Future Datasets
- Lantmäteriet Laserdata Skog (CC0, FTP) — nodata_fill: "interpolate"

---
*Update this file at the end of every Claude Code session.*
