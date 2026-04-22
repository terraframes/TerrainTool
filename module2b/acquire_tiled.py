"""
acquire_tiled.py — Module 2b tiled API DEM handler.

Streams tiles via /vsicurl/ from a STAC API directly into gdalwarp —
no local tile download required. Saves result as raw_dem.tif in the
order folder.

All GDAL operations run via subprocess to the QGIS Python executable.
Never import osgeo directly in this file.

Public API:
    acquire_tiled_dem(params, order_number, ds_entry) -> bool
"""

import json
import os
import subprocess
import sys

import requests

QGIS_PYTHON = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
LOCAL_ORDERS_ROOT = r"E:\TerrainTool\orders"


def acquire_tiled_dem(params, order_number, ds_entry):
    """
    Stream STAC tiles via /vsicurl/, mosaic if needed, and save raw_dem.tif.
    Returns True on success, False on any failure.
    """

    # ------------------------------------------------------------------
    # Step 1 — Extract bbox and apply 5% padding on each edge
    # ------------------------------------------------------------------

    bbox = params["bbox"]
    min_lon, min_lat = bbox["min_lon"], bbox["min_lat"]
    max_lon, max_lat = bbox["max_lon"], bbox["max_lat"]

    lat_pad = (max_lat - min_lat) * 0.05
    lon_pad = (max_lon - min_lon) * 0.05
    pad_min_lon = min_lon - lon_pad
    pad_min_lat = min_lat - lat_pad
    pad_max_lon = max_lon + lon_pad
    pad_max_lat = max_lat + lat_pad

    # ------------------------------------------------------------------
    # Step 2 — Query STAC API
    # ------------------------------------------------------------------

    try:
        import pystac_client
    except ImportError:
        print(f"  [{order_number}] ERROR: pystac-client not installed. Run: pip install pystac-client")
        return False

    client = pystac_client.Client.open(ds_entry["stac_api_url"])
    search = client.search(
        collections=[ds_entry["stac_collection"]],
        bbox=[pad_min_lon, pad_min_lat, pad_max_lon, pad_max_lat]
    )
    items = list(search.items())

    if not items:
        print(
            f"  [{order_number}] ERROR: No tiles found for bbox "
            f"{pad_min_lon:.4f},{pad_min_lat:.4f},{pad_max_lon:.4f},{pad_max_lat:.4f}"
        )
        return False

    print(f"  [{order_number}] Found {len(items)} tile(s) from STAC.")

    # ------------------------------------------------------------------
    # Step 3 — Extract /vsicurl/ URLs from items
    #
    # ArcticDEM STAC exposes s3://pgc-opendata-dems/ hrefs; convert to
    # the public HTTPS equivalent so /vsicurl/ can reach them without
    # AWS credentials.
    # ------------------------------------------------------------------

    asset_key = ds_entry["stac_asset_key"]
    vsicurl_urls = []

    for item in items:
        asset = item.assets.get(asset_key)
        if asset is None:
            print(f"  [{order_number}] WARNING: No asset '{asset_key}' in item {item.id}, skipping.")
            continue
        href = asset.href
        if href.startswith("s3://pgc-opendata-dems/"):
            href = href.replace(
                "s3://pgc-opendata-dems/",
                "https://pgc-opendata-dems.s3.us-west-2.amazonaws.com/",
            )
        url = f"/vsicurl/{href}"
        print(f"  [{order_number}] Using: {url}")
        vsicurl_urls.append(url)

    if not vsicurl_urls:
        print(f"  [{order_number}] ERROR: No valid asset URLs found after processing items.")
        return False

    # ------------------------------------------------------------------
    # Step 4 — Create output path
    # ------------------------------------------------------------------

    order_dir = os.path.join(LOCAL_ORDERS_ROOT, order_number)
    os.makedirs(order_dir, exist_ok=True)
    raw_dem_path = os.path.join(order_dir, "raw_dem.tif")

    # ------------------------------------------------------------------
    # Step 5 — gdalwarp (with optional VRT mosaic) via QGIS subprocess
    # ------------------------------------------------------------------

    src_nodata = ds_entry["nodata"]

    # GDAL config block — set before any gdal call in the inline script
    gdal_config = (
        "gdal.SetConfigOption('GDAL_HTTP_UNSAFESSL', 'YES'); "
        "gdal.SetConfigOption('CPL_VSIL_CURL_ALLOWED_EXTENSIONS', '.tif'); "
        "gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR'); "
        "gdal.SetConfigOption('CPL_VSIL_CURL_USE_CACHE', 'YES'); "
    )

    warp_opts = (
        "gdal.WarpOptions("
        "    dstSRS='EPSG:4326', "
        f"   outputBounds=({pad_min_lon}, {pad_min_lat}, {pad_max_lon}, {pad_max_lat}), "
        f"   srcNodata={repr(src_nodata)}, "
        "    dstNodata=-9999.0, "
        "    resampleAlg='bilinear', "
        "    outputType=gdal.GDT_Float32, "
        "    format='GTiff'"
        ")"
    )

    use_vrt = len(vsicurl_urls) > 1
    vrt_path = raw_dem_path.replace("raw_dem.tif", "mosaic.vrt")

    if use_vrt:
        urls_repr = repr(vsicurl_urls)
        inline = (
            "from osgeo import gdal; "
            "gdal.UseExceptions(); "
            + gdal_config
            + f"vrt = gdal.BuildVRT(r'{vrt_path}', {urls_repr}); "
            "vrt.FlushCache(); vrt = None; "
            f"opts = {warp_opts}; "
            f"result = gdal.Warp(r'{raw_dem_path}', r'{vrt_path}', options=opts); "
            "result.FlushCache(); result = None; "
            "print('gdalwarp OK')"
        )
    else:
        source_url = vsicurl_urls[0]
        inline = (
            "from osgeo import gdal; "
            "gdal.UseExceptions(); "
            + gdal_config
            + f"opts = {warp_opts}; "
            f"result = gdal.Warp(r'{raw_dem_path}', {repr(source_url)}, options=opts); "
            "result.FlushCache(); result = None; "
            "print('gdalwarp OK')"
        )

    print(f"  [{order_number}] Running gdalwarp via QGIS Python...")
    try:
        result = subprocess.run(
            [QGIS_PYTHON, "-c", inline],
            capture_output=True, text=True, timeout=900,
        )
    except FileNotFoundError:
        print(f"  [{order_number}] ERROR: QGIS Python not found at: {QGIS_PYTHON}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [{order_number}] ERROR: gdalwarp timed out after 900 s.")
        return False

    if result.returncode != 0 or "gdalwarp OK" not in result.stdout:
        print(f"  [{order_number}] ERROR: gdalwarp subprocess failed.")
        if result.stdout.strip():
            print(f"  [{order_number}]   stdout: {result.stdout.strip()[:400]}")
        if result.stderr.strip():
            print(f"  [{order_number}]   stderr: {result.stderr.strip()[:400]}")
        return False

    if use_vrt:
        cleanup = f"import os; os.remove(r'{vrt_path}'); print('vrt removed')"
        subprocess.run(
            [QGIS_PYTHON, "-c", cleanup],
            capture_output=True, text=True, timeout=30,
        )

    # ------------------------------------------------------------------
    # Step 6 — Done
    # ------------------------------------------------------------------

    size_mb = os.path.getsize(raw_dem_path) / (1024 * 1024)
    print(f"  [{order_number}] acquire_tiled_dem complete -> {raw_dem_path} ({size_mb:.1f} MB)")
    return True
