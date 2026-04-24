# Module 1 — User-Facing Widget

**STATUS: In progress — Stages 1–3 complete. Slider + coverage system + ArcticDEM live.**

## Widget Files (/docs/ folder at repo root)

```
widget.html                     map, overlay, UI, noUiSlider CDN, Turf.js CDN
hillshade.js                    second Mapbox instance, clip-path, window._triggerClipUpdate
search.js                       dual-source geocoding
selection.js                    bbox, confirmation, reads dataset from coverage.js
coverage.js                     SNAP_LIST, slider, bbox containment, priority loop, State A+B
coverage_modal.js               coverage info modal
coverage_info.json              region list: emoji, region, status, source[]
faroe_islands_coverage.geojson  Faroes polygon, EPSG:4326, ~8km offshore margin
arcticdem_coverage.geojson      ArcticDEM polygon, EPSG:4326, FeatureCollection of Polygons
```

## ⚠ Mapbox Tile Constant

512px tiles: `pixel_size = (area_km * 1000) / ((78271.516 * cos(lat)) / 2^zoom)`

## Coverage System

**Full bbox containment:** `turf.booleanContains(coveragePolygon, bboxPolygon)`.
Bbox computed live in coverage.js on every map move + slider change (haversine).

**DATASETS config** (position = priority, first match wins):
```javascript
var DATASETS = [
  { key: 'ArcticDEM', geojson: 'arcticdem_coverage.geojson' },
  { key: 'FO-DEM',    geojson: 'faroe_islands_coverage.geojson' }
  // GLO-30 = fallback, no polygon needed
];
```

**_coverageReady flag** — essential. Gates all `_runCoverageCheck` entry points until
Promise.all fetches complete. Without it: slider init triggers checks on empty arrays → feedback loop.

**Coverage GeoJSON rules:**
- Must be FeatureCollection of Polygon features — NOT MultiPolygon (turf.booleanContains throws)
- Must be simplified before deployment — complex polygons on every frame = unusable map
- Dissolve in EPSG:4326, NOT in polar/projected CRS (antimeridian wrapping artefacts)

**State A** — panned out while sub-25km selected: red border + fill, disabled Select, message.
**State B** — tried to drag below 25km outside coverage: handle shakes, "Not available for this region" tooltip 2.5s.
**Coverage Modal** — ? button, dark modal, coverage_info.json rows, mobile-safe.

## Slider

```javascript
const HIGH_RES_THRESHOLD_KM = 25;  // named constant
// Left 25% track → 2–25km. Right 75% → 25–200km.
// 25 MUST always be in SNAP_LIST — boot-time assertion
```
`update` event: no auto-zoom. `change` event: snap + auto-zoom.

## Webhook (complete)

6 line item properties: min_lat, max_lat, min_lon, max_lon, area_km, dataset.
Railway: github.com/terraframes/TerrainTool

## Remaining

- Stage 4: real Shopify checkout
- Stage 5: mobile layout, hardening
