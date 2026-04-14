# TerrainTool — Root CLAUDE.md

## Project

E2E pipeline: customer map selection → 3D-printable terrain STL.
Windows 11. Python 3.11. Blender 4.5 LTS. GDAL via QGIS only.

## Critical Rules (never break these)

- **GDAL via subprocess only** — `C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat`
  Never `import osgeo` anywhere. Not in bpy, not in any module script.
- **Google Shared Drive** — all Drive calls need:
  `supportsAllDrives=True, includeItemsFromAllDrives=True, driveId, corpora='drive'`
- **params.json is single source of truth** — all modules read from and write to it
- **Drive holds params.json only** — all other files stay local at `E:\TerrainTool\orders\{order_number}\`
- **Blender 4.5 LTS only** — not 5.x (breaking API changes)
- **Files < 300 lines**
- **Mapbox GL JS uses 512px tiles** → constant `78271.516` m/px, NOT `156543.03392`

## Module Status

| Module | Status |
|--------|--------|
| Module 4 — Blender displacement & export | COMPLETE |
| Module 3 — Refinement addon | COMPLETE |
| Module 2 — GLO-30 acquisition | COMPLETE |
| Module 2b — Extended datasets (Faroe Islands) | COMPLETE |
| Module 1 — Widget + webhook | In progress |
| Operator Tool | In progress |

## File Locations

```
E:\TerrainTool\
  orders\{order_number}\     local order files
  datasets\                  local_datasets.json, coverage GeoJSONs, source DEMs
  module1\                   Flask webhook (Railway)
  module2\                   GLO-30 acquisition
  module2b\                  Extended dataset acquisition
  module3\terrain_export\    Blender addon (shared with module4)
  module4\terrain_export\    Blender addon
  operator_tool\             CustomTkinter desktop app
  credentials\               gdrive_key.json — NEVER COMMIT
```

GitHub Pages: `/docs/` folder at repo root — widget files served from here.
Railway: `/module1/` — Flask webhook.

## Blender Invocation Modes (NEVER CONFLATE)

1. **With UI** — mandatory manual refinement (Module 3). Operator reviews, adjusts, saves.
2. **Headless** (`--background`) — automated Bake & Export (Module 4). Not yet wired from operator tool.

## Key Technical Decisions

### Mapbox Tile Constant
Mapbox GL JS uses 512×512 pixel tiles.
Pixel formula: `pixel_size = (area_km * 1000) / ((78271.516 * cos(lat)) / 2^zoom)`
The old value 156543.03392 is for 256px tiles (legacy Google Maps) — produces half-size boxes.

### nodata Handling
- Always use exact float: `3.3999999521443642e+38` (NOT `3.4e+38`) for Faroe Islands
- Use `repr(nodata_value)` in subprocess string interpolation
- `nodata_fill: "zero"` for coastal/island DEMs — ocean = sea level, not interpolated
- `nodata_fill: "interpolate"` for land DEMs with scan gaps
- resample.py guard: if band nodata == 0.0, skip gdal.FillNodata entirely

### processing_status in params.json
- `"ready"` or absent: Module 3 proceeds normally
- `"pending_lidar_review"`: Module 3 blocks load
- `"needs_manual_processing"`: Module 3 blocks load

### Continuous Area Slider (planned, Module 1)
- Library: noUiSlider
- `const HIGH_RES_THRESHOLD_KM = 25` — named constant
- `SNAP_LIST` array defines all available sizes — 25 must always be present
- Track left of 25km: grey/blocked unless inside coverage polygon
- slider.updateOptions() on every map move
- update event: no auto-zoom; change event: auto-zoom

## Future High-Res Dataset Architecture

### Coverage Polygons
- Derived from tile index (not country boundary)
- Manually editable GeoJSON files bundled with widget
- Widget uses Turf.js union of all polygons to determine available sizes

### Cross-Border Orders
- If bbox spans two high-res datasets: set processing_status = "needs_manual_processing"
- NEVER fall back to GLO-30 silently on a paid high-res order

### Routing (future)
Priority-ordered selector, not if/else chains:
1. High-res datasets (LiDAR etc.) if bbox inside coverage
2. GLO-30 fallback
