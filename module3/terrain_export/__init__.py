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


# ── Operator: Bake Full Res ───────────────────────────────────────────────────

class TERRAIN_OT_BakeFullRes(Operator):
    """Subdivide a plane, apply displacement from resampled.tif, export OBJ files"""

    bl_idname  = "terrain.bake_full_res"
    bl_label   = "Bake Full Res"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.terrain_export_settings
        order_folder = bpy.path.abspath(settings.order_folder).rstrip("\\/")

        if not order_folder:
            self.report({"ERROR"}, "No order loaded. Click 'Load Order' first.")
            return {"CANCELLED"}
        if not os.path.isdir(order_folder):
            self.report({"ERROR"}, f"Order folder not found:\n  {order_folder}")
            return {"CANCELLED"}

        ok = bake.run_bake(order_folder, self.report, context)
        if ok:
            # Hide the preview mesh now that the full-resolution mesh exists
            preview_obj = bpy.data.objects.get("TerrainPreview")
            if preview_obj:
                preview_obj.hide_set(True)
        return {"FINISHED"} if ok else {"CANCELLED"}


# ── Operator: Add Base and Export ─────────────────────────────────────────────

class TERRAIN_OT_AddBaseAndExport(Operator):
    """Add a flat base to TerrainMesh and export as final.stl"""

    bl_idname  = "terrain.add_base_and_export"
    bl_label   = "Add Base and Export"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.terrain_export_settings
        order_folder = bpy.path.abspath(settings.order_folder).rstrip("\\/")

        if not order_folder:
            self.report({"ERROR"}, "No order loaded. Click 'Load Order' first.")
            return {"CANCELLED"}
        if not os.path.isdir(order_folder):
            self.report({"ERROR"}, f"Order folder not found:\n  {order_folder}")
            return {"CANCELLED"}

        ok = base_export.run_add_base_and_export(
            order_folder, settings.base_thickness_mm, settings.print_size_mm, self.report
        )
        return {"FINISHED"} if ok else {"CANCELLED"}



# ── Panel ─────────────────────────────────────────────────────────────────────

class TERRAIN_PT_ExportPanel(Panel):
    """Terrain Export panel in the N-sidebar"""

    bl_label       = "Terrain Export"
    bl_idname      = "TERRAIN_PT_export_panel"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Terrain Export"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.terrain_export_settings

        # ── Refinement section ─────────────────────────────────────────────
        box = layout.box()
        box.label(text="Refinement", icon="SETTINGS")
        box.operator("terrain.load_order", icon="FILE_FOLDER")

        # Show the active order name once an order has been loaded
        if settings.order_folder:
            order_name = os.path.basename(settings.order_folder.rstrip("\\/"))
            box.label(text=f"Order: {order_name}", icon="CHECKMARK")

        box.separator()

        # Metre equivalents for clamp sliders (only shown once elevation is known)
        elev_range = settings.elevation_max_m - settings.elevation_min_m
        has_elev   = elev_range > 0
        if has_elev:
            box.label(
                text=f"Elev: {settings.elevation_min_m:.0f}–{settings.elevation_max_m:.0f} m",
                icon="INFO",
            )
            # Max printed terrain height = displacement_scale × print_size_mm / 10 mm
            # (displacement is 1 Blender unit per scale unit on a 10-unit plane,
            #  then uniformly scaled to print_size_mm × print_size_mm)
            max_h_mm    = settings.displacement_scale * settings.print_size_mm / 10.0
            total_h_mm  = max_h_mm + settings.base_thickness_mm
            box.label(
                text=f"Print height: {max_h_mm/10:.1f} cm  ({total_h_mm/10:.1f} cm with base)",
                icon="BLANK1",
            )

        row = box.row(align=True)
        row.prop(settings, "min_clamp", slider=True)
        if has_elev:
            row.label(
                text=f"{settings.min_clamp * elev_range + settings.elevation_min_m:.0f} m"
            )

        row = box.row(align=True)
        row.prop(settings, "max_clamp", slider=True)
        if has_elev:
            row.label(
                text=f"{settings.max_clamp * elev_range + settings.elevation_min_m:.0f} m"
            )

        box.prop(settings, "gamma",              slider=True)
        box.prop(settings, "displacement_scale", slider=True)
        box.separator()
        box.operator("terrain.save_settings",  icon="FILE_TICK")
        box.operator("terrain.bake_resampled", icon="RENDER_STILL")

        layout.separator()

        # ── Full Resolution section ────────────────────────────────────────
        fbox = layout.box()
        fbox.label(text="Full Resolution", icon="MESH_GRID")

        col = fbox.column(align=True)
        col.label(text="Print Settings:")
        col.prop(settings, "print_size_mm")
        col.prop(settings, "base_thickness_mm")

        fbox.separator()

        col = fbox.column(align=True)
        col.label(text="Step 1 — Build mesh from GeoTIFF:")
        col.operator("terrain.bake_full_res", icon="MESH_GRID")

        fbox.separator()

        col = fbox.column(align=True)
        col.label(text="Step 2 — Add base and export STL:")
        col.operator("terrain.add_base_and_export", icon="EXPORT")

        fbox.separator()

        terrain_obj = bpy.data.objects.get("TerrainMesh")
        if terrain_obj:
            tri_count = sum(len(p.vertices) - 2 for p in terrain_obj.data.polygons)
            fbox.label(text=f"TerrainMesh: {tri_count:,} triangles", icon="INFO")
        else:
            fbox.label(text="No TerrainMesh in scene yet", icon="QUESTION")


# ── Registration ──────────────────────────────────────────────────────────────

CLASSES = [
    TerrainExportSettings,
    TERRAIN_OT_BakeFullRes,
    TERRAIN_OT_AddBaseAndExport,
    *refinement.CLASSES,   # LoadOrder, BakeResampled, SaveSettings
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
