"""
acquire_extended.py — Module 2b main script.
Scans Google Drive for pending orders where dataset != "GLO-30".
GLO-30 orders belong to Module 2 and are skipped here.
Run: python acquire_extended.py
"""

import os
import sys
import json
import argparse

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
LOCAL_ORDERS_ROOT = r"E:\TerrainTool\orders"
QGIS_PYTHON = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"
LOCAL_DATASETS_JSON = r"E:\TerrainTool\datasets\local_datasets.json"
SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_COMPLETE = os.path.join(SETUP_DIR, "setup_complete.txt")


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


# ── Drive helpers (copied from Module 2 acquire.py) ───────────────────────────

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
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=DRIVE_SCOPES)
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


def read_params(path):
    """Load params.json and return as dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── New helpers ───────────────────────────────────────────────────────────────

def update_processing_status(order_number, status):
    """Set params["processing_status"] in local params.json. Signals Module 3 the order is ready."""
    path = os.path.join(LOCAL_ORDERS_ROOT, order_number, "params.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            params = json.load(f)
        params["processing_status"] = status
        with open(path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)
        print(f"  [{order_number}] processing_status set to '{status}'.")
    except Exception as e:
        print(f"  [{order_number}] WARNING: Could not update processing_status — {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Module 2b — acquire_extended.py")
    parser.add_argument("--sync-only", action="store_true", default=False,
                        help="Download params.json only — skip DEM processing")
    parser.add_argument("--order", default=None,
                        help="Process a single order by order number (folder name on Drive).")
    args = parser.parse_args()
    sync_only = args.sync_only
    order_filter = args.order

    print("Module 2b — acquire_extended.py")
    print("=" * 50)
    if sync_only:
        print("Running in sync-only mode — skipping DEM processing")

    drive_id = os.environ.get("GDRIVE_ORDERS_DRIVE_ID", "")
    if not drive_id:
        print("ERROR: GDRIVE_ORDERS_DRIVE_ID environment variable is not set.")
        print("Run setup.py to configure it.")
        sys.exit(1)

    print("\nConnecting to Google Drive...")
    service = auth_drive()
    print("  Authenticated OK")
    print(f"  Connected to Shared Drive (id: {drive_id})")

    subfolders = list_subfolders(service, drive_id, drive_id)
    print(f"  Found {len(subfolders)} subfolders in 'orders'")

    if order_filter:
        subfolders = [(name, fid) for name, fid in subfolders if name == order_filter]
        if not subfolders:
            print(f"ERROR: Order {order_filter} not found on Drive.")
            sys.exit(1)
        print(f"  Filtered to order: {order_filter}")

    if not subfolders:
        print("\nNo order folders found on Drive. Nothing to do.")
        return

    # ── Classify orders ───────────────────────────────────────────────────────
    # Download params.json for each order that passes the pending check,
    # then inspect the dataset field. GLO-30 belongs to Module 2.

    pending = []                # (order_number, params_dict)
    skipped_no_params = []
    skipped_already_local = []
    skipped_glo30 = []          # dataset == "GLO-30" — Module 2 handles these
    download_failed = []

    print(f"\nClassifying {len(subfolders)} order(s)...")
    for order_number, folder_id in subfolders:
        params_id = find_params_json(service, folder_id, drive_id)
        if params_id is None:
            skipped_no_params.append(order_number)
            continue

        raw_dem_path = os.path.join(LOCAL_ORDERS_ROOT, order_number, "raw_dem.tif")
        if os.path.isfile(raw_dem_path):
            skipped_already_local.append(order_number)
            continue

        # Must download params.json now to read the dataset field for routing
        dest = os.path.join(LOCAL_ORDERS_ROOT, order_number, "params.json")
        try:
            download_file(service, params_id, dest)
        except Exception as e:
            print(f"  [{order_number}] FAILED to download params.json: {e}")
            download_failed.append(order_number)
            continue

        params = read_params(dest)
        dataset = params.get("dataset", "GLO-30")

        if dataset == "GLO-30":
            skipped_glo30.append(order_number)
            continue

        pending.append((order_number, params))
        print(f"  [{order_number}] Pending — dataset: {dataset}")

    # ── Sync-only: stop after classification ──────────────────────────────────

    if sync_only:
        synced = [o for o, _ in pending]
        print("\n" + "=" * 50)
        print("SUMMARY (sync-only)")
        print(f"  Subfolders found on Drive            : {len(subfolders)}")
        print(f"  Skipped — no params.json on Drive    : {len(skipped_no_params)}")
        print(f"  Skipped — raw_dem.tif already local  : {len(skipped_already_local)}")
        print(f"  Skipped — GLO-30 (Module 2 handles)  : {len(skipped_glo30)}")
        if download_failed:
            print(f"  ERRORS — params.json download failed : {len(download_failed)}")
        print(f"  params.json downloaded               : {len(synced)}")
        for o in synced:
            print(f"    - {o}")
        msg = f"Done. {len(synced)} params.json downloaded." if pending else "No non-GLO-30 pending orders found."
        print(f"\n{msg}")
        return

    # ── DEM processing ────────────────────────────────────────────────────────
    # Route each pending order to the correct handler based on its dataset field.

    dem_ok = []
    dem_failed = []

    if pending:
        print(f"\nProcessing DEM for {len(pending)} order(s)...")

        if not os.path.isfile(LOCAL_DATASETS_JSON):
            print(f"ERROR: local_datasets.json not found at: {LOCAL_DATASETS_JSON}")
            sys.exit(1)
        with open(LOCAL_DATASETS_JSON, "r", encoding="utf-8") as f:
            local_datasets = json.load(f)

        # Import clip_local_dem from this same module2b folder
        sys.path.insert(0, SETUP_DIR)
        from local_clip import clip_local_dem  # noqa: E402

        for order_number, params in pending:
            dataset = params.get("dataset", "")
            if dataset in local_datasets:
                # Local raster dataset — clip source DEM to bbox
                print(f"\n  [{order_number}] Routing to local_clip (dataset: {dataset})")
                if clip_local_dem(params, order_number):
                    update_processing_status(order_number, "ready")
                    dem_ok.append(order_number)
                else:
                    dem_failed.append(order_number)
            else:
                # Dataset key not in registry — no handler implemented yet
                print(f"  [{order_number}] ERROR: Dataset '{dataset}' is not yet implemented in Module 2b.")
                print(f"  [{order_number}]   Known local datasets: {list(local_datasets.keys())}")
                dem_failed.append(order_number)

    # ── Summary ───────────────────────────────────────────────────────────────

    print("\n" + "=" * 50)
    print("SUMMARY")
    print(f"  Subfolders found on Drive            : {len(subfolders)}")
    print(f"  Skipped — no params.json on Drive    : {len(skipped_no_params)}")
    for o in skipped_no_params:
        print(f"    - {o}")
    print(f"  Skipped — raw_dem.tif already local  : {len(skipped_already_local)}")
    for o in skipped_already_local:
        print(f"    - {o}")
    print(f"  Skipped — GLO-30 (Module 2 handles)  : {len(skipped_glo30)}")
    for o in skipped_glo30:
        print(f"    - {o}")
    if download_failed:
        print(f"  ERRORS — params.json download failed : {len(download_failed)}")
        for o in download_failed:
            print(f"    - {o}")
    print(f"  DEM processed OK                     : {len(dem_ok)}")
    for o in dem_ok:
        print(f"    - {o}")
    if dem_failed:
        print(f"  ERRORS — DEM processing failed       : {len(dem_failed)}")
        for o in dem_failed:
            print(f"    - {o}")

    if not pending:
        print("\nNo non-GLO-30 pending orders found.")
    else:
        total_err = len(download_failed) + len(dem_failed)
        print(f"\nDone. {len(dem_ok)} order(s) complete, {total_err} error(s).")


if __name__ == "__main__":
    main()
