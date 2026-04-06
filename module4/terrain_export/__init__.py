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
    "version":     (1, 0, 0),
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


# ── Settings auto-load callback ───────────────────────────────────────────────

def _load_params_on_folder_change(self, context):
    """
    Called automatically when the order_folder property changes.
    Reads params.json and populates all panel settings so they stay in sync
    with the order folder without the user having to click anything.
    """
    folder = bpy.path.abspath(self.order_folder).rstrip("\\/")
    params_path = os.path.join(folder, "params.json")
    if not os.path.isfile(params_path):
        return
    try:
        with open(params_path, "r", encoding="utf-8") as f:
            p = json.load(f)
        self.displacement_scale = float(p.get("displacement_scale", 1.0))
        self.min_clamp          = float(p.get("min_clamp", 0.0))
        self.max_clamp          = float(p.get("max_clamp", 1.0))
        self.gamma              = float(p.get("gamma", 1.0))
        self.print_size_mm      = int(p.get("print_size_mm", 150))
        self.base_thickness_mm  = int(p.get("base_thickness_mm", 10))
        print(f"  Settings loaded from params.json: {params_path}")
    except Exception as e:
        print(f"  Could not load params.json: {e}")


# ── Scene-level property group ────────────────────────────────────────────────

class TerrainExportSettings(PropertyGroup):

    order_folder: StringProperty(
        name="Order Folder",
        description=(
            "Full path to the order folder containing params.json and resampled.tif.\n"
            "Example: E:\\TerrainTool\\orders\\TEST001"
        ),
        default="",
        subtype="DIR_PATH",
        update=_load_params_on_folder_change,
    )

    # ── Slider-driven params (will control live preview when wired up) ─────────
    # These are read from params.json on folder change and written back by Save Settings.

    displacement_scale: FloatProperty(
        name="Displacement Scale",
        description="Height of terrain relief. 1.0 = 10% of print width.",
        default=1.0, min=0.1, max=5.0, step=10,
    )

    min_clamp: FloatProperty(
        name="Min Clamp",
        description="Elevation values below this are clipped to 0.",
        default=0.0, min=0.0, max=1.0, step=1,
    )

    max_clamp: FloatProperty(
        name="Max Clamp",
        description="Elevation values above this are clipped to 1.",
        default=1.0, min=0.0, max=1.0, step=1,
    )

    gamma: FloatProperty(
        name="Gamma",
        description="Gamma correction on elevation. 1.0 = no correction.",
        default=1.0, min=0.1, max=5.0, step=10,
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
            self.report({"ERROR"}, "Order Folder is empty. Set it in the Terrain Export panel.")
            return {"CANCELLED"}
        if not os.path.isdir(order_folder):
            self.report({"ERROR"}, f"Order folder not found:\n  {order_folder}")
            return {"CANCELLED"}

        ok = bake.run_bake(order_folder, self.report, context)
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
            self.report({"ERROR"}, "Order Folder is empty. Set it in the Terrain Export panel.")
            return {"CANCELLED"}
        if not os.path.isdir(order_folder):
            self.report({"ERROR"}, f"Order folder not found:\n  {order_folder}")
            return {"CANCELLED"}

        ok = base_export.run_add_base_and_export(
            order_folder, settings.base_thickness_mm, settings.print_size_mm, self.report
        )
        return {"FINISHED"} if ok else {"CANCELLED"}


# ── Operator: Save Settings ───────────────────────────────────────────────────

class TERRAIN_OT_SaveSettings(Operator):
    """Write current panel settings back to params.json"""

    bl_idname  = "terrain.save_settings"
    bl_label   = "Save Settings"
    bl_options = {"REGISTER"}

    def execute(self, context):
        settings = context.scene.terrain_export_settings
        order_folder = bpy.path.abspath(settings.order_folder).rstrip("\\/")

        if not order_folder:
            self.report({"ERROR"}, "Order Folder is empty.")
            return {"CANCELLED"}
        if not os.path.isdir(order_folder):
            self.report({"ERROR"}, f"Order folder not found:\n  {order_folder}")
            return {"CANCELLED"}

        params_path = os.path.join(order_folder, "params.json")
        params = {}
        if os.path.isfile(params_path):
            try:
                with open(params_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
            except Exception:
                pass

        params["displacement_scale"] = settings.displacement_scale
        params["min_clamp"]          = settings.min_clamp
        params["max_clamp"]          = settings.max_clamp
        params["gamma"]              = settings.gamma
        params["print_size_mm"]      = settings.print_size_mm
        params["base_thickness_mm"]  = settings.base_thickness_mm

        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)

        self.report({"INFO"}, "Settings saved to params.json.")
        print(f"  Settings saved: {params_path}")
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
        layout = self.layout
        settings = context.scene.terrain_export_settings

        layout.label(text="Order Folder:")
        layout.prop(settings, "order_folder", text="")

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Print Settings:")
        col.prop(settings, "print_size_mm")
        col.prop(settings, "base_thickness_mm")

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Step 1 — Build mesh from GeoTIFF:")
        col.operator("terrain.bake_full_res", icon="MESH_GRID")

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Step 2 — Add base and export STL:")
        col.operator("terrain.add_base_and_export", icon="EXPORT")

        layout.separator()

        terrain_obj = bpy.data.objects.get("TerrainMesh")
        if terrain_obj:
            tri_count = sum(len(p.vertices) - 2 for p in terrain_obj.data.polygons)
            layout.label(text=f"TerrainMesh: {tri_count:,} triangles", icon="INFO")
        else:
            layout.label(text="No TerrainMesh in scene yet", icon="QUESTION")


# ── Registration ──────────────────────────────────────────────────────────────

CLASSES = [
    TerrainExportSettings,
    TERRAIN_OT_BakeFullRes,
    TERRAIN_OT_AddBaseAndExport,
    TERRAIN_OT_SaveSettings,
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
