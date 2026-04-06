"""
refinement.py — Module 3 operators: Load Order, Bake Full Res, Save Settings.
Helper functions (resample subprocess, TerrainPreview mesh) live in preview.py.
"""

import os
import json

import bpy
from bpy.types import Operator

from . import preview
from . import bake


# Re-export the slider callback so __init__.py can reference it directly.
on_slider_change = preview.on_slider_change


# ── Operators ─────────────────────────────────────────────────────────────────

class TERRAIN_OT_LoadOrder(Operator):
    """Open a folder browser, then load params.json and create the TerrainPreview"""
    bl_idname  = "terrain.load_order"
    bl_label   = "Load Order"
    # Removing REGISTER prevents Blender from showing the "operator finished" popup after the order loads.
    bl_options = set()

    # Blender file-browser properties — populated when the user accepts the dialog
    directory:     bpy.props.StringProperty(subtype="DIR_PATH")
    filter_folder: bpy.props.BoolProperty(default=True, options={"HIDDEN"})

    # Optional direct-path property for external callers (e.g. the operator tool).
    # When set, the file browser is bypassed entirely.
    folder: bpy.props.StringProperty(default="")

    def invoke(self, context, event):
        # Way 2 — folder was passed directly by an external caller (e.g. operator tool).
        # Skip the file browser and execute immediately.
        if self.folder:
            return self.execute(context)

        # Way 1 — normal interactive use: open Blender's file browser.
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        settings = context.scene.terrain_export_settings

        # Way 2 — use the directly supplied folder path.
        # Way 1 — fall back to the directory chosen in the file browser.
        folder = (self.folder if self.folder else self.directory).rstrip("\\/")
        if not folder:
            self.report({"ERROR"}, "No folder was selected.")
            return {"CANCELLED"}
        settings.order_folder = folder

        _, p = preview.check_order(settings, self.report)
        if p is None:
            return {"CANCELLED"}

        # Remove the default Cube and any other starter objects before doing anything else
        bake.clear_default_objects()

        if not os.path.isfile(os.path.join(folder, "raw_dem.tif")):
            self.report({"ERROR"}, f"raw_dem.tif not found in:\n  {folder}")
            return {"CANCELLED"}

        bbox = p.get("bbox", {})
        if not bbox:
            self.report({"ERROR"}, "params.json has no 'bbox' entry.")
            return {"CANCELLED"}

        # Populate panel sliders from params.json before running resample
        settings.min_clamp          = float(p.get("min_clamp",          0.0))
        settings.max_clamp          = float(p.get("max_clamp",          1.0))
        settings.gamma              = float(p.get("gamma",              1.0))
        settings.displacement_scale = float(p.get("displacement_scale", 0.3))
        settings.elevation_min_m    = float(p.get("elevation_min_m",    0.0))
        settings.elevation_max_m    = float(p.get("elevation_max_m",    0.0))

        preview_tif = os.path.join(folder, "preview.tif")
        result = preview.run_resample(
            folder, preview_tif, 256,
            settings.min_clamp, settings.max_clamp, settings.gamma,
            bbox, self.report,
        )
        if result is None:
            return {"CANCELLED"}

        # Overwrite with values measured from the actual DEM (may differ from stored params)
        settings.elevation_min_m = result["elevation_min_m"]
        settings.elevation_max_m = result["elevation_max_m"]

        preview.create_preview_mesh(preview_tif, settings.displacement_scale)

        # Cancel any pending timer triggered by the property-set calls above
        if bpy.app.timers.is_registered(preview._deferred_preview_update):
            bpy.app.timers.unregister(preview._deferred_preview_update)

        # Schedule a one-shot timer to open the sidebar after Blender has finished
        # processing the current operator. Doing this immediately inside execute()
        # can fail because the UI hasn't fully updated yet; 0.5 s is enough headroom.
        def _open_sidebar():
            try:
                for area in bpy.context.screen.areas:
                    if area.type == "VIEW_3D":
                        for region in area.regions:
                            if region.type == "UI":
                                # Make the N-panel strip visible on the right of the viewport.
                                area.spaces.active.show_region_ui = True
                                # Switch to the Terrain Export tab inside the sidebar.
                                region.active_panel_category = "Terrain Export"
                                break
                        break
            except Exception as e:
                # Never crash Blender over a cosmetic UI action — just log it.
                print(f"TerrainExport: could not open sidebar tab: {e}")
            # Returning None tells the timer system not to reschedule this callback.
            return None

        bpy.app.timers.register(_open_sidebar, first_interval=0.5)

        self.report({"INFO"},
            f"Order loaded. Elevation "
            f"{result['elevation_min_m']:.0f}–{result['elevation_max_m']:.0f} m.")
        return {"FINISHED"}


class TERRAIN_OT_SaveSettings(Operator):
    """Write current panel settings back to params.json"""
    bl_idname  = "terrain.save_settings"
    bl_label   = "Save Settings"
    bl_options = {"REGISTER"}

    def execute(self, context):
        settings = context.scene.terrain_export_settings
        folder, _ = preview.check_order(settings, self.report)
        if folder is None:
            return {"CANCELLED"}

        params_path = os.path.join(folder, "params.json")
        params = {}
        if os.path.isfile(params_path):
            try:
                with open(params_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
            except Exception:
                pass

        params.update({
            "min_clamp":          settings.min_clamp,
            "max_clamp":          settings.max_clamp,
            "gamma":              settings.gamma,
            "displacement_scale": settings.displacement_scale,
            "elevation_min_m":    settings.elevation_min_m,
            "elevation_max_m":    settings.elevation_max_m,
            "print_size_mm":      settings.print_size_mm,
            "base_thickness_mm":  settings.base_thickness_mm,
        })
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)

        self.report({"INFO"}, "Settings saved to params.json.")
        print(f"  Settings saved: {params_path}")
        return {"FINISHED"}


CLASSES = [TERRAIN_OT_LoadOrder, TERRAIN_OT_SaveSettings]
