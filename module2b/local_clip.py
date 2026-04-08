"""
local_clip.py — Module 2b local raster handler.

Clips a locally-stored high-resolution DEM to an order's bounding box
and saves the result as raw_dem.tif in the order folder.

All GDAL operations run via subprocess to the QGIS Python executable.
Never import osgeo directly in this file.

Public API:
    clip_local_dem(params, order_number) -> bool
"""

import json
import os
import subprocess
import sys

QGIS_PYTHON = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
LOCAL_ORDERS_ROOT = r"E:\TerrainTool\orders"
DATASETS_ROOT = r"E:\TerrainTool\datasets"
LOCAL_DATASETS_JSON = r"E:\TerrainTool\datasets\local_datasets.json"


def clip_local_dem(params, order_number):
    """
    Clip a local source DEM to the order's bounding box and save raw_dem.tif.
    Returns True on success, False on any failure.
    """

    # ------------------------------------------------------------------
    # Step 1 — Load dataset registry and look up the order's dataset key
    # ------------------------------------------------------------------

    if not os.path.isfile(LOCAL_DATASETS_JSON):
        print(f"  [{order_number}] ERROR: local_datasets.json not found at: {LOCAL_DATASETS_JSON}")
        return False

    with open(LOCAL_DATASETS_JSON, "r", encoding="utf-8") as f:
        datasets = json.load(f)

    dataset_key = params.get("dataset", "")
    if dataset_key not in datasets:
        print(f"  [{order_number}] ERROR: Dataset '{dataset_key}' not found in local_datasets.json.")
        print(f"  [{order_number}]   Available: {list(datasets.keys())}")
        return False

    ds_entry = datasets[dataset_key]
    files = ds_entry.get("files", [])
    nodata_value = ds_entry.get("nodata_value", -9999)

    if not files:
        print(f"  [{order_number}] ERROR: No files listed for dataset '{dataset_key}'.")
        return False

    for f in files:
        if not os.path.isfile(f):
            print(f"  [{order_number}] ERROR: Source file not found: {f}")
            return False

    # ------------------------------------------------------------------
    # Step 2 — Build output path and create the order folder
    # ------------------------------------------------------------------

    order_dir = os.path.join(LOCAL_ORDERS_ROOT, order_number)
    os.makedirs(order_dir, exist_ok=True)
    raw_dem_path = os.path.join(order_dir, "raw_dem.tif")

    # ------------------------------------------------------------------
    # Step 3 — If multiple source files, merge into a VRT; else use directly
    # ------------------------------------------------------------------

    vrt_path = None  # track whether we created a VRT so we can delete it later

    if len(files) > 1:
        vrt_path = os.path.join(order_dir, "source_mosaic.vrt")
        print(f"  [{order_number}] Merging {len(files)} source files into VRT...")

        # gdal.BuildVrt accepts a list of source paths and writes a virtual mosaic
        files_repr = repr(files)
        inline = (
            "from osgeo import gdal; "
            "gdal.UseExceptions(); "
            f"vrt = gdal.BuildVrt(r'{vrt_path}', {files_repr}); "
            "vrt.FlushCache(); "
            "vrt = None; "
            "print('buildvrt OK')"
        )
        result = subprocess.run(
            [QGIS_PYTHON, "-c", inline],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0 or "buildvrt OK" not in result.stdout:
            print(f"  [{order_number}] ERROR: gdal.BuildVrt subprocess failed.")
            if result.stdout.strip():
                print(f"  [{order_number}]   stdout: {result.stdout.strip()[:400]}")
            if result.stderr.strip():
                print(f"  [{order_number}]   stderr: {result.stderr.strip()[:400]}")
            return False

        source_path = vrt_path
        print(f"  [{order_number}] VRT created: {vrt_path}")
    else:
        # Single file — use it directly as the warp source
        source_path = files[0]
        print(f"  [{order_number}] Single source file: {source_path}")

    # ------------------------------------------------------------------
    # Step 4 — gdalwarp: reproject to EPSG:4326, clip to padded bbox, float32
    #
    # 5% padding on each edge matches the two-pass pattern in resample.py
    # and ensures the bilinear kernel always has valid source pixels at edges.
    # The downstream resample.py crop pass will trim back to the exact bbox.
    # ------------------------------------------------------------------

    bbox = params["bbox"]
    min_lon = bbox["min_lon"]
    min_lat = bbox["min_lat"]
    max_lon = bbox["max_lon"]
    max_lat = bbox["max_lat"]

    lat_pad = (max_lat - min_lat) * 0.05
    lon_pad = (max_lon - min_lon) * 0.05
    te_min_lon = min_lon - lon_pad
    te_min_lat = min_lat - lat_pad
    te_max_lon = max_lon + lon_pad
    te_max_lat = max_lat + lat_pad

    print(f"  [{order_number}] Running gdalwarp (reproject + clip) via QGIS Python...")

    # gdalwarp -te expects xmin ymin xmax ymax = min_lon min_lat max_lon max_lat
    inline = (
        "from osgeo import gdal; "
        "gdal.UseExceptions(); "
        "opts = gdal.WarpOptions("
        "    dstSRS='EPSG:4326', "
        f"   outputBounds=({te_min_lon}, {te_min_lat}, {te_max_lon}, {te_max_lat}), "
        f"   srcNodata={nodata_value}, "
        "    dstNodata=-9999, "
        "    resampleAlg='bilinear', "
        "    outputType=gdal.GDT_Float32, "
        "    format='GTiff'"
        "); "
        f"result = gdal.Warp(r'{raw_dem_path}', r'{source_path}', options=opts); "
        "result.FlushCache(); "
        "result = None; "
        "print('gdalwarp OK')"
    )
    try:
        result = subprocess.run(
            [QGIS_PYTHON, "-c", inline],
            capture_output=True, text=True, timeout=600
        )
    except FileNotFoundError:
        print(f"  [{order_number}] ERROR: QGIS Python not found at: {QGIS_PYTHON}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [{order_number}] ERROR: gdalwarp timed out after 600 s.")
        return False

    if result.returncode != 0 or "gdalwarp OK" not in result.stdout:
        print(f"  [{order_number}] ERROR: gdalwarp subprocess failed.")
        if result.stdout.strip():
            print(f"  [{order_number}]   stdout: {result.stdout.strip()[:400]}")
        if result.stderr.strip():
            print(f"  [{order_number}]   stderr: {result.stderr.strip()[:400]}")
        return False

    size_mb = os.path.getsize(raw_dem_path) / (1024 * 1024)
    print(f"  [{order_number}] gdalwarp complete -> {raw_dem_path} ({size_mb:.1f} MB)")

    # ------------------------------------------------------------------
    # Step 5 — Fill nodata voids using Module 2's run_fillnodata
    # ------------------------------------------------------------------

    # Insert module2 at the front of sys.path so run_fillnodata can be imported
    module2_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "module2")
    module2_dir = os.path.normpath(module2_dir)
    sys.path.insert(0, module2_dir)
    from dem_download import run_fillnodata  # noqa: E402

    if not run_fillnodata(order_number, raw_dem_path):
        return False

    # ------------------------------------------------------------------
    # Step 6 — Delete the temporary VRT if one was created
    # ------------------------------------------------------------------

    if vrt_path and os.path.isfile(vrt_path):
        os.remove(vrt_path)
        print(f"  [{order_number}] Temporary VRT deleted.")

    # ------------------------------------------------------------------
    # Step 7 — Done
    # ------------------------------------------------------------------

    print(f"  [{order_number}] clip_local_dem complete. raw_dem.tif ready.")
    return True
