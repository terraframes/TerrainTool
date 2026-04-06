# Current Work State

## Active Module
**Module 1 — Stage 3 (cloud deployment to Railway/Render)**

## Status
Stage 1 complete (4 files). Stage 2 complete (4 files).

## What Is Built

### Module 4 — COMPLETE
- Blender 4.5 LTS addon: Bake Full Res + Add Base and Export
- Outputs: displaced.obj, simplified.obj, final.stl

### Module 3 — COMPLETE
- Extends terrain_export addon, same N-panel tab
- resample.py: two-pass warp, dstNodata=-9999.0, edge fill (load-bearing)

### Module 2 — COMPLETE
- GLO-30 via OpenTopography. GLO-10 disabled (Public Authority account required).
- Drive: params.json only. Local: E:\TerrainTool\orders\{order_number}\

### Module 1 — Stage 2 complete
Stage 1 files: widget.html, hillshade.js, search.js, selection.js
Stage 2 files: webhook.py, test_webhook.py, requirements.txt, setup.py

Stage 1 key details:
- Two stacked Mapbox instances: bottom basemap, top hillshade-only
- Hillshade clipped via CSS clip-path: inset() (not Mapbox layer masking)
- Dual-source search: Mapbox + Nominatim in parallel (Promise.allSettled)
- Rotation disabled (fixes hillshade clip desync on mobile)
- isProgrammaticMove guard working
- Confirmation: Select → summary panel → Confirm (logs JSON) / Cancel

Stage 2 key details:
- POST /webhook responds 200 immediately; Drive write is async (threading)
- Drive auth: GDRIVE_KEY_JSON (cloud) takes priority over GDRIVE_KEY_PATH (local)
- Writes params.json to Drive orders/{order_number}/; overwrites if exists
- Writes order.txt locally to E:\TerrainTool\orders\{order_number}\
- Logs Mapbox Static Images URL for order confirmation email
- test_webhook.py sends fake Shopify payload to localhost:5000 for local testing

## What To Build Next — Stage 3

Deploy webhook.py to Railway or Render.
Before deploying:
- Test on mobile now rotation is disabled — confirm hillshade clip tracks correctly
- Test natural landmark search (Everest, Mont Blanc) — confirm Nominatim results appear
- Manually verify Shopify line item properties survive checkout end-to-end
- Run test_webhook.py against local webhook.py to confirm full local flow

## Decisions Made

- Stage 1 split into 4 files (not single HTML)
- Hillshade: two stacked map instances + CSS clip-path (Mapbox clip layer doesn't support hillshade in v3.3)
- Dual-source search: Mapbox + Nominatim (for mountains/natural features)
- Rotation disabled: dragRotate, touchPitch, touchZoomRotate.disableRotation
- Browser zoom locked via viewport meta
- GDRIVE_KEY_JSON for credential handling (not file path)

---
*Update this file at the end of every Claude Code session.*

## Future Architecture Notes (not blocking current work)

### High-Res Dataset Expansion
- Coverage polygons derived from tile index (not country boundary) — handles partial coverage + water tiles correctly
- Widget uses Turf.js union of all coverage polygons to determine available sizes
- Cross-border orders (bbox spans two datasets): flag as needs_manual_processing, operator handles manually
- DO NOT fall back to GLO-30 silently on a paid high-res order
- processing_status field to be added to params.json when LiDAR is implemented
- Dataset routing to be refactored from if/else to priority-ordered selector when second high-res source is added
- Swedish LiDAR: CC0 license confirmed for commercial use. Markhöjdmodell license TBC (likely DTM anyway).
