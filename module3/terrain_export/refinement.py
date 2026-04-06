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
    bl_options = {"REGISTER"}

    # Blender file-browser properties — populated when the user accepts the dialog
    directory:     bpy.props.StringProperty(subtype="DIR_PATH")
    filter_folder: bpy.props.BoolProperty(default=True, options={"HIDDEN"})

    def invoke(self, context, event):
        """Open Blender's file browser so the user can select the order folder."""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        settings = context.scene.terrain_export_settings

        # Store the selected folder so all other operators can find it
        folder = self.directory.rstrip("\\/")
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

        self.report({"INFO"},
            f"Order loaded. Elevation "
            f"{result['elevation_min_m']:.0f}–{result['elevation_max_m']:.0f} m.")
        return {"FINISHED"}


class TERRAIN_OT_BakeResampled(Operator):
    """Run resample.py at full resolution and write resampled.tif — handoff to Step 1"""
    bl_idname  = "terrain.bake_resampled"
    bl_label   = "Create Full Res DEM"
    bl_options = {"REGISTER"}

    def execute(self, context):
        settings = context.scene.terrain_export_settings
        folder, p = preview.check_order(settings, self.report)
        if folder is None:
            return {"CANCELLED"}

        resolution = int(p.get("subdivision_level", 1024))
        result = preview.run_resample(
            folder,
            os.path.join(folder, "resampled.tif"),
            resolution,
            settings.min_clamp, settings.max_clamp, settings.gamma,
            p.get("bbox", {}), self.report,
        )
        if result is None:
            return {"CANCELLED"}

        self.report({"INFO"},
            f"resampled.tif written at {resolution}×{resolution}. Ready for Step 1.")
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


CLASSES = [TERRAIN_OT_LoadOrder, TERRAIN_OT_BakeResampled, TERRAIN_OT_SaveSettings]
