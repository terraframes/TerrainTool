# Module 1 — User-Facing Widget

**STATUS: In progress — Stage 1 complete. Stage 2 ready to build.**

## Area Sizes

Three fixed: **25, 50, 100 km** — worldwide, all GLO-30.
5×5 and 10×10 dropped. EEA-39 detection dropped. print_size_mm = 200 (fixed).

## Stage 1 Files (all built)

```
module1\
  widget.html     main page — map containers, overlay div, UI controls
  hillshade.js    second Mapbox instance, camera sync, CSS clip-path
  search.js       dual-source geocoding, autocomplete, explore mode integration
  selection.js    bbox computation, confirmation flow, payload output
```

## Map Implementation

Two stacked Mapbox GL JS v3.3 instances:
- **Bottom**: outdoors-v12 basemap, default centre Stockholm [18.0727, 59.321]
- **Top**: hillshade-only (bare style-spec, white background, no roads/labels)
  - DEM source: mapbox://mapbox.mapbox-terrain-dem-v1
  - Hillshade paint: black shadows, white highlights, 315° light, 0.9 exaggeration
  - Background #ebe0d5 (warm tone tints highlights)
  - Non-interactive (pointer-events: none)
  - Camera synced to bottom map via jumpTo on every move event
  - Clipped to selection box via **CSS clip-path: inset()** — computed from overlay
    div pixel position, updates on every map move and size button click

Rotation disabled: dragRotate: false, touchPitch: false, touchZoomRotate.disableRotation()
Browser page zoom locked: viewport meta maximum-scale=1.0, user-scalable=no

## Square Overlay

Fixed div, always centred. Red border, transparent fill. Map moves underneath.

**Pixel formula (latitude cosine correction):**
```
pixel_size = (area_km * 1000) / ((156543.03392 * cos(lat)) / 2^zoom)
```
Updates every zoom event. Size change updates immediately.
Geographic bbox computed at confirmation only — not continuously.

## Bbox Computation (confirmation only)

1. Read centre lat/lon from Mapbox viewport centre
2. Haversine offset ±(area_km / 2) in all four directions
3. Non-square lat/lon bbox = true square on the ground
4. Separate from pixel size calculation — do not conflate

## Search (search.js)

Dual-source geocoding queried in parallel (Promise.allSettled):
- **Mapbox**: addresses, cities, POI
- **Nominatim**: natural features, mountains, landmarks

Results merged and deduplicated. Mapbox results first.
Autocomplete: up to 5 suggestions, 300ms debounce.
On result: flyTo, zoom so square covers ~65% of shortest viewport.
After flyTo lands: explore_mode = false.

## Explore Mode

- Starts false
- True on any user pan or zoom
- False after flyTo lands from search
- Auto-zoom on size change only while false
- isProgrammaticMove guard: true before flyTo, cleared in map.once('moveend')

## Confirmation Flow

1. 'Select' → haversine bbox, lock map, disable controls, show summary panel
2. Summary: centre coords, N/S/E/W bbox, area size, dataset
3. 'Confirm' → log payload JSON to console (Stage 2 wires this to Shopify)
4. 'Cancel' → hide panel, re-enable all controls

## Known Deferred

- Mobile hillshade clip desync: rotation disabled as fix — needs thorough mobile retest
- Responsive mobile layout: deferred until widget embedded in Shopify page
- Hillshade visual polish: post-launch

## Stage 2 — To Build (webhook.py)

**Critical: use GDRIVE_KEY_JSON (full JSON string), NOT GDRIVE_KEY_PATH (file path)**
Design this in now — Stage 3 cloud deployment requires it.
For local testing: set GDRIVE_KEY_JSON to contents of E:\TerrainTool\credentials\gdrive_key.json

webhook.py:
1. POST /webhook from Shopify orders/paid
2. Respond 200 immediately
3. Extract: order_number, min_lat, max_lat, min_lon, max_lon, area_km
4. Derive: center_lat = (min_lat + max_lat) / 2, center_lon = (min_lon + max_lon) / 2
5. Construct full params.json (all fields + Module 3/4 defaults):
   dataset='GLO-30', dem_resolution_m=30, print_size_mm=200,
   min_clamp=0.0, max_clamp=1.0, gamma=1.4, displacement_scale=0.3,
   subdivision_level=1024, target_triangles=1000000, base_thickness_mm=10,
   elevation_min_m=0.0, elevation_max_m=0.0
6. Write params.json to Google Drive: /orders/{order_number}/
7. Write order.txt locally: E:\TerrainTool\orders\{order_number}\ (no PII)
8. Construct Mapbox Static Images URL from bbox centre — log it
9. Log all Drive write outcomes
10. Drive write async — never blocks 200

## ⚠ Test Before Building webhook.py

Manually verify Shopify line item properties survive checkout end-to-end.
min_lat, max_lat, min_lon, max_lon, area_km must appear in webhook payload.
Most likely failure point in the whole pipeline.

## Build Stages

| Stage | Status |
|-------|--------|
| 1 — Offline prototype (4 files) | DONE |
| 2 — Flask webhook (local + ngrok) | Next |
| 3 — Deploy to Railway/Render | Not started |
| 4 — Shopify integration + embed | Not started |
| 5 — Hardening | Post-launch |
