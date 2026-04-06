"""
acquire.py — Module 2 main script.

Session 1: Google Drive scan — finds pending orders, downloads params.json.
Session 2: DEM download — GLO-30 via OpenTopography, gdal_fillnodata via QGIS.

Run: python acquire.py
"""

import os
import sys
import json
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


def find_orders_folder(service):
    """Return the Drive file ID of the top-level 'orders' folder."""
    resp = service.files().list(
        q="name='orders' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=10,
    ).execute()
    folders = resp.get("files", [])
    if not folders:
        print("ERROR: No folder named 'orders' found on Google Drive.")
        print("Create a folder called 'orders' and share it with the service account.")
        sys.exit(1)
    if len(folders) > 1:
        print(f"WARNING: {len(folders)} folders named 'orders' found — using the first one.")
    return folders[0]["id"]


def list_subfolders(service, parent_id):
    """Return list of (name, id) for all subfolders of parent_id."""
    results = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        results.extend((f["name"], f["id"]) for f in resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def find_params_json(service, folder_id):
    """Return file ID of params.json in folder_id, or None if absent."""
    resp = service.files().list(
        q=f"'{folder_id}' in parents and name='params.json' and trashed=false",
        fields="files(id, name)",
        pageSize=5,
    ).execute()
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def download_file(service, file_id, dest_path):
    """Download a Drive file by ID to dest_path."""
    request = service.files().get_media(fileId=file_id)
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
    print("Module 2 — acquire.py")
    print("=" * 50)

    # Authenticate
    print("\nConnecting to Google Drive...")
    service = auth_drive()
    print("  Authenticated OK")

    # Find orders folder
    orders_folder_id = find_orders_folder(service)
    print(f"  Found 'orders' folder on Drive (id: {orders_folder_id})")

    # List subfolders
    subfolders = list_subfolders(service, orders_folder_id)
    print(f"  Found {len(subfolders)} subfolders in 'orders'")

    if not subfolders:
        print("\nNo order folders found on Drive. Nothing to do.")
        return

    # Classify each order
    pending = []       # (order_number, params_file_id)
    skipped_no_params = []
    skipped_already_local = []

    for order_number, folder_id in subfolders:
        params_id = find_params_json(service, folder_id)
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
                print(f"  [{order_number}] params.json → {dest}")
                downloaded.append(order_number)
            except Exception as e:
                print(f"  [{order_number}] FAILED to download params.json: {e}")
                failed.append(order_number)

    # ── Session 2: DEM download ────────────────────────────────────────────────

    dem_ok = []
    dem_failed = []

    if downloaded:
        print(f"\nDownloading DEM for {len(downloaded)} order(s)...")
        for order_number in downloaded:
            params_path = os.path.join(LOCAL_ORDERS_ROOT, order_number, "params.json")
            try:
                params = read_params(params_path)
            except Exception as e:
                print(f"  [{order_number}] ERROR: Could not read params.json — {e}")
                dem_failed.append(order_number)
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
