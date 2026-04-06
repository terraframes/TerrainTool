"""
terrain_export — Blender 4.x addon
===================================
Converts a processed GeoTIFF into a print-ready STL.

HOW TO INSTALL:
  Run setup.py first — it produces terrain_export.zip in the module4 folder.
  Then in Blender: Edit > Preferences > Add-ons > Install
  Select terrain_export.zip  (NOT the __init__.py directly)
  Enable the addon: search for "Terrain Export"

Usage:
  Press N in the 3D Viewport to open the sidebar.
  Select the "Terrain Export" tab.
  Set the order folder path — settings load automatically from params.json.
  Click the buttons.
"""

import sys
import os
import json

bl_info = {
    "name":        "Terrain Export",
    "author":      "TerrainTool",
    "version":     (2, 0, 0),
    "blender":     (4, 0, 0),
    "location":    "View3D > Sidebar > Terrain Export",
    "description": "Convert a processed GeoTIFF into a print-ready STL",
    "category":    "Import-Export",
}

import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty
from bpy.types import Panel, Operator, PropertyGroup

from . import bake
from . import base_export
from . import refinement
from . import preview


# ── Scene-level property group ────────────────────────────────────────────────

class TerrainExportSettings(PropertyGroup):

    # Internal — set by the Load Order file browser, read by all other operators.
    order_folder: StringProperty(
        name="Order Folder",
        default="",
    )

    # ── Slider-driven params (will control live preview when wired up) ─────────
    # These are read from params.json on folder change and written back by Save Settings.

    displacement_scale: FloatProperty(
        name="Displacement Scale",
        description="Height of terrain relief as a ratio of the plane width.",
        default=1.0, min=0.1, max=5.0, step=10,
        update=refinement.on_slider_change,
    )

    min_clamp: FloatProperty(
        name="Min Clamp",
        description="Elevation values below this normalised level are clipped to 0.",
        default=0.0, min=0.0, max=1.0, step=1,
        update=refinement.on_slider_change,
    )

    max_clamp: FloatProperty(
        name="Max Clamp",
        description="Elevation values above this normalised level are clipped to 1.",
        default=1.0, min=0.0, max=1.0, step=1,
        update=refinement.on_slider_change,
    )

    gamma: FloatProperty(
        name="Gamma",
        description="Gamma correction on elevation. 1.0 = no correction.",
        default=1.0, min=0.5, max=3.0, step=10,
        update=refinement.on_slider_change,
    )

    # Read-only elevation values — set by Load Order, displayed as labels in the panel.
    elevation_min_m: FloatProperty(
        name="Elevation Min (m)",
        description="Lowest elevation found in the raw DEM (metres). Set by Load Order.",
        default=0.0,
    )

    elevation_max_m: FloatProperty(
        name="Elevation Max (m)",
        description="Highest elevation found in the raw DEM (metres). Set by Load Order.",
        default=0.0,
    )

    # ── Export settings ────────────────────────────────────────────────────────

    print_size_mm: IntProperty(
        name="Print Size (mm)",
        description="Width and depth of the printed terrain square in millimetres.",
        default=150, min=50, max=500,
    )

    base_thickness_mm: IntProperty(
        name="Base Thickness (mm)",
        description="Depth of the flat base below the terrain in millimetres.",
        default=10, min=1, max=100,
    )


# ── Operator: Bake & Export ───────────────────────────────────────────────────

class TERRAIN_OT_BakeAndExport(Operator):
    """Resample DEM, bake terrain mesh, add base, and export STL — all in one step"""

    bl_idname  = "terrain.bake_and_export"
    bl_label   = "Bake & Export"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings     = context.scene.terrain_export_settings
        order_folder = bpy.path.abspath(settings.order_folder).rstrip("\\/")
        wm           = context.window_manager

        if not order_folder:
            self.report({"ERROR"}, "No order loaded. Click 'Load Order' first.")
            return {"CANCELLED"}
        if not os.path.isdir(order_folder):
            self.report({"ERROR"}, f"Order folder not found:\n  {order_folder}")
            return {"CANCELLED"}

        params_path = os.path.join(order_folder, "params.json")
        try:
            with open(params_path, "r", encoding="utf-8") as f:
                params = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"Could not read params.json:\n{e}")
            return {"CANCELLED"}

        wm.progress_begin(0, 3)

        # ── Step 1: Resample DEM at full subdivision_level resolution ─────────
        self.report({"INFO"}, "Bake & Export (1/3): resampling DEM...")
        wm.progress_update(0)

        resolution = int(params.get("subdivision_level", 1024))
        bbox       = params.get("bbox", {})
        result = preview.run_resample(
            order_folder,
            os.path.join(order_folder, "resampled.tif"),
            resolution,
            settings.min_clamp, settings.max_clamp, settings.gamma,
            bbox, self.report,
        )
        if result is None:
            wm.progress_end()
            return {"CANCELLED"}

        wm.progress_update(1)

        # ── Step 2: Bake terrain mesh → displaced.obj + simplified.obj ────────
        self.report({"INFO"}, "Bake & Export (2/3): baking terrain mesh...")
        ok = bake.run_bake(order_folder, self.report, context)
        if not ok:
            wm.progress_end()
            return {"CANCELLED"}

        preview_obj = bpy.data.objects.get("TerrainPreview")
        if preview_obj:
            preview_obj.hide_set(True)

        wm.progress_update(2)

        # ── Step 3: Add base and export STL ───────────────────────────────────
        self.report({"INFO"}, "Bake & Export (3/3): adding base and exporting STL...")
        ok = base_export.run_add_base_and_export(
            order_folder, settings.base_thickness_mm, settings.print_size_mm, self.report
        )
        if not ok:
            wm.progress_end()
            return {"CANCELLED"}

        wm.progress_update(3)
        wm.progress_end()

        self.report({"INFO"}, "Bake & Export complete — final.stl written.")
        return {"FINISHED"}


# ── Panel ─────────────────────────────────────────────────────────────────────

class TERRAIN_PT_ExportPanel(Panel):
    """Terrain Export panel in the N-sidebar"""

    bl_label       = "Terrain Export"
    bl_idname      = "TERRAIN_PT_export_panel"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Terrain Export"

    def draw(self, context):
        layout   = self.layout
        settings = context.scene.terrain_export_settings

        # Load Order button, or order name + checkmark once an order is loaded
        if settings.order_folder:
            order_name = os.path.basename(settings.order_folder.rstrip("\\/"))
            layout.label(text=order_name, icon="CHECKMARK")
        else:
            layout.operator("terrain.load_order", icon="FILE_FOLDER")

        # Elevation range and print height labels — only shown once elevation is known
        elev_range = settings.elevation_max_m - settings.elevation_min_m
        has_elev   = elev_range > 0
        if has_elev:
            layout.label(
                text=f"Elevation: {settings.elevation_min_m:.0f}–{settings.elevation_max_m:.0f} m",
                icon="INFO",
            )
            max_h_mm   = settings.displacement_scale * settings.print_size_mm / 10.0
            total_h_mm = max_h_mm + settings.base_thickness_mm
            layout.label(text=f"Print height: {max_h_mm:.1f} mm", icon="BLANK1")
            layout.label(text=f"Print height with base: {total_h_mm:.1f} mm", icon="BLANK1")

        layout.prop(settings, "print_size_mm")
        layout.prop(settings, "base_thickness_mm")

        row = layout.row(align=True)
        row.prop(settings, "min_clamp", slider=True)
        if has_elev:
            row.label(text=f"{settings.min_clamp * elev_range + settings.elevation_min_m:.0f} m")

        row = layout.row(align=True)
        row.prop(settings, "max_clamp", slider=True)
        if has_elev:
            row.label(text=f"{settings.max_clamp * elev_range + settings.elevation_min_m:.0f} m")

        layout.prop(settings, "gamma",              slider=True)
        layout.prop(settings, "displacement_scale", slider=True)

        layout.separator()
        layout.operator("terrain.save_settings",    icon="FILE_TICK")
        layout.operator("terrain.bake_and_export",  icon="RENDER_STILL")


# ── Registration ──────────────────────────────────────────────────────────────

CLASSES = [
    TerrainExportSettings,
    TERRAIN_OT_BakeAndExport,
    *refinement.CLASSES,   # LoadOrder, SaveSettings
    TERRAIN_PT_ExportPanel,
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.terrain_export_settings = bpy.props.PointerProperty(
        type=TerrainExportSettings
    )
    print("Terrain Export addon registered.")


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.terrain_export_settings
    print("Terrain Export addon unregistered.")
