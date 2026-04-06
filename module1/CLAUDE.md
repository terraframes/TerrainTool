# Module 1 — User-Facing Widget

**STATUS: In progress — Stages 1, 2, 3 complete. Stage 4 (Shopify integration) next.**

## Stage 1 Files (complete)

```
module1\
  widget.html     main page — map containers, overlay div, UI controls
  hillshade.js    second Mapbox instance, camera sync, CSS clip-path
  search.js       dual-source geocoding, autocomplete, explore mode
  selection.js    bbox computation, confirmation flow, payload output
  webhook.py      Flask webhook receiver — BUILT AND DEPLOYED
  test_webhook.py local test script
  requirements.txt
  setup.py
```

## Map — Key Decisions

- Mapbox GL JS v3.3, outdoors-v12, default centre Stockholm [18.0727, 59.321]
- Two stacked instances: bottom basemap, top hillshade-only
- Hillshade clipped via CSS clip-path: inset() — updates every camera move
- Dual-source search: Mapbox + Nominatim in parallel (Promise.allSettled)
- Rotation disabled, browser zoom locked via viewport meta
- Pixel formula: (area_km * 1000) / ((156543.03392 * cos(lat)) / 2^zoom)
- isProgrammaticMove guard for flyTo / explore mode

## webhook.py (Stages 2 & 3 — complete)

**Deployed on Railway. End-to-end tested.**

Behaviour:
- POST /webhook → 200 immediately, processing in background thread
- Extracts: order_number, min_lat, max_lat, min_lon, max_lon, area_km
- Constructs full params.json with all Module 3/4 defaults
- Writes params.json to Google Shared Drive: orders/{order_number}/
- Writes order.txt locally (silently skipped on Railway — harmless)
- Logs Mapbox Static Images URL for order confirmation email
- Never crashes on bad input — always returns 200

**Google Drive Auth — dual mode:**
- MODE A: GDRIVE_KEY_JSON env var (full JSON string) — Railway/cloud
- MODE B: GDRIVE_KEY_PATH env var (file path) — local
- Falls through A → B if JSON parse fails

**⚠ Shared Drive required:**
Service accounts have no storage quota on regular My Drive.
Orders live in a Shared Drive called 'orders'.
All Drive API calls need: supportsAllDrives=True, includeItemsFromAllDrives=True,
driveId, corpora='drive'
Shared Drive ID from GDRIVE_ORDERS_DRIVE_ID env var.

**Railway deployment:**
- Code at github.com/terraframes/TerrainTool
- Credentials and order data excluded via .gitignore
- Procfile: runs webhook.py, binds to 0.0.0.0, port from PORT env var
- Railway env vars: GDRIVE_KEY_JSON, MAPBOX_TOKEN, GDRIVE_ORDERS_DRIVE_ID

## Environment Variables

| Variable | Where | Value |
|----------|-------|-------|
| GDRIVE_KEY_PATH | Local only | E:\TerrainTool\credentials\gdrive_key.json |
| GDRIVE_KEY_JSON | Railway | Full JSON content of service account key |
| MAPBOX_TOKEN | Both | Mapbox public token |
| GDRIVE_ORDERS_DRIVE_ID | Both | Shared Drive ID |

## Stage 4 — To Build

Wire widget into Shopify store:
- Embed widget HTML in Shopify product page
- Bbox fields as line item properties through checkout
- Register Railway webhook URL in Shopify for orders/paid
- Update order confirmation email with Mapbox static thumbnail
- End-to-end test: select → checkout → webhook → params.json on Drive → acquire.py picks up

⚠ Key risk: verify line item properties survive Shopify checkout end-to-end.
Test this before building the Shopify integration.

## Build Stages

| Stage | Status |
|-------|--------|
| 1 — Offline prototype | DONE |
| 2 — Flask webhook (local) | DONE |
| 3 — Railway deployment | DONE |
| 4 — Shopify integration | Next |
| 5 — Hardening | Post-launch |
