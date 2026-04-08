"""
acquire.py — Module 2 main script.

Session 1: Google Drive scan — finds pending orders, downloads params.json.
Session 2: DEM download — GLO-30 via OpenTopography, gdal_fillnodata via QGIS.

Run: python acquire.py
"""

import os
import sys
import json
import argparse
from eea39_bbox import is_in_eea39
from dem_download import download_glo30, run_fillnodata
from glo10_download import download_glo10

SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_COMPLETE = os.path.join(SETUP_DIR, "setup_complete.txt")
LOCAL_ORDERS_ROOT = r"E:\TerrainTool\orders"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


# ── Startup check ─────────────────────────────────────────────────────────────

if not os.path.isfile(SETUP_COMPLETE):
    print("ERROR: setup_complete.txt not found.")
    print("Run setup.py first:  python setup.py")
    sys.exit(1)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}")
    print("Run setup.py first:  python setup.py")
    sys.exit(1)


# ── Drive helpers ─────────────────────────────────────────────────────────────

def auth_drive():
    """Authenticate with service account and return Drive API client."""
    key_path = os.environ.get("GDRIVE_KEY_PATH", "")
    if not key_path:
        print("ERROR: GDRIVE_KEY_PATH environment variable is not set.")
        print("Run setup.py to configure it.")
        sys.exit(1)
    if not os.path.isfile(key_path):
        print(f"ERROR: Service account key file not found: {key_path}")
        print("Check GDRIVE_KEY_PATH points to a valid JSON key file.")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_subfolders(service, parent_id, drive_id):
    """Return list of (name, id) for all subfolders of parent_id."""
    results = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageSize=100,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="drive",
            driveId=drive_id,
        ).execute()
        results.extend((f["name"], f["id"]) for f in resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def find_params_json(service, folder_id, drive_id):
    """Return file ID of params.json in folder_id, or None if absent."""
    resp = service.files().list(
        q=f"'{folder_id}' in parents and name='params.json' and trashed=false",
        fields="files(id, name)",
        pageSize=5,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        corpora="drive",
        driveId=drive_id,
    ).execute()
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def download_file(service, file_id, dest_path):
    """Download a Drive file by ID to dest_path."""
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


# ── Session 2 helper ──────────────────────────────────────────────────────────

def read_params(path):
    """Load params.json and return as dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Module 2 — acquire.py")
    parser.add_argument(
        "--sync-only",
        action="store_true",
        default=False,
        help="Download params.json only — skip DEM download",
    )
    parser.add_argument(
        "--order",
        default=None,
        help="Process a single order by order number (folder name on Drive). If not set, all pending orders are processed.",
    )
    args = parser.parse_args()
    sync_only = args.sync_only
    order_filter = args.order

    print("Module 2 — acquire.py")
    print("=" * 50)

    if sync_only:
        print("Running in sync-only mode — skipping DEM download")

    # Read Shared Drive ID
    drive_id = os.environ.get("GDRIVE_ORDERS_DRIVE_ID", "")
    if not drive_id:
        print("ERROR: GDRIVE_ORDERS_DRIVE_ID environment variable is not set.")
        print("Run setup.py to configure it.")
        sys.exit(1)

    # Authenticate
    print("\nConnecting to Google Drive...")
    service = auth_drive()
    print("  Authenticated OK")

    # The Shared Drive root IS the orders folder — order subfolders live directly
    # inside it, so the drive ID itself is the parent ID to scan.
    orders_folder_id = drive_id
    print(f"  Connected to Shared Drive (id: {orders_folder_id})")

    # List subfolders
    subfolders = list_subfolders(service, orders_folder_id, drive_id)
    print(f"  Found {len(subfolders)} subfolders in 'orders'")

    # If --order is set, filter to that one order only
    if order_filter:
        subfolders = [(name, fid) for name, fid in subfolders if name == order_filter]
        if not subfolders:
            print(f"ERROR: Order {order_filter} not found on Drive.")
            sys.exit(1)
        print(f"  Filtered to order: {order_filter}")

    if not subfolders:
        print("\nNo order folders found on Drive. Nothing to do.")
        return

    # Classify each order
    pending = []       # (order_number, params_file_id)
    skipped_no_params = []
    skipped_already_local = []

    for order_number, folder_id in subfolders:
        params_id = find_params_json(service, folder_id, drive_id)
        if params_id is None:
            skipped_no_params.append(order_number)
            continue

        raw_dem_path = os.path.join(LOCAL_ORDERS_ROOT, order_number, "raw_dem.tif")
        if os.path.isfile(raw_dem_path):
            skipped_already_local.append(order_number)
            continue

        pending.append((order_number, params_id))

    # Download params.json for pending orders
    downloaded = []
    failed = []

    if pending:
        print(f"\nDownloading params.json for {len(pending)} pending order(s)...")
        for order_number, params_id in pending:
            dest = os.path.join(LOCAL_ORDERS_ROOT, order_number, "params.json")
            try:
                download_file(service, params_id, dest)
                print(f"  [{order_number}] params.json -> {dest}")
                downloaded.append(order_number)
            except Exception as e:
                print(f"  [{order_number}] FAILED to download params.json: {e}")
                failed.append(order_number)

    # ── Session 2: DEM download ────────────────────────────────────────────────
    # Skipped entirely when --sync-only is set.

    dem_ok = []
    dem_failed = []

    if downloaded and not sync_only:
        print(f"\nDownloading DEM for {len(downloaded)} order(s)...")
        for order_number in downloaded:
            params_path = os.path.join(LOCAL_ORDERS_ROOT, order_number, "params.json")
            try:
                params = read_params(params_path)
            except Exception as e:
                print(f"  [{order_number}] ERROR: Could not read params.json — {e}")
                dem_failed.append(order_number)
                continue

            # Skip non-GLO-30 orders — handled by Module 2b (acquire_extended.py)
            if params.get("dataset", "GLO-30") != "GLO-30":
                print(f"  [{order_number}] Skipping — dataset '{params.get('dataset')}' handled by Module 2b.")
                continue

            lat = params.get("center_lat", 0.0)
            lon = params.get("center_lon", 0.0)

            # GLO-10 disabled — EEA-10 dataset requires Public Authority account on Copernicus CDSE.
            # Routing logic preserved below for future use when access is resolved.
            # in_eea, country = is_in_eea39(lat, lon)
            # area_km = params.get("area_km", 0)
            # if in_eea and area_km <= 25:
            #     print(f"  [{order_number}] European order, area_km={area_km} — using GLO-10")
            #     if not download_glo10(params, order_number):
            #         dem_failed.append(order_number)
            #         continue
            # elif not download_glo30(params, order_number):
            #     dem_failed.append(order_number)
            #     continue

            tif_path = os.path.join(LOCAL_ORDERS_ROOT, order_number, "raw_dem.tif")

            if not download_glo30(params, order_number):
                dem_failed.append(order_number)
                continue

            if not run_fillnodata(order_number, tif_path):
                dem_failed.append(order_number)
                continue

            dem_ok.append(order_number)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("SUMMARY")
    print(f"  Subfolders found on Drive            : {len(subfolders)}")
    print(f"  Skipped — no params.json on Drive    : {len(skipped_no_params)}")
    if skipped_no_params:
        for o in skipped_no_params:
            print(f"    - {o}")
    print(f"  Skipped — raw_dem.tif already local  : {len(skipped_already_local)}")
    if skipped_already_local:
        for o in skipped_already_local:
            print(f"    - {o}")
    if failed:
        print(f"  ERRORS — params.json download failed : {len(failed)}")
        for o in failed:
            print(f"    - {o}")

    if sync_only:
        # Sync-only mode: show params.json download count, skip DEM lines
        print(f"  params.json downloaded               : {len(downloaded)}")
        if downloaded:
            for o in downloaded:
                print(f"    - {o}")
        if not pending:
            print("\nNo pending orders found.")
        else:
            print(f"\nDone. {len(downloaded)} params.json downloaded, {len(failed)} error(s).")
    else:
        # Full run: show DEM results
        print(f"  DEM downloaded OK                    : {len(dem_ok)}")
        if dem_ok:
            for o in dem_ok:
                print(f"    - {o}")
        if dem_failed:
            print(f"  ERRORS — DEM download failed         : {len(dem_failed)}")
            for o in dem_failed:
                print(f"    - {o}")

        if not pending:
            print("\nNo pending orders found.")
        else:
            total_ok = len(dem_ok)
            total_err = len(failed) + len(dem_failed)
            print(f"\nDone. {total_ok} order(s) complete, {total_err} error(s).")


if __name__ == "__main__":
    main()
