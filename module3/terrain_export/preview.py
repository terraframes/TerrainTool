"""
preview.py — Module 3: resample subprocess, TerrainPreview mesh, and slider timer.
Do NOT run directly. Do NOT import osgeo — resample.py is subprocess-only.
"""

import os
import json
import subprocess

import bpy
import bmesh

from . import bake   # reused: bake.reset_uvs builds clean UV maps


# ── QGIS Python path — read from qgis_config.json at addon load time ─────────

def _read_qgis_python():
    config = os.path.join(os.path.dirname(__file__), "qgis_config.json")
    if os.path.isfile(config):
        try:
            with open(config, "r", encoding="utf-8") as f:
                return json.load(f).get("qgis_python", "")
        except Exception:
            pass
    return r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"


QGIS_PYTHON      = _read_qgis_python()
PREVIEW_OBJ_NAME = "TerrainPreview"
PREVIEW_IMG_NAME = "TerrainPreviewImg"
PREVIEW_TEX_NAME = "TerrainPreviewTex"


# ── Helpers ───────────────────────────────────────────────────────────────────

def err(report, msg):
    """Print an error and optionally call the operator self.report."""
    print(f"  ERROR: {msg}")
    if report:
        report({"ERROR"}, msg)


def check_order(settings, report):
    """
    Validate order folder + params.json. Returns (folder, params_dict) on
    success, or (None, None) with the error already reported on failure.
    """
    folder = bpy.path.abspath(settings.order_folder).rstrip("\\/")
    if not folder:
        report({"ERROR"}, "Order Folder is empty.")
        return None, None
    if not os.path.isdir(folder):
        report({"ERROR"}, f"Order folder not found:\n  {folder}")
        return None, None
    params_path = os.path.join(folder, "params.json")
    if not os.path.isfile(params_path):
        report({"ERROR"}, f"params.json not found in:\n  {folder}")
        return None, None
    with open(params_path, "r", encoding="utf-8") as f:
        return folder, json.load(f)


def _setup_tex(tif_path, reload_existing=False):
    """Load (or reload) a TIF into a Blender image + Displace-compatible texture."""
    img = bpy.data.images.get(PREVIEW_IMG_NAME)
    if reload_existing and img is not None:
        img.filepath = tif_path
        img.reload()
    else:
        if img:
            bpy.data.images.remove(img)
        img = bpy.data.images.load(tif_path)
        img.name = PREVIEW_IMG_NAME
        img.colorspace_settings.name = "Non-Color"  # keep raw 0-1 elevation values
    tex = bpy.data.textures.get(PREVIEW_TEX_NAME)
    if tex is None:
        tex = bpy.data.textures.new(PREVIEW_TEX_NAME, type="IMAGE")
    tex.image = img
    tex.extension = "EXTEND"          # no wrapping at UV edges
    tex.use_interpolation = True
    return img, tex


# ── Run resample.py via subprocess ────────────────────────────────────────────

def run_resample(order_folder, output_path, resolution,
                 min_clamp, max_clamp, gamma, bbox, report):
    """
    Call resample.py via the QGIS Python interpreter.
    Returns the parsed JSON result dict on success, or None on failure.
    Pass report=None when calling from a timer (no operator context).
    """
    raw_dem = os.path.join(order_folder, "raw_dem.tif")
    if not os.path.isfile(raw_dem):
        err(report, f"raw_dem.tif not found in: {order_folder}")
        return None

    cmd = [
        QGIS_PYTHON,
        os.path.join(os.path.dirname(__file__), "resample.py"),
        "--input",      raw_dem,
        "--output",     output_path,
        "--bbox",
            str(bbox.get("min_lat", 0)), str(bbox.get("max_lat", 0)),
            str(bbox.get("min_lon", 0)), str(bbox.get("max_lon", 0)),
        "--resolution", str(resolution),
        "--min_clamp",  str(min_clamp),
        "--max_clamp",  str(max_clamp),
        "--gamma",      str(gamma),
    ]

    print(f"  Calling resample.py at {resolution}×{resolution} ...")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        err(report, "resample.py timed out (>120 s).")
        return None
    except Exception as e:
        err(report, f"Could not launch QGIS Python: {e}\n"
                    "Check the path in qgis_config.json.")
        return None

    # resample.py prints one JSON line — ignore GDAL warnings before it
    json_line = next(
        (ln.strip() for ln in reversed(proc.stdout.splitlines())
         if ln.strip().startswith("{")),
        None,
    )
    if json_line is None:
        err(report,
            f"resample.py returned no JSON.\n"
            f"stdout: {proc.stdout[:200]}\nstderr: {proc.stderr[:200]}")
        return None
    try:
        data = json.loads(json_line)
    except json.JSONDecodeError:
        err(report, f"Could not parse resample.py output:\n{json_line[:200]}")
        return None
    if data.get("status") != "ok":
        err(report, f"resample.py: {data.get('message', 'unknown error')}")
        return None
    return data


# ── TerrainPreview mesh management ────────────────────────────────────────────

def create_preview_mesh(tif_path, displacement_scale):
    """
    Create (or replace) a 256-segment grid named TerrainPreview with a live
    Displace modifier. Modifier is NOT applied — image reloads cheaply on slider change.
    """
    existing = bpy.data.objects.get(PREVIEW_OBJ_NAME)
    if existing:
        bpy.data.objects.remove(existing, do_unlink=True)

    mesh = bpy.data.meshes.new(PREVIEW_OBJ_NAME)
    bm   = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=256, y_segments=256, size=5.0)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(PREVIEW_OBJ_NAME, mesh)
    bake.reset_uvs(obj)   # clean [0,1] UV spanning the whole mesh (reused from bake.py)
    bpy.context.scene.collection.objects.link(obj)

    _, tex = _setup_tex(tif_path, reload_existing=False)
    mod = obj.modifiers.new("Displace", type="DISPLACE")
    mod.texture = tex
    mod.strength = displacement_scale
    mod.mid_level = 0.0
    mod.texture_coords = "UV"
    print(f"  TerrainPreview created. strength={displacement_scale:.3f}")
    return obj


def refresh_preview(tif_path, displacement_scale):
    """Reload preview.tif and update modifier. Does nothing if TerrainPreview is absent."""
    obj = bpy.data.objects.get(PREVIEW_OBJ_NAME)
    if obj is None:
        return
    _, tex = _setup_tex(tif_path, reload_existing=True)
    mod = obj.modifiers.get("Displace")
    if mod:
        mod.texture  = tex
        mod.strength = displacement_scale
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


# ── Slider callback + debounce timer ─────────────────────────────────────────

def on_slider_change(self, context):
    """Property update callback — schedules a preview refresh 0.3 s later."""
    if not bpy.app.timers.is_registered(_deferred_preview_update):
        bpy.app.timers.register(_deferred_preview_update, first_interval=0.3)


def _deferred_preview_update():
    """Timer callback — fires after slider activity settles."""
    try:
        _run_preview_update()
    except Exception as e:
        print(f"  Preview update error: {e}")
    return None   # None cancels the timer (don't repeat)


def _run_preview_update():
    """Re-run 256×256 resample and refresh TerrainPreview displacement texture."""
    scene = bpy.context.scene
    if scene is None:
        return
    settings     = scene.terrain_export_settings
    order_folder = bpy.path.abspath(settings.order_folder).rstrip("\\/")
    if not order_folder or not os.path.isdir(order_folder):
        return
    params_path = os.path.join(order_folder, "params.json")
    if not os.path.isfile(params_path):
        return
    with open(params_path, "r", encoding="utf-8") as f:
        bbox = json.load(f).get("bbox", {})
    if not bbox:
        return
    # Convert metre clamp values → 0–1 range that resample.py expects.
    elev_min   = settings.elevation_min_m
    elev_max   = settings.elevation_max_m
    elev_range = elev_max - elev_min
    if elev_range > 0:
        t_min = max(0.0, min(1.0, (settings.min_clamp - elev_min) / elev_range))
        t_max = max(0.0, min(1.0, (settings.max_clamp - elev_min) / elev_range))
    else:
        # Elevation not recorded yet — pass full range so nothing is clipped.
        t_min, t_max = 0.0, 1.0

    preview_tif = os.path.join(order_folder, "preview.tif")
    result = run_resample(
        order_folder, preview_tif, 256,
        t_min, t_max, settings.gamma,
        bbox, report=None,
    )
    if result:
        refresh_preview(preview_tif, settings.displacement_scale)
