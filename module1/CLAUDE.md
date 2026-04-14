# Module 1 — User-Facing Widget

**STATUS: In progress — Stages 1–3 complete. Slider built and live.**

## What's Working

Full pipeline: widget Confirm → Railway webhook → params.json on Shared Drive → operator tool.
Continuous area slider live. Coverage polygon system live.

## ⚠ Critical: Mapbox Tile Constant

Mapbox GL JS uses **512×512 pixel tiles**.
Formula: `pixel_size = (area_km * 1000) / ((78271.516 * cos(lat)) / 2^zoom)`
The legacy constant 156543.03392 (256px Google Maps) produces a half-size box. Fixed.

## Widget Files (/docs/ folder at repo root)

```
widget.html                     map, overlay, UI, noUiSlider 15.7.1 CDN, Turf.js CDN
hillshade.js                    second Mapbox instance, camera sync, clip-path
                                  window._triggerClipUpdate exposed
search.js                       dual-source geocoding, explore mode
selection.js                    bbox, confirmation, reads dataset from coverage.js
                                  .size-btn refs removed from lockMap/unlockMap
coverage.js                     SNAP_LIST, slider, coverage check, red state logic
faroe_islands_coverage.geojson  Faroe Islands coverage polygon, EPSG:4326
```

## Area Slider (coverage.js)

### SNAP_LIST & Threshold
```javascript
const HIGH_RES_THRESHOLD_KM = 25;  // ALWAYS a named constant
const SNAP_LIST = [
  2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
  3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.5,
  5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 20,
  25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90,
  100, 110, 120, 130, 140, 150, 175, 200
];
// Boot-time assertion: 25 MUST be in SNAP_LIST — throws if missing
// State stored as km value, never index
```

### Two-Segment Track Mapping
Left 25% of track → 2–25 km. Right 75% → 25–200 km.
Functions: `snapIndexToTrackPct()` and `trackPctToSnapIndex()`
Keeps 25km boundary at the 25% visual position regardless of snap list density.

### noUiSlider Config
noUiSlider 15.7.1. Single handle, `connect: [false, true]`. Default: 25km.
Track height 20px, handle 35px. `LEFT_SEGMENT_END_PCT = 25`.

### Three-Segment Visual
Two overlay divs (`seg-locked`, `seg-available`) behind the track.
`updateSegmentColours()` repositions based on `_insideCoverage` + handle position.

### Three Coverage States

| State | Track | Overlay | Select |
|-------|-------|---------|--------|
| Outside coverage (GLO-30 only) | Left 25% grey, min hard-locked to 25km | None | Enabled |
| Inside coverage | Full range to 2km, grey lifts | None | Enabled |
| Red state (panned outside while < 25km) | Grey re-engages, handle stays | Red border+fill+message | Disabled |

Red state message: "High-res data not available here — select 25 km or larger"
No force-snap on drag release. Hard lock re-engages at 25km if dragged there.

### Events
- `update` (continuous drag): overlay resize, clip-path, coverage check, hard lock. **No auto-zoom.**
- `change` (drag end only): snap to nearest SNAP_LIST entry, trigger auto-zoom
- map move: coverage check → `updateSegmentColours()` → red state if needed

## Coverage System

`_runCoverageCheck()` → Turf.js point-in-polygon → `_insideCoverage`
→ `_applyInvalidState()` or `_applyClearState()`

Inside Faroe Islands AND area_km <= 25: `window._currentDataset = "FO-DEM"`
Otherwise: `window._currentDataset = "GLO-30"`
Read by selection.js via `window.getDatasetForCurrentSelection()`

## Webhook (Stages 2 & 3 — complete)

POST /webhook → 200 immediately. Extracts 6 line item properties.
dataset defaults to "GLO-30" if absent.
Railway: github.com/terraframes/TerrainTool

## Remaining / Deferred
- Coverage info overlay (Section 8.3)
- Stage 4: real Shopify checkout
- Stage 5: mobile layout, hillshade polish
