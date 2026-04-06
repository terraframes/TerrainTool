"""
glo10_download.py — GLO-10 DEM download from Copernicus S3.

Used for European orders with area_km <= 25.
Probes the bucket to find the correct tile prefix — no hardcoded unverified path.
Merges multi-tile downloads and crops to exact bbox via QGIS Python subprocess.
Never imports osgeo — all GDAL calls go through the QGIS Python subprocess.
"""

import os
import math
import subprocess

LOCAL_ORDERS_ROOT = r"E:\TerrainTool\orders"
QGIS_PYTHON = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
CDSE_ENDPOINT = "https://eodata.dataspace.copernicus.eu"
CDSE_BUCKET = "eodata"
COLLECTION_PREFIX = "Copernicus/DEM/DEMCollection/"


# ── S3 client ─────────────────────────────────────────────────────────────────

def _make_s3_client():
    """Create boto3 S3 client from env vars. Returns (client, error_str)."""
    import boto3
    from botocore.config import Config

    key = os.environ.get("CDSE_S3_KEY", "")
    secret = os.environ.get("CDSE_S3_SECRET", "")
    if not key or not secret:
        return None, (
            "CDSE_S3_KEY or CDSE_S3_SECRET environment variable is not set.\n"
            "  Run setup.py or set them manually with setx."
        )
    client = boto3.client(
        "s3",
        endpoint_url=CDSE_ENDPOINT,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    return client, None


def _is_auth_error(exc):
    """Return True if exc is a boto3 ClientError indicating bad credentials."""
    try:
        from botocore.exceptions import ClientError
        if not isinstance(exc, ClientError):
            return False
        code = exc.response.get("Error", {}).get("Code", "")
        return code in ("403", "AccessDenied", "InvalidAccessKeyId",
                        "SignatureDoesNotMatch", "ExpiredToken")
    except Exception:
        return False


def _print_auth_error(order_number):
    print(f"  [{order_number}] ERROR: Copernicus S3 authentication failed.")
    print(f"  [{order_number}]   Your S3 credentials may be expired.")
    print(f"  [{order_number}]   Regenerate them at: s3-credentials.dataspace.copernicus.eu")
    print(f"  [{order_number}]   Then update CDSE_S3_KEY and CDSE_S3_SECRET with setx.")


# ── Bucket probe ──────────────────────────────────────────────────────────────

def find_glo10_prefix(s3, order_number):
    """
    List the Copernicus S3 bucket to find the GLO-10 tile base prefix.
    Prints all discovered paths for manual verification.
    Returns the tile base prefix string (e.g. '.../DSM/10m/') or None on failure.
    """
    from botocore.exceptions import ClientError

    print(f"  [{order_number}] Probing Copernicus S3 for GLO-10 prefix...")

    # Step 1: list collections under Copernicus/DEM/DEMCollection/
    try:
        resp = s3.list_objects_v2(
            Bucket=CDSE_BUCKET,
            Prefix=COLLECTION_PREFIX,
            Delimiter="/",
            MaxKeys=30,
        )
    except ClientError as e:
        if _is_auth_error(e):
            _print_auth_error(order_number)
            return None
        print(f"  [{order_number}] ERROR: S3 list_objects failed — {e}")
        return None

    collections = [p["Prefix"] for p in resp.get("CommonPrefixes", [])]
    print(f"  [{order_number}] Collections found under {COLLECTION_PREFIX}:")
    for c in collections:
        print(f"    {c}")

    glo10 = [c for c in collections if "GLO-10" in c or "GLO10" in c]
    if not glo10:
        print(f"  [{order_number}] ERROR: No GLO-10 collection found in the bucket.")
        print(f"  [{order_number}]   Inspect the paths printed above to find the correct prefix.")
        return None

    collection = glo10[0]
    print(f"  [{order_number}] Using GLO-10 collection: {collection}")

    # Step 2: confirm DSM/10m/ subpath exists and contains tiles
    tile_base = collection + "DSM/10m/"
    try:
        resp2 = s3.list_objects_v2(
            Bucket=CDSE_BUCKET,
            Prefix=tile_base,
            Delimiter="/",
            MaxKeys=5,
        )
    except ClientError as e:
        if _is_auth_error(e):
            _print_auth_error(order_number)
            return None
        print(f"  [{order_number}] ERROR: Could not list {tile_base} — {e}")
        return None

    sub_prefixes = [p["Prefix"] for p in resp2.get("CommonPrefixes", [])]
    if not sub_prefixes and resp2.get("KeyCount", 0) == 0:
        # Show what is inside the collection so the user can diagnose
        print(f"  [{order_number}] WARNING: {tile_base} appears empty.")
        print(f"  [{order_number}]   Listing {collection} to help diagnose:")
        resp3 = s3.list_objects_v2(
            Bucket=CDSE_BUCKET, Prefix=collection, Delimiter="/", MaxKeys=20
        )
        for p in resp3.get("CommonPrefixes", []):
            print(f"    {p['Prefix']}")
        print(f"  [{order_number}] ERROR: Cannot confirm GLO-10 tile path. See output above.")
        return None

    print(f"  [{order_number}] GLO-10 tile prefix confirmed: {tile_base}")
    print(f"  [{order_number}]   Sample tile folders: {[p.split('/')[-2] for p in sub_prefixes[:3]]}")
    return tile_base


# ── Tile helpers ──────────────────────────────────────────────────────────────

def _lat_tag(lat_floor):
    return f"N{abs(lat_floor):02d}" if lat_floor >= 0 else f"S{abs(lat_floor):02d}"


def _lon_tag(lon_floor):
    return f"E{abs(lon_floor):03d}" if lon_floor >= 0 else f"W{abs(lon_floor):03d}"


def _tile_s3_key(tile_prefix, lat_floor, lon_floor):
    """Return S3 key for the GLO-10 tile at (lat_floor, lon_floor)."""
    lt = _lat_tag(lat_floor)
    ln = _lon_tag(lon_floor)
    folder = f"{lt}_00_{ln}_00_DEM"
    filename = f"DSM_10m_{lt}_00_{ln}_00_DEM.tif"
    return f"{tile_prefix}{folder}/{filename}"


def _tiles_for_bbox(bbox):
    """Return list of (lat_floor, lon_floor) for all 1° tiles overlapping bbox."""
    lat_min = math.floor(bbox["min_lat"])
    lat_max = math.floor(bbox["max_lat"])
    lon_min = math.floor(bbox["min_lon"])
    lon_max = math.floor(bbox["max_lon"])
    return [
        (lat, lon)
        for lat in range(lat_min, lat_max + 1)
        for lon in range(lon_min, lon_max + 1)
    ]


# ── Download helpers ──────────────────────────────────────────────────────────

def _download_tile(s3, order_number, key, local_path):
    """
    Download one S3 tile to local_path.
    Returns True on success, None if tile not found (ocean/no coverage), False on error.
    """
    from botocore.exceptions import ClientError

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        s3.download_file(CDSE_BUCKET, key, local_path)
        size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"  [{order_number}]   {os.path.basename(local_path)} ({size_mb:.1f} MB)")
        return True
    except ClientError as e:
        if _is_auth_error(e):
            _print_auth_error(order_number)
            return False
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            print(f"  [{order_number}]   SKIP {key.split('/')[-1]} — not in S3 (ocean or no coverage)")
            return None
        print(f"  [{order_number}]   ERROR downloading {key}: {e}")
        return False


def _warp_tiles_to_dem(order_number, tile_paths, bbox, out_path):
    """
    Merge and crop tiles to bbox via gdal.Warp in QGIS Python subprocess.
    Handles single tile (crop only) and multiple tiles (merge + crop) identically.
    Returns True on success, False on failure.
    """
    tile_repr = "[" + ", ".join(f"r'{p}'" for p in tile_paths) + "]"
    bounds = f"{bbox['min_lon']}, {bbox['min_lat']}, {bbox['max_lon']}, {bbox['max_lat']}"

    inline = (
        "from osgeo import gdal; "
        "gdal.UseExceptions(); "
        f"tiles = {tile_repr}; "
        "opts = gdal.WarpOptions("
        "    format='GTiff', "
        f"   outputBounds=({bounds}), "
        "    outputBoundsSRS='EPSG:4326'"
        "); "
        f"ds = gdal.Warp(r'{out_path}', tiles, options=opts); "
        "if ds is None: raise RuntimeError('gdal.Warp returned None'); "
        "ds = None; "
        "print('warp_ok')"
    )

    n = len(tile_paths)
    action = "Cropping tile" if n == 1 else f"Merging {n} tiles and cropping"
    print(f"  [{order_number}] {action} to bbox via gdalwarp...")
    try:
        result = subprocess.run(
            [QGIS_PYTHON, "-c", inline],
            capture_output=True, text=True, timeout=600,
        )
    except FileNotFoundError:
        print(f"  [{order_number}] ERROR: QGIS Python not found at {QGIS_PYTHON}")
        print(f"  [{order_number}]   Verify QGIS 3.44.8 is installed.")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [{order_number}] ERROR: gdalwarp timed out after 600 s.")
        return False

    if result.returncode != 0 or "warp_ok" not in result.stdout:
        print(f"  [{order_number}] ERROR: gdalwarp subprocess failed.")
        if result.stdout.strip():
            print(f"  [{order_number}]   stdout: {result.stdout.strip()[:400]}")
        if result.stderr.strip():
            print(f"  [{order_number}]   stderr: {result.stderr.strip()[:400]}")
        return False

    return True


# ── Public entry point ────────────────────────────────────────────────────────

def download_glo10(params, order_number):
    """
    Download GLO-10 DEM from Copernicus S3 and save as raw_dem.tif.
    Probes bucket for correct prefix, downloads required tiles, merges and crops.
    Returns True on success, False on failure.
    """
    s3, err = _make_s3_client()
    if s3 is None:
        print(f"  [{order_number}] ERROR: {err}")
        return False

    tile_prefix = find_glo10_prefix(s3, order_number)
    if tile_prefix is None:
        return False

    bbox = params["bbox"]
    tiles = _tiles_for_bbox(bbox)
    print(f"  [{order_number}] Bounding box spans {len(tiles)} GLO-10 tile(s): "
          f"{[(_lat_tag(lat) + _lon_tag(lon)) for lat, lon in tiles]}")

    order_dir = os.path.join(LOCAL_ORDERS_ROOT, order_number)
    os.makedirs(order_dir, exist_ok=True)

    downloaded = []
    for lat_floor, lon_floor in tiles:
        key = _tile_s3_key(tile_prefix, lat_floor, lon_floor)
        lt = _lat_tag(lat_floor)
        ln = _lon_tag(lon_floor)
        local_tile = os.path.join(order_dir, f"tile_{lt}_{ln}.tif")
        result = _download_tile(s3, order_number, key, local_tile)
        if result is False:
            return False     # hard error (auth failure, unexpected S3 error)
        if result is True:
            downloaded.append(local_tile)
        # None = ocean / no coverage — skip silently

    if not downloaded:
        attempted = [_tile_s3_key(tile_prefix, lat, lon) for lat, lon in tiles]
        print(f"  [{order_number}] ERROR: No GLO-10 tiles found for this bounding box.")
        print(f"  [{order_number}]   Tiles attempted:")
        for k in attempted:
            print(f"    {k}")
        return False

    raw_dem_path = os.path.join(order_dir, "raw_dem.tif")
    ok = _warp_tiles_to_dem(order_number, downloaded, bbox, raw_dem_path)

    # Clean up individual tile files regardless of warp outcome
    for tp in downloaded:
        try:
            os.remove(tp)
        except OSError:
            pass

    if not ok:
        return False

    size_mb = os.path.getsize(raw_dem_path) / (1024 * 1024)
    print(f"  [{order_number}] GLO-10 raw DEM saved → {raw_dem_path} ({size_mb:.1f} MB)")
    return True
