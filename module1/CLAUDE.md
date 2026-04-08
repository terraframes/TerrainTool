# Module 1 — User-Facing Widget

**STATUS: In progress — Stages 1–3 and Widget Phases 1–3 complete.**

## What's Working

Full pipeline: widget Confirm → Railway webhook → params.json on Shared Drive → operator tool.
Coverage polygon system live: map centre determines dataset (FO-DEM vs GLO-30).
Unavailable state UX: red overlay + disabled Select when high-res size selected outside coverage.

## Widget Files (/docs/ folder at repo root)

```
widget.html                     map, overlay, UI, Turf.js CDN
hillshade.js                    second Mapbox instance, camera sync, CSS clip-path
search.js                       dual-source geocoding, explore mode
selection.js                    bbox, confirmation flow, reads dataset from coverage.js
coverage.js                     loads GeoJSONs, sets window._currentDataset per map move
faroe_islands_coverage.geojson  Faroe Islands coverage polygon, EPSG:4326
```

## Area Sizes

Five sizes: **5, 10, 25, 50, 100 km**
- 5 and 10 km: greyed out by default, enabled only when inside a coverage polygon
- 25, 50, 100 km: always available (GLO-30)

## Coverage System (coverage.js)

On every map move and size button click:
- Check map centre point against all loaded coverage polygons
- If inside Faroe Islands polygon AND area_km <= 25: window._currentDataset = "FO-DEM"
- Otherwise: window._currentDataset = "GLO-30"

selection.js reads dataset via window.getDatasetForCurrentSelection() and:
- Includes dataset in Shopify line item properties
- Shows dataset in confirmation summary panel

## Unavailable State UX

When high-res size is active and map centre moves outside coverage:
- Border turns red
- Semi-transparent red fill
- Message "Chosen resolution not available in this region" below square
- Select button disabled

When back inside coverage or switched to non-high-res size: all above clears.

## Webhook (Stages 2 & 3 — complete)

- POST /webhook → 200 immediately, background thread
- Extracts: order_number, min_lat, max_lat, min_lon, max_lon, area_km, dataset
- Constructs full params.json (includes dataset field for Module 2b routing)
- Dual auth: GDRIVE_KEY_JSON (cloud) → GDRIVE_KEY_PATH (local)
- CORS enabled via flask-cors
- Railway deployed: github.com/terraframes/TerrainTool

## Environment Variables

| Variable | Where | Value |
|----------|-------|-------|
| GDRIVE_KEY_PATH | Local | E:\TerrainTool\credentials\gdrive_key.json |
| GDRIVE_KEY_JSON | Railway | Full JSON content |
| MAPBOX_TOKEN | Both | Mapbox public token |
| GDRIVE_ORDERS_DRIVE_ID | Both | Shared Drive ID |

## Remaining / Deferred

- Coverage info overlay (Section 8.3) — explains datasets, triggered from greyed button tooltip
- Stage 4: real Shopify checkout — verify 6 line item properties survive
- Dataset column width in operator tool (80 → 110px) — cosmetic
- Stage 5 hardening: Drive write recovery, mobile layout, hillshade polish
