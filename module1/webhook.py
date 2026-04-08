"""
Module 1 Stage 2 — Shopify orders/paid webhook receiver.

Receives POST /webhook, responds 200 immediately, then asynchronously:
  - Writes params.json to Google Drive orders/{order_number}/
  - Writes order.txt locally to E:\TerrainTool\orders\{order_number}\
  - Logs the Mapbox Static Images URL for the order confirmation email
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ORDERS_DIR = r"E:\TerrainTool\orders"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


# ── Drive helpers ─────────────────────────────────────────────────────────────

def get_drive_creds():
    """
    Return Drive credentials.
    MODE A (cloud): GDRIVE_KEY_JSON env var — full service account JSON string.
    MODE B (local): GDRIVE_KEY_PATH env var — path to service account JSON file.
    Returns None if neither is set.
    """
    json_str = os.environ.get("GDRIVE_KEY_JSON", "").strip()
    if json_str:
        try:
            info = json.loads(json_str)
            return Credentials.from_service_account_info(info, scopes=[DRIVE_SCOPE])
        except Exception as e:
            log.error("Failed to parse GDRIVE_KEY_JSON — %s", e)
            # fall through to MODE B

    key_path = os.environ.get("GDRIVE_KEY_PATH", "").strip()
    if key_path:
        try:
            return Credentials.from_service_account_file(key_path, scopes=[DRIVE_SCOPE])
        except Exception as e:
            log.error("Failed to load GDRIVE_KEY_PATH '%s' — %s", key_path, e)
            return None

    return None


def find_or_create_folder(service, name, parent_id=None):
    """Find a Drive folder by name (and optional parent), or create it."""
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        f" and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
    q=query,
    fields="files(id)",
    supportsAllDrives=True,
    includeItemsFromAllDrives=True,
    driveId=parent_id,
    corpora="drive"
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id",
        supportsAllDrives=True).execute()
    return folder["id"]


def write_to_drive(order_number, params):
    """Write params.json to Drive orders/{order_number}/. Overwrites if exists."""
    try:
        creds = get_drive_creds()
        if creds is None:
            log.error(
                "Order %s: cannot write to Drive — "
                "neither GDRIVE_KEY_JSON nor GDRIVE_KEY_PATH is set.",
                order_number,
            )
            return

        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        orders_id = os.environ.get("GDRIVE_ORDERS_DRIVE_ID", "").strip()
        if not orders_id:
            log.error("Order %s: GDRIVE_ORDERS_DRIVE_ID env var not set — cannot write to Drive.", order_number
            )
            return
    
        order_folder_id = find_or_create_folder(service, order_number, parent_id=orders_id)

        # Check for existing params.json to overwrite
        query = f"name='params.json' and '{order_folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id)", 
            supportsAllDrives=True, 
            includeItemsFromAllDrives=True).execute()
        existing = results.get("files", [])

        content = json.dumps(params, indent=2).encode("utf-8")
        media = MediaInMemoryUpload(content, mimetype="application/json")

        if existing:
            file = service.files().update(
                fileId=existing[0]["id"], media_body=media, fields="id",
                supportsAllDrives=True).execute()
            log.info("Order %s: params.json overwritten on Drive (file ID: %s)", order_number, file["id"])
        else:
            meta = {"name": "params.json", "parents": [order_folder_id]}
            file = service.files().create(body=meta, media_body=media, fields="id",
                supportsAllDrives=True).execute()
            log.info("Order %s: params.json created on Drive (file ID: %s)", order_number, file["id"])

    except Exception as e:
        log.error("Order %s: Drive write failed — %s", order_number, e)


# ── Local file helpers ────────────────────────────────────────────────────────

def write_order_txt(order_number, params):
    """Write a plain-text order summary locally (no PII)."""
    folder = os.path.join(ORDERS_DIR, order_number)
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "order.txt")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        bbox = params["bbox"]
        lines = [
            f"Order: {order_number}",
            f"Date: {now}",
            f"Area: {params['area_km']} km",
            f"Dataset: {params['dataset']}",
            f"BBox: N{bbox['max_lat']} S{bbox['min_lat']} E{bbox['max_lon']} W{bbox['min_lon']}",
            f"Center: {params['center_lat']}, {params['center_lon']}",
        ]
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        log.info("Order %s: order.txt written to %s", order_number, path)
    except Exception as e:
        log.error("Order %s: failed to write order.txt — %s", order_number, e)


# ── Background task ───────────────────────────────────────────────────────────

def process_order(order_number, params):
    """Runs in a background thread after 200 is sent."""
    mapbox_token = os.environ.get("MAPBOX_TOKEN", "")
    center_lon = params["center_lon"]
    center_lat = params["center_lat"]
    mapbox_url = (
        f"https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/static/"
        f"{center_lon},{center_lat},8/600x400"
        f"?access_token={mapbox_token}"
    )
    log.info("Order %s: Mapbox Static URL — %s", order_number, mapbox_url)

    write_order_txt(order_number, params)
    write_to_drive(order_number, params)


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    # Parse payload — never crash on malformed input
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}

    order_number_raw = payload.get("order_number")
    if order_number_raw is None:
        log.error("Webhook received with no order_number field — ignoring payload.")
        return jsonify({"status": "ok"}), 200

    order_number = str(order_number_raw)

    # Extract line item properties
    try:
        properties = payload["line_items"][0]["properties"]
        props = {p["name"]: p["value"] for p in properties}
    except (KeyError, IndexError, TypeError):
        log.error("Order %s: could not read line_items[0].properties.", order_number)
        return jsonify({"status": "ok"}), 200

    # Validate required fields
    required = ["min_lat", "max_lat", "min_lon", "max_lon", "area_km"]
    missing = [k for k in required if k not in props]
    if missing:
        log.error("Order %s: missing required line item properties: %s", order_number, missing)
        return jsonify({"status": "ok"}), 200

    # Parse numeric values
    dataset = props.get("dataset", "GLO-30")
    try:
        min_lat = float(props["min_lat"])
        max_lat = float(props["max_lat"])
        min_lon = float(props["min_lon"])
        max_lon = float(props["max_lon"])
        area_km = float(props["area_km"])
    except (ValueError, TypeError) as e:
        log.error("Order %s: failed to parse numeric properties — %s", order_number, e)
        return jsonify({"status": "ok"}), 200

    # Build full params.json
    params = {
        "order_number": order_number,
        "bbox": {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
        },
        "center_lat": (min_lat + max_lat) / 2,
        "center_lon": (min_lon + max_lon) / 2,
        "area_km": area_km,
        "dataset": dataset,
        "dem_resolution_m": 30,
        "elevation_min_m": 0.0,
        "elevation_max_m": 0.0,
        "min_clamp": 0.0,
        "max_clamp": 1.0,
        "gamma": 1.4,
        "displacement_scale": 0.3,
        "print_size_mm": 200,
        "base_thickness_mm": 10,
        "subdivision_level": 1024,
        "target_triangles": 1000000,
    }

    # Respond 200 immediately, process in background
    t = threading.Thread(target=process_order, args=(order_number, params), daemon=True)
    t.start()

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
