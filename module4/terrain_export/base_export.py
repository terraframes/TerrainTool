"""
base_export.py — "Add Base and Export" operator logic.

Export pipeline (runs on a temporary duplicate — scene mesh is never modified):
  1. Duplicate TerrainMesh
  2. Scale the duplicate uniformly so its XY extents equal exactly print_size_mm
  3. Add the base by extrusion: bottom at Z = -base_thickness_mm (absolute mm,
     independent of print size — already in mm after step 2)
  4. Recalculate face normals so they point outward consistently
  5. Check for non-manifold edges
  6. Print final bounding box min/max XYZ in mm
  7. Export final.stl (raw coordinates = mm, no unit conversion)
  8. Delete the duplicate

Result in slicer:
  XY = print_size_mm × print_size_mm
  Z  = terrain relief (scales with print size) + base_thickness_mm (fixed)
"""

import bpy
import bmesh
import os
import json


def load_params(order_folder):
    """Read params.json from the given folder. Returns a dict or raises."""
    path = os.path.join(order_folder, "params.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"params.json not found at:\n  {path}\n"
            "Make sure the order folder path is correct."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_params(order_folder, params):
    """Write params dict back to params.json."""
    path = os.path.join(order_folder, "params.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    print(f"  params.json updated: {path}")


def get_terrain_mesh():
    """Return the TerrainMesh object, or None if it doesn't exist."""
    return bpy.data.objects.get("TerrainMesh")


def add_base_by_extrusion(obj, base_z):
    """
    Add a watertight base to the terrain mesh using pure extrusion.
    No existing terrain vertices are moved or modified.

    base_z — the Z coordinate for all bottom vertices (a negative value).
             Caller scales the mesh to mm before calling this, so
             base_z = -base_thickness_mm gives the exact depth in the STL.

    Step 1 — Find the perimeter boundary edge loop.
    Step 2 — For each boundary vertex create a new vertex directly below it
             at Z = base_z (X and Y are unchanged), then create a quad
             side-wall face per boundary edge.
    Step 3 — Fill the open bottom loop with a flat cap face.
    Step 4 — Recalculate face normals to point outward consistently.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    # ── Step 1: identify the perimeter ───────────────────────────────────────
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    if not boundary_edges:
        bm.free()
        raise RuntimeError(
            "No boundary edges found on TerrainMesh.\n"
            "The mesh may already be a closed solid, or Bake Full Res "
            "has not been run yet."
        )

    boundary_verts = {v for e in boundary_edges for v in e.verts}
    print(
        f"  Step 1: {len(boundary_edges)} perimeter edges, "
        f"{len(boundary_verts)} perimeter vertices identified."
    )

    # ── Step 2: extrude downward, create side walls ───────────────────────────
    # Create one new vertex directly below each boundary vertex.
    # X and Y are preserved exactly — the wall follows the terrain edge profile.
    vert_map = {}   # original BMVert -> new BMVert below it
    for v in boundary_verts:
        nv = bm.verts.new((v.co.x, v.co.y, base_z))
        vert_map[v] = nv

    # One quad side-wall face per boundary edge: top-left, top-right,
    # bottom-right, bottom-left. Winding is corrected in Step 4.
    for edge in boundary_edges:
        v0, v1 = edge.verts[0], edge.verts[1]
        try:
            bm.faces.new([v0, v1, vert_map[v1], vert_map[v0]])
        except ValueError:
            pass   # face already exists — skip silently

    print(
        f"  Step 2: {len(boundary_edges)} side wall quads created "
        f"(bottom at Z={base_z:.6f} Blender units)."
    )

    # ── Step 3: fill the bottom cap ───────────────────────────────────────────
    # After adding side walls the bottom ring of new vertices has open boundary
    # edges. contextual_create turns a closed edge loop into a flat n-gon face.
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    new_verts_set = set(vert_map.values())
    bottom_edges = [
        e for e in bm.edges
        if e.is_boundary and all(v in new_verts_set for v in e.verts)
    ]

    if not bottom_edges:
        bm.free()
        raise RuntimeError(
            "Could not find bottom boundary edges after side wall creation.\n"
            "This is unexpected — check the mesh for pre-existing geometry issues."
        )

    bmesh.ops.contextual_create(bm, geom=bottom_edges)
    print(f"  Step 3: bottom cap filled ({len(bottom_edges)} edges).")

    # ── Step 4: fix normals ───────────────────────────────────────────────────
    # Side wall winding depends on which direction the boundary loop travels,
    # so we recalculate all normals to point outward consistently.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def print_z_range(obj):
    """Print the min and max Z of every vertex in the mesh."""
    zs = [v.co.z for v in obj.data.vertices]
    print(f"  Z range: min={min(zs):.4f} m   max={max(zs):.4f} m")


def check_non_manifold(obj):
    """
    Select and report any non-manifold edges.
    Returns the count found.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_non_manifold()

    bm = bmesh.from_edit_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bad_edges = [e for e in bm.edges if e.select]
    count = len(bad_edges)

    if count > 0:
        print(f"  WARNING: {count} non-manifold edge(s) found:")
        for e in bad_edges[:20]:
            mid = (e.verts[0].co + e.verts[1].co) / 2
            print(f"    edge {e.index}  midpoint=({mid.x:.4f}, {mid.y:.4f}, {mid.z:.4f})")
        if count > 20:
            print(f"    ... and {count - 20} more (check Blender console for full list)")
    else:
        print("  Mesh is manifold — no non-manifold edges found.")

    bpy.ops.object.mode_set(mode="OBJECT")
    return count


def export_stl(obj, filepath):
    """
    Export the given object as a binary STL file.
    Vertex coordinates are written as-is — no unit conversion applied.
    The caller is responsible for scaling vertices to mm before calling this.
    """
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.wm.stl_export(
        filepath=filepath,
        export_selected_objects=True,
        ascii_format=False,
        use_scene_unit=False,
    )

    print(f"  Exported: {filepath}")


# ── Main operator function ────────────────────────────────────────────────────

def run_add_base_and_export(order_folder, base_thickness_mm, print_size_mm, report):
    """
    Add base and export pipeline.
      order_folder      — path to the order folder containing params.json
      base_thickness_mm — value from the UI spinner (overrides params.json)
      print_size_mm     — value from the UI spinner (overrides params.json)
      report            — operator.report callable
    Returns True on success, False on failure.
    """
    print("\n── Add Base and Export ────────────────────────────")

    # Check terrain mesh exists
    obj = get_terrain_mesh()
    if obj is None:
        report(
            {"ERROR"},
            "TerrainMesh not found in the scene.\n"
            "Run 'Bake Full Res' first to create the terrain mesh.",
        )
        return False

    # Load params (needed for save-back and any other settings)
    try:
        params = load_params(order_folder)
    except FileNotFoundError as e:
        report({"ERROR"}, str(e))
        return False

    stl_path = os.path.join(order_folder, "final.stl")

    print(f"  Order folder:      {order_folder}")
    print(f"  Print size:        {print_size_mm} mm")
    print(f"  Base thickness:    {base_thickness_mm} mm")

    # ── Compute scale and base depth in Blender units ────────────────────────
    verts_scene = obj.data.vertices
    xs0 = [v.co.x for v in verts_scene]
    ys0 = [v.co.y for v in verts_scene]
    xy_extent = max(max(xs0) - min(xs0), max(ys0) - min(ys0))
    if xy_extent == 0:
        report({"ERROR"}, "Mesh has zero XY extent — cannot scale to print size.")
        return False
    scale = print_size_mm / xy_extent
    # base_z in Blender units: scale × base_z_blender = -base_thickness_mm in STL
    base_z_blender = -base_thickness_mm / scale

    print(f"  XY extent: {xy_extent:.4f} Blender units  →  scale: {scale:.4f}×")
    print(f"  Base in viewport at Z = {base_z_blender:.4f} Blender units")

    # ── Add base to the scene mesh so it shows in the viewport ───────────────
    try:
        add_base_by_extrusion(obj, base_z_blender)
    except RuntimeError as e:
        report({"ERROR"}, str(e))
        return False

    # ── Duplicate (with base) for scaled export, then delete after ────────────
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate(linked=False)
    export_obj = bpy.context.active_object
    export_obj.name = "TerrainMeshExportTemp"

    for v in export_obj.data.vertices:
        v.co *= scale
    export_obj.data.update()

    # ── Non-manifold check ────────────────────────────────────────────────────
    bad_count = check_non_manifold(export_obj)
    if bad_count > 0:
        report(
            {"WARNING"},
            f"{bad_count} non-manifold edge(s) found — mesh may not be fully "
            "watertight. Check the Blender console for locations.",
        )

    # ── Print final bounding box to confirm all three axes are correct ─────────
    verts = export_obj.data.vertices
    xs = [v.co.x for v in verts]
    ys = [v.co.y for v in verts]
    zs = [v.co.z for v in verts]
    print(
        f"  Final STL bounding box (mm):\n"
        f"    X: {min(xs):.2f} → {max(xs):.2f}  (width  {max(xs) - min(xs):.2f} mm)\n"
        f"    Y: {min(ys):.2f} → {max(ys):.2f}  (depth  {max(ys) - min(ys):.2f} mm)\n"
        f"    Z: {min(zs):.2f} → {max(zs):.2f}  (height {max(zs) - min(zs):.2f} mm)"
    )

    # ── Export then delete the temporary object ───────────────────────────────
    export_stl(export_obj, stl_path)
    bpy.data.objects.remove(export_obj, do_unlink=True)
    bpy.context.view_layer.objects.active = obj

    # ── Write settings back to params.json ───────────────────────────────────
    params["base_thickness_mm"] = base_thickness_mm
    params["print_size_mm"] = print_size_mm
    save_params(order_folder, params)

    report({"INFO"}, f"Export complete. final.stl written to {order_folder}")
    print("── Add Base and Export done ───────────────────────\n")
    return True
