# Current Work State

## Active Module
**Module 1 — Stage 4 (Shopify integration) + Module 2 Shared Drive fix**

## Status
Operator tool Phases 1–3 complete. Module 1 Stage 4 next.
Module 2 requires Shared Drive fix before Download DEM works end-to-end.

## What Is Built

### Module 4 — COMPLETE
- Blender 4.5 LTS addon: single "Bake & Export" button (runs full pipeline in sequence)
- Panel unified — single layout, two separate print height lines

### Module 3 — COMPLETE
- Extends terrain_export addon, same N-panel tab
- resample.py: two-pass warp, dstNodata=-9999.0, edge fill (load-bearing fixes)
- TERRAIN_OT_LoadOrder: accepts optional folder property for external launch
- Single "Bake & Export" button replaces three separate buttons

### Module 2 — COMPLETE (pending Shared Drive fix)
- GLO-30 via OpenTopography working
- ⚠ acquire.py needs Shared Drive API parameters before Download DEM button works
  Add to all service.files() calls: supportsAllDrives=True, includeItemsFromAllDrives=True,
  driveId=GDRIVE_ORDERS_DRIVE_ID, corpora='drive'

### Module 1 — Stages 1–3 complete, Stage 4 next
- widget.html: green border overlay, disclaimer label, unconditional size-change zoom
- webhook.py deployed on Railway, Shared Drive integration working
- Stage 4: Shopify embed (planning via private admin page for dummy orders first)

### Operator Tool — Phases 1–3 complete
Location: E:\TerrainTool\operator_tool\
Files: main.py, app.py, settings_tab.py, orders_tab.py, console.py, config.py
- Settings tab: all paths + API keys → config.json
- Orders tab: scans local orders, colour-coded status badges, Download DEM + Open in Blender buttons
- Console pane: fixed-height, colour-coded, thread-safe
- Blender launch: subprocess.Popen with --python-expr, calls terrain.load_order directly
- Download DEM: runs acquire.py in background thread (blocked by Module 2 Shared Drive fix)

## What To Build Next

Priority 1: Module 2 Shared Drive fix (unlocks Download DEM button)
Priority 2: Module 1 Stage 4 — Shopify integration (private admin page approach first)

Operator tool remaining:
- Status auto-refresh after Blender closes
- Manual order entry
- Archive tab
- PyInstaller .exe packaging

## Key Decisions Made

- Single "Bake & Export" button in Blender addon (replaces 3 separate buttons)
- Panel unified into single layout (no more two-box split)
- Print height shown as two separate lines (terrain height / with base)
- Green border on selection square (was red)
- Disclaimer label inside square, hidden when too small
- Size-change auto-zoom is unconditional (explore_mode check removed)
- Blender launch: --python-expr passes order folder directly, bypasses file browser
- active_panel_category is read-only in Blender 4.5 — sidebar shown via timer workaround
- REGISTER removed from LoadOrder bl_options (suppresses popup)

---
*Update this file at the end of every Claude Code session.*
