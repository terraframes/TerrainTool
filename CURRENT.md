# Current Work State

## Active Module
No active build — all implemented items working.
Next: Coverage info overlay (Section 8.3), or operator tool improvements.

## What Is Built

### Module 4 — COMPLETE
### Module 3 — COMPLETE (processing_status guard, nodata 0.0 guard)
### Module 2 — COMPLETE (GLO-30, Shared Drive, --sync-only, --order)
### Module 2b — COMPLETE (Faroe Islands, real order end-to-end confirmed)
### Module 1 — Stages 1–3 complete + slider built
  - Tile constant fixed: 78271.516 (512px tiles)
  - Continuous area slider: noUiSlider 15.7.1, SNAP_LIST, two-segment mapping
  - Three coverage states: GLO-30 only / inside coverage / red state
  - coverage.js fully rewritten, hillshade.js and selection.js updated
### Operator Tool — Full end-to-end working

## Remaining Work

### Widget
1. Coverage info overlay (Section 8.3)
2. Stage 4: real Shopify checkout

### Operator Tool
1. Status auto-refresh after Blender closes
2. Manual order entry
3. Archive tab
4. PyInstaller .exe
5. Headless Blender export (--background)
6. Dataset column width (80 → 110px, cosmetic)

### Future Datasets
- Lantmäteriet Laserdata Skog (CC0, FTP)

## Key Decisions Made

- Two-segment track: LEFT_SEGMENT_END_PCT = 25 (left 25% = 2–25km, right 75% = 25–200km)
- snapIndexToTrackPct() / trackPctToSnapIndex() handle the mapping
- Hard lock: handle cannot enter left segment when outside coverage
- Red state: fires when panning outside coverage while handle < 25km
- No force-snap on drag release in red state — user acts when ready
- Hard lock re-engages at 25km if user drags toward it from red state
- update event: no auto-zoom; change event (drag end): snap + auto-zoom
- window._triggerClipUpdate exposed from hillshade.js
- window._currentAreaKm used by widget.html (removed local area_km variable)
- initCoverage(map, []) — empty array passed from widget.html

---
*Update this file at the end of every Claude Code session.*
