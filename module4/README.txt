Module 4 — Displacement & Export
==================================================

STATUS: Setup complete
Python: 3.11.0
Blender: Found at C:\Program Files\Blender Foundation\Blender 4.5\blender.exe
Dependencies: none (addon uses only Blender's bundled Python)

HOW TO USE
--------------------------------------------------

Step 1 — Install the Blender addon:
   Open Blender > Edit > Preferences > Add-ons > Install
   Select:  module4\terrain_export.zip   (created by this setup.py)
   IMPORTANT: select the .zip, NOT the __init__.py file directly.
   Installing the zip keeps bake.py and base_export.py together as a package.
   Enable the addon: search for 'Terrain Export'

Step 2 — Run the export pipeline:
   In Blender, press N to open the sidebar
   Find the 'Terrain Export' tab
   Set the Order Folder to the full path of your order folder
   e.g.  E:\TerrainTool\orders\TEST001
   The folder must contain:  resampled.tif  and  params.json
   Click 'Bake Full Res'       — generates displaced.obj and simplified.obj
   Click 'Add Base and Export' — generates final.stl

OUTPUT FILES (written to the order folder):
   displaced.obj   — full resolution mesh
   simplified.obj  — decimated to ~1M triangles
   final.stl       — watertight, flat base added, print-ready

TROUBLESHOOTING
--------------------------------------------------
- If the addon fails to load: check Blender's Python console for errors
- If displacement looks wrong: confirm resampled.tif is float32 with values in [0, 1]
- If params.json is missing: create it in the order folder (see CLAUDE.md for schema)
