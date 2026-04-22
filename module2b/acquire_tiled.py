"""
acquire_tiled.py — Module 2b tiled API DEM handler.

Downloads tiles from a STAC API, mosaics them, and saves the result
as raw_dem.tif in the order folder.

All GDAL operations run via subprocess to the QGIS Python executable.
Never import osgeo directly in this file.

Public API:
    acquire_tiled_dem(params, order_number, ds_entry) -> bool
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import requests

QGIS_PYTHON = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
LOCAL_ORDERS_ROOT = r"E:\TerrainTool\orders"


def acquire_tiled_dem(params, order_number, ds_entry):
    """
    Download tiles from a STAC API, mosaic, and save raw_dem.tif.
    Returns True on success, False on any failure.
    """

    try:
        import pystac_client
    except ImportError as exc:
        print(f"  [{order_number}] ERROR: pystac_client not available: {exc}")
        return False

    # ------------------------------------------------------------------
    # Step 1 — Extract bbox and apply 5% padding on each edge
    # ------------------------------------------------------------------

    bbox = params["bbox"]
    min_lon = bbox["min_lon"]
    min_lat = bbox["min_lat"]
    max_lon = bbox["max_lon"]
    max_lat = bbox["max_lat"]

    lat_pad = (max_lat - min_lat) * 0.05
    lon_pad = (max_lon - min_lon) * 0.05
    pad_min_lon = min_lon - lon_pad
    pad_min_lat = min_lat - lat_pad
    pad_max_lon = max_lon + lon_pad
    pad_max_lat = max_lat + lat_pad

    # ------------------------------------------------------------------
    # Step 2 — Query STAC API
    # ------------------------------------------------------------------

    print(f"  [{order_number}] Querying STAC API: {ds_entry['stac_api_url']}")
    try:
        client = pystac_client.Client.open(ds_entry["stac_api_url"])
        search = client.search(
            collections=[ds_entry["stac_collection"]],
            bbox=[pad_min_lon, pad_min_lat, pad_max_lon, pad_max_lat],
        )
        items = list(search.items())
    except Exception as exc:
        print(f"  [{order_number}] ERROR: STAC search failed: {exc}")
        return False

    if not items:
        print(f"  [{order_number}] ERROR: No STAC tiles found for bbox.")
        return False

    print(f"  [{order_number}] Found {len(items)} matching tile(s).")

    # ------------------------------------------------------------------
    # Step 3 — Extract HTTPS download URLs from items
    # ------------------------------------------------------------------

    asset_key = ds_entry["stac_asset_key"]
    download_urls = []

    for item in items:
        asset = item.assets.get(asset_key)
        if asset is None:
            print(f"  [{order_number}] WARNING: No asset '{asset_key}' in item {item.id}, skipping.")
            continue
        href = asset.href
        if not href.startswith("https://"):
            # Some STAC catalogs expose alternate hrefs (e.g. s3:// primary, https:// alternate)
            alternate = asset.extra_fields.get("alternate", {})
            https_href = next(
                (v.get("href") for v in alternate.values()
                 if isinstance(v, dict) and v.get("href", "").startswith("https://")),
                None,
            )
            if https_href:
                href = https_href
            else:
                print(f"  [{order_number}] WARNING: No HTTPS href for item {item.id}, skipping.")
                continue
        download_urls.append((item.id, href))

    if not download_urls:
        print(f"  [{order_number}] ERROR: No downloadable HTTPS tiles after filtering.")
        return False

    # ------------------------------------------------------------------
    # Step 4 — Download each tile to a temp folder
    # ------------------------------------------------------------------

    temp_dir = tempfile.mkdtemp()
    tile_paths = []
    total = len(download_urls)

    for idx, (item_id, url) in enumerate(download_urls, start=1):
        print(f"  [{order_number}] Downloading tile {idx}/{total}: {item_id}")
        tile_path = os.path.join(temp_dir, f"{item_id}_dem.tif")
        try:
            resp = requests.get(url, stream=True, timeout=300)
            resp.raise_for_status()
            with open(tile_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
        except requests.RequestException as exc:
            print(f"  [{order_number}] ERROR: Download failed for {item_id}: {exc}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        tile_paths.append(tile_path)

    # ------------------------------------------------------------------
    # Step 5 — Mosaic (if multiple tiles) then gdalwarp to padded bbox
    # ------------------------------------------------------------------

    order_dir = os.path.join(LOCAL_ORDERS_ROOT, order_number)
    os.makedirs(order_dir, exist_ok=True)
    raw_dem_path = os.path.join(order_dir, "raw_dem.tif")

    if len(tile_paths) == 1:
        source_path = tile_paths[0]
        print(f"  [{order_number}] Single tile, skipping VRT.")
    else:
        vrt_path = os.path.join(temp_dir, "mosaic.vrt")
        print(f"  [{order_number}] Building VRT from {len(tile_paths)} tiles...")
        tile_paths_repr = repr(tile_paths)
        inline = (
            "from osgeo import gdal; "
            "gdal.UseExceptions(); "
            f"vrt = gdal.BuildVrt(r'{vrt_path}', {tile_paths_repr}); "
            "vrt.FlushCache(); "
            "vrt = None; "
            "print('buildvrt OK')"
        )
        try:
            result = subprocess.run(
                [QGIS_PYTHON, "-c", inline],
                capture_output=True, text=True, timeout=120,
            )
        except FileNotFoundError:
            print(f"  [{order_number}] ERROR: QGIS Python not found at: {QGIS_PYTHON}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        except subprocess.TimeoutExpired:
            print(f"  [{order_number}] ERROR: gdal.BuildVrt timed out after 120 s.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        if result.returncode != 0 or "buildvrt OK" not in result.stdout:
            print(f"  [{order_number}] ERROR: gdal.BuildVrt subprocess failed.")
            if result.stdout.strip():
                print(f"  [{order_number}]   stdout: {result.stdout.strip()[:400]}")
            if result.stderr.strip():
                print(f"  [{order_number}]   stderr: {result.stderr.strip()[:400]}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        source_path = vrt_path
        print(f"  [{order_number}] VRT created: {vrt_path}")

    print(f"  [{order_number}] Running gdalwarp (mosaic + crop) via QGIS Python...")
    src_nodata = ds_entry["nodata"]
    inline = (
        "from osgeo import gdal; "
        "gdal.UseExceptions(); "
        "opts = gdal.WarpOptions("
        "    dstSRS='EPSG:4326', "
        f"   outputBounds=({pad_min_lon}, {pad_min_lat}, {pad_max_lon}, {pad_max_lat}), "
        f"   srcNodata={repr(src_nodata)}, "
        "    dstNodata=-9999.0, "
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
            capture_output=True, text=True, timeout=900,
        )
    except FileNotFoundError:
        print(f"  [{order_number}] ERROR: QGIS Python not found at: {QGIS_PYTHON}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
    except subprocess.TimeoutExpired:
        print(f"  [{order_number}] ERROR: gdalwarp timed out after 900 s.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    if result.returncode != 0 or "gdalwarp OK" not in result.stdout:
        print(f"  [{order_number}] ERROR: gdalwarp subprocess failed.")
        if result.stdout.strip():
            print(f"  [{order_number}]   stdout: {result.stdout.strip()[:400]}")
        if result.stderr.strip():
            print(f"  [{order_number}]   stderr: {result.stderr.strip()[:400]}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # ------------------------------------------------------------------
    # Step 6 — Clean up temp folder
    # ------------------------------------------------------------------

    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"  [{order_number}] Temp folder cleaned up.")

    # ------------------------------------------------------------------
    # Step 7 — Done
    # ------------------------------------------------------------------

    size_mb = os.path.getsize(raw_dem_path) / (1024 * 1024)
    print(f"  [{order_number}] acquire_tiled_dem complete -> {raw_dem_path} ({size_mb:.1f} MB)")
    return True
