"""
bake.py — terrain bake pipeline.

Public API
----------
bake_terrain(resolution, context, target_name)
    Core pipeline used by both full bake and preview.
    Reads displacement_scale from the panel property group (not params.json).

bake_preview(context)
    256×256 lightweight bake → TerrainPreview object.
    Replaces TerrainPreview on every call; used by sliders for live feedback.

run_bake(order_folder, report, context)
    Full-resolution bake → TerrainMesh, then export displaced.obj / simplified.obj.
"""

import bpy
import bmesh
import os
import json
import math


# ── Params ────────────────────────────────────────────────────────────────────

def load_params(order_folder):
    """Read params.json from the given folder. Returns a dict or raises."""
    path = os.path.join(order_folder, "params.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"params.json not found at:\n  {path}\n"
            "Create a params.json file in the order folder."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Scene helpers ─────────────────────────────────────────────────────────────

def clear_default_objects():
    """Remove Blender's default cube if present — it serves no purpose here."""
    obj = bpy.data.objects.get("Cube")
    if obj and obj.type == "MESH":
        bpy.data.objects.remove(obj, do_unlink=True)
        print("  Removed default Cube.")


def clear_object_by_name(name):
    """Remove any object with this name from the scene."""
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
        print(f"  Removed existing {name}.")


# ── Mesh construction ─────────────────────────────────────────────────────────

def create_subdivided_plane(subdivision_level, target_name="TerrainMesh"):
    """
    Create a 10×10 Blender-unit plane, subdivide it to subdivision_level
    vertices per edge, build a clean UV map, and return the object.

    10 units is viewport-convenient. Export scales to mm independently.
    """
    bpy.ops.mesh.primitive_plane_add(size=10.0, enter_editmode=False, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = target_name

    # Each subdivide doubles vertices per edge; log2 gives the number of cuts.
    cuts = int(math.log2(subdivision_level))
    bpy.ops.object.mode_set(mode="EDIT")
    for _ in range(cuts):
        bpy.ops.mesh.subdivide(number_cuts=1, smoothness=0)
    bpy.ops.object.mode_set(mode="OBJECT")

    print(f"  {target_name}: {cuts} subdivisions → {subdivision_level}×{subdivision_level} vertices.")
    reset_uvs(obj)
    return obj


def reset_uvs(obj):
    """
    Build a single UV layer that maps the full mesh as one 0→1 square.

    bpy.ops.uv.reset() gives each face its own 0→1 square (wrong — every quad
    would sample the whole texture). Instead we derive each loop's UV from its
    vertex XY position relative to the mesh bounding box.
    """
    while obj.data.uv_layers:
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
    uv_layer = obj.data.uv_layers.new(name="UVMap")

    verts = obj.data.vertices
    xs = [v.co.x for v in verts]
    ys = [v.co.y for v in verts]
    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)
    min_x, min_y = min(xs), min(ys)

    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            v = verts[obj.data.loops[li].vertex_index]
            uv_layer.data[li].uv = (
                (v.co.x - min_x) / x_range,
                (v.co.y - min_y) / y_range,
            )
    print(f"  UV map reset: {len(verts)} vertices → clean [0, 1] grid.")


# ── Displacement ──────────────────────────────────────────────────────────────

def load_tif_as_blender_image(tif_path, img_name="TerrainDisplaceTex"):
    """
    Load a float32 GeoTIFF via Blender's OIIO backend.
    Non-Color colorspace keeps raw 0-1 elevation values intact.
    """
    existing = bpy.data.images.get(img_name)
    if existing:
        bpy.data.images.remove(existing)

    img = bpy.data.images.load(tif_path)
    img.name = img_name
    img.colorspace_settings.name = "Non-Color"
    print(f"  TIF loaded: {img.size[0]}×{img.size[1]} px  ({img_name})")
    return img


def apply_displacement(obj, blender_img, displacement_strength, tex_name="TerrainDisplaceTex"):
    """
    Attach a Displace modifier using blender_img, then apply it to real geometry.

    Key settings that must not change:
      extension = EXTEND   — prevents texture wrapping at UV edges
      use_interpolation    — smooth pixel blending, no blocky artefacts
      mid_level = 0.0      — terrain displaces upward from Z=0 only
    """
    tex = bpy.data.textures.get(tex_name)
    if tex is None:
        tex = bpy.data.textures.new(name=tex_name, type="IMAGE")
    tex.image = blender_img
    tex.extension = "EXTEND"
    tex.use_interpolation = True

    mod = obj.modifiers.new(name="TerrainDisplace", type="DISPLACE")
    mod.texture = tex
    mod.strength = displacement_strength
    mod.texture_coords = "UV"
    mod.mid_level = 0.0
    print(f"  Displace modifier: strength={displacement_strength:.4f}")

    bpy.context.view_layer.objects.active = obj
    for modifier in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    print("  Modifiers applied — displacement baked to geometry.")


def snap_perimeter_z_to_interior(obj):
    """
    Replace each boundary vertex's Z with the average Z of its interior
    edge-neighbours. Guards against texture-sampler edge artefacts.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    boundary_verts = {v for e in bm.edges if e.is_boundary for v in e.verts}
    snapped = 0
    for v in boundary_verts:
        interior = [e.other_vert(v) for e in v.link_edges
                    if e.other_vert(v) not in boundary_verts]
        if interior:
            v.co.z = sum(n.co.z for n in interior) / len(interior)
            snapped += 1

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    print(f"  Perimeter Z snap: {snapped} vertices snapped.")


# ── OBJ export / decimation ───────────────────────────────────────────────────

def export_obj(obj, filepath):
    """Export the given object as a Wavefront OBJ file."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        export_uv=False,
        export_normals=True,
        export_materials=False,
    )
    print(f"  Exported: {filepath}")


def decimate_mesh(obj, target_triangles):
    """Reduce the mesh to approximately target_triangles triangles."""
    current_tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if current_tris == 0:
        raise RuntimeError("Mesh has no polygons — cannot decimate.")
    ratio = min(1.0, target_triangles / current_tris)
    print(f"  Decimating: {current_tris} → ~{target_triangles} triangles (ratio={ratio:.4f})")
    mod = obj.modifiers.new(name="TerrainDecimate", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    final = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"  After decimation: {final} triangles.")


# ── Core shared pipeline ──────────────────────────────────────────────────────

def bake_terrain(resolution, context, target_name="TerrainMesh"):
    """
    Shared displacement pipeline used by both full bake and preview.

      resolution  — subdivision level: 256 (preview) or 1024/2048 (full)
      context     — bpy.context; displacement_scale is read from
                    context.scene.terrain_export_settings, NOT from params.json
      target_name — name of the Blender object to create/replace

    Returns the created object. Raises RuntimeError on failure.
    """
    settings = context.scene.terrain_export_settings
    order_folder = bpy.path.abspath(settings.order_folder).rstrip("\\/")
    displacement_scale    = settings.displacement_scale
    displacement_strength = displacement_scale * 1.0   # 10% of 10-unit plane

    tif_path = os.path.join(order_folder, "resampled.tif")
    if not os.path.isfile(tif_path):
        raise RuntimeError(f"resampled.tif not found in:\n  {tif_path}")

    tex_name = f"{target_name}Tex"   # keep full/preview textures separate in Blender data

    print(f"  Target: {target_name}  resolution: {resolution}×{resolution}")
    print(f"  displacement_scale: {displacement_scale}  → strength: {displacement_strength:.4f}")

    clear_object_by_name(target_name)
    obj = create_subdivided_plane(resolution, target_name)

    try:
        img = load_tif_as_blender_image(tif_path, img_name=tex_name)
    except Exception as e:
        raise RuntimeError(f"Failed to load resampled.tif:\n{e}")

    apply_displacement(obj, img, displacement_strength, tex_name=tex_name)
    snap_perimeter_z_to_interior(obj)
    return obj


def bake_preview(context):
    """
    Lightweight 256×256 bake targeting TerrainPreview.
    Replaces TerrainPreview on every call — does not accumulate.
    Called by sliders for live feedback; also works when called manually.
    Does NOT affect TerrainMesh.
    """
    print("\n── Bake Preview ───────────────────────────────────")
    obj = bake_terrain(256, context, target_name="TerrainPreview")
    print("── Preview done ───────────────────────────────────\n")
    return obj


# ── Full bake operator entry point ────────────────────────────────────────────

def run_bake(order_folder, report, context):
    """
    Full bake pipeline: bake_terrain at params.json resolution,
    then export displaced.obj and decimated simplified.obj.

      order_folder — pre-validated path containing params.json + resampled.tif
      report       — operator.report callable
      context      — bpy.context (passed through to bake_terrain for settings)
    """
    print("\n── Bake Full Res ──────────────────────────────────")

    try:
        params = load_params(order_folder)
    except FileNotFoundError as e:
        report({"ERROR"}, str(e))
        return False

    subdivision_level = params.get("subdivision_level", 1024)
    target_triangles  = params.get("target_triangles", 1_000_000)

    print(f"  Order folder:      {order_folder}")
    print(f"  subdivision_level: {subdivision_level}")
    print(f"  target_triangles:  {target_triangles}")

    clear_default_objects()

    try:
        obj = bake_terrain(subdivision_level, context)   # targets TerrainMesh
    except RuntimeError as e:
        report({"ERROR"}, str(e))
        return False

    displaced_path  = os.path.join(order_folder, "displaced.obj")
    simplified_path = os.path.join(order_folder, "simplified.obj")

    export_obj(obj, displaced_path)
    decimate_mesh(obj, target_triangles)
    export_obj(obj, simplified_path)

    report({"INFO"}, "Bake complete. displaced.obj and simplified.obj written.")
    print("── Bake done ──────────────────────────────────────\n")
    return True
