"""
create_test004.py — one-shot script to create TEST_004 on Google Drive.

TEST_004: small Swedish bounding box, area_km=10, triggers GLO-10 path.
  Center: 59.35°N, 18.07°E (Stockholm outskirts)
  Bbox:   ~3 km x ~3 km (approx 10 km²)

Run once: python create_test004.py
"""

import os
import sys
import json
import io

SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_COMPLETE = os.path.join(SETUP_DIR, "setup_complete.txt")
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

if not os.path.isfile(SETUP_COMPLETE):
    print("ERROR: setup_complete.txt not found. Run setup.py first.")
    sys.exit(1)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}. Run setup.py first.")
    sys.exit(1)

# ── TEST_004 params ────────────────────────────────────────────────────────────

ORDER_NUMBER = "TEST_004"

PARAMS = {
    "order_number": ORDER_NUMBER,
    "bbox": {
        "min_lat": 59.335,
        "max_lat": 59.365,
        "min_lon": 18.045,
        "max_lon": 18.095,
    },
    "center_lat": 59.35,
    "center_lon": 18.07,
    "area_km": 10,
    "dataset": "GLO-10",
    "dem_resolution_m": 10,
    "elevation_min_m": 0.0,
    "elevation_max_m": 0.0,
    "min_clamp": 0.0,
    "max_clamp": 1.0,
    "gamma": 1.0,
    "displacement_scale": 0.3,
    "print_size_mm": 200,
    "base_thickness_mm": 10,
    "subdivision_level": 1024,
    "target_triangles": 1000000,
}


# ── Drive helpers ──────────────────────────────────────────────────────────────

def auth_drive():
    key_path = os.environ.get("GDRIVE_KEY_PATH", "")
    if not key_path or not os.path.isfile(key_path):
        print(f"ERROR: GDRIVE_KEY_PATH not set or file missing: {key_path}")
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def find_orders_folder(service):
    resp = service.files().list(
        q="name='orders' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=5,
    ).execute()
    folders = resp.get("files", [])
    if not folders:
        print("ERROR: No folder named 'orders' found on Drive.")
        print("  Create it and share with the service account.")
        sys.exit(1)
    return folders[0]["id"]


def get_or_create_subfolder(service, parent_id, name):
    """Return existing subfolder ID or create it."""
    resp = service.files().list(
        q=(f"'{parent_id}' in parents and name='{name}' "
           "and mimeType='application/vnd.google-apps.folder' and trashed=false"),
        fields="files(id, name)",
        pageSize=5,
    ).execute()
    existing = resp.get("files", [])
    if existing:
        print(f"  Folder '{name}' already exists on Drive (id: {existing[0]['id']})")
        return existing[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]}
    folder = service.files().create(body=meta, fields="id").execute()
    print(f"  Created folder '{name}' on Drive (id: {folder['id']})")
    return folder["id"]


def upload_params(service, folder_id, params_dict):
    """Upload params.json to folder_id, overwriting any existing file."""
    # Delete existing params.json if present
    resp = service.files().list(
        q=f"'{folder_id}' in parents and name='params.json' and trashed=false",
        fields="files(id)",
        pageSize=5,
    ).execute()
    for f in resp.get("files", []):
        service.files().delete(fileId=f["id"]).execute()
        print(f"  Deleted existing params.json (id: {f['id']})")

    content = json.dumps(params_dict, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")
    meta = {"name": "params.json", "parents": [folder_id]}
    result = service.files().create(body=meta, media_body=media, fields="id").execute()
    print(f"  Uploaded params.json (id: {result['id']})")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Creating {ORDER_NUMBER} on Google Drive...")
    print(f"  Center: {PARAMS['center_lat']}°N, {PARAMS['center_lon']}°E (Sweden)")
    print(f"  Area:   {PARAMS['area_km']} km²  →  triggers GLO-10 path")

    service = auth_drive()
    print("  Drive authenticated OK")

    orders_id = find_orders_folder(service)
    print(f"  Found 'orders' folder (id: {orders_id})")

    order_folder_id = get_or_create_subfolder(service, orders_id, ORDER_NUMBER)
    upload_params(service, order_folder_id, PARAMS)

    print(f"\nDone. {ORDER_NUMBER} is live on Drive.")
    print("Run acquire.py to download the GLO-10 DEM.")


if __name__ == "__main__":
    main()
