# Module 1 — User-Facing Widget

**STATUS: In progress — full pipeline working end-to-end. Stage 4 (real checkout) deferred.**

## What's Working

Full pipeline confirmed: widget Confirm → Railway webhook → params.json on Shared Drive → visible in operator tool. No real Shopify checkout involved.

## Files

```
module1\          (Railway uses this folder — do not rename)
  webhook.py      Flask webhook — deployed on Railway
  test_webhook.py local test script
  requirements.txt  includes flask-cors
  setup.py
  Procfile        tells Railway to run webhook.py

docs\             (GitHub Pages serves from here — at repo root, not inside module1)
  widget.html
  selection.js    POSTs Shopify-shaped payload directly to Railway on Confirm
  hillshade.js
  search.js
```

## Hosting

- **Widget**: GitHub Pages on /docs/ folder → public URL
- **Webhook**: Railway → public URL, binds 0.0.0.0:PORT
- **Embed**: widget iframe in hidden Shopify page (for testing)
- **Repo**: github.com/terraframes/TerrainTool (public)
  config.json removed from Git history via git filter-repo before making public

## Current Pipeline Flow

1. User positions selection, clicks Confirm
2. selection.js POSTs Shopify-shaped payload to Railway webhook URL
3. Order number = TEST-{timestamp} (no real checkout)
4. Railway: constructs params.json, writes to Google Shared Drive
5. params.json appears in operator tool orders tab

## webhook.py Key Details

- POST /webhook → 200 immediately, processing in background thread
- CORS enabled (flask-cors) — required for direct browser POST
- Dual auth: GDRIVE_KEY_JSON (cloud) falls through to GDRIVE_KEY_PATH (local)
- All Drive calls: supportsAllDrives=True, includeItemsFromAllDrives=True,
  driveId=GDRIVE_ORDERS_DRIVE_ID, corpora='drive'
- Never crashes on bad input — always returns 200

## Environment Variables

| Variable | Where | Value |
|----------|-------|-------|
| GDRIVE_KEY_PATH | Local | E:\TerrainTool\credentials\gdrive_key.json |
| GDRIVE_KEY_JSON | Railway | Full JSON content of service account key |
| MAPBOX_TOKEN | Both | Mapbox public token |
| GDRIVE_ORDERS_DRIVE_ID | Both | Shared Drive ID |

## Stage 4 (deferred)

Real Shopify checkout with line item properties.
When building: verify min_lat, max_lat, min_lon, max_lon, area_km survive
the full checkout flow end-to-end before wiring the production webhook.
This is the most likely failure point in the real integration.

## Build Stages

| Stage | Status |
|-------|--------|
| 1 — Offline prototype | DONE |
| 2 — Flask webhook (local) | DONE |
| 3 — Railway deployment | DONE |
| 4 — Real Shopify checkout | Deferred |
| 5 — Hardening | Post-launch |
