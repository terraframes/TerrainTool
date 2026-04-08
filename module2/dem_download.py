"""
dem_download.py — DEM acquisition helpers for acquire.py.

Handles GLO-30 download from OpenTopography and void-filling via QGIS.
Never imports osgeo — all GDAL calls go through the QGIS Python subprocess.
"""

import os
import subprocess
import requests

LOCAL_ORDERS_ROOT = r"E:\TerrainTool\orders"
QGIS_PYTHON = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"
TIFF_MAGIC = {b"II*\x00", b"MM\x00*"}  # little-endian and big-endian TIFF


def download_glo30(params, order_number):
    """
    Download GLO-30 DEM from OpenTopography and save as raw_dem.tif.
    Returns True on success, False on failure.
    """
    api_key = os.environ.get("OPENTOPO_API_KEY", "")
    if not api_key:
        print(f"  [{order_number}] ERROR: OPENTOPO_API_KEY environment variable is not set.")
        print(f"  [{order_number}]   Run setup.py to configure it.")
        return False

    bbox = params["bbox"]
    query = {
        "demtype": "COP30",
        "south": bbox["min_lat"],
        "north": bbox["max_lat"],
        "west": bbox["min_lon"],
        "east": bbox["max_lon"],
        "outputFormat": "GTiff",
        "API_Key": api_key,
    }

    print(f"  [{order_number}] Requesting GLO-30 from OpenTopography...")
    try:
        resp = requests.get(OPENTOPO_URL, params=query, timeout=300)
    except requests.RequestException as e:
        print(f"  [{order_number}] ERROR: Network request failed — {e}")
        return False

    data = resp.content

    # Validate TIFF magic number (first 4 bytes)
    if len(data) < 4 or data[:4] not in TIFF_MAGIC:
        print(f"  [{order_number}] ERROR: Response is not a valid GeoTIFF.")
        try:
            text = data.decode("utf-8", errors="replace")[:500]
        except Exception:
            text = repr(data[:200])
        print(f"  [{order_number}]   Server response: {text}")
        return False

    dest = os.path.join(LOCAL_ORDERS_ROOT, order_number, "raw_dem.tif")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(data)

    size_mb = len(data) / (1024 * 1024)
    print(f"  [{order_number}] GLO-30 saved -> {dest} ({size_mb:.1f} MB)")
    return True


def run_fillnodata(order_number, tif_path):
    """
    Fill nodata voids in tif_path via QGIS Python subprocess.

    The input is a Cloud Optimized GeoTIFF which cannot be edited in-place.
    Steps:
      1. gdal_translate -> raw_dem_temp.tif (standard GeoTIFF)
      2. gdal.FillNodata on raw_dem_temp.tif -> raw_dem.tif
      3. Delete raw_dem_temp.tif

    Returns True on success, False on failure.
    """
    temp_path = tif_path.replace("raw_dem.tif", "raw_dem_temp.tif")

    inline = (
        "from osgeo import gdal; "
        "gdal.UseExceptions(); "
        # Step 1: translate COG -> standard GeoTIFF
        f"gdal.Translate(r'{temp_path}', r'{tif_path}', format='GTiff'); "
        # Step 2: fillnodata on temp, writing output to tif_path
        f"ds = gdal.Open(r'{temp_path}', gdal.GA_Update); "
        "b = ds.GetRasterBand(1); "
        "gdal.FillNodata(b, None, 100, 0); "
        "ds.FlushCache(); "
        "ds = None; "
        # Step 3: translate filled temp -> final raw_dem.tif
        f"gdal.Translate(r'{tif_path}', r'{temp_path}', format='GTiff'); "
        # Step 4: delete temp
        "import os; "
        f"os.remove(r'{temp_path}'); "
        "print('fillnodata OK')"
    )

    print(f"  [{order_number}] Running gdal_fillnodata via QGIS Python...")
    try:
        result = subprocess.run(
            [QGIS_PYTHON, "-c", inline],
            capture_output=True, text=True, timeout=300
        )
    except FileNotFoundError:
        print(f"  [{order_number}] ERROR: QGIS Python not found at:")
        print(f"  [{order_number}]   {QGIS_PYTHON}")
        print(f"  [{order_number}]   Verify QGIS 3.44.8 is installed.")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [{order_number}] ERROR: gdal_fillnodata timed out after 300 s.")
        return False

    if result.returncode != 0 or "fillnodata OK" not in result.stdout:
        print(f"  [{order_number}] ERROR: gdal_fillnodata subprocess failed.")
        if result.stdout.strip():
            print(f"  [{order_number}]   stdout: {result.stdout.strip()[:400]}")
        if result.stderr.strip():
            print(f"  [{order_number}]   stderr: {result.stderr.strip()[:400]}")
        return False

    print(f"  [{order_number}] Void-fill complete.")
    return True
