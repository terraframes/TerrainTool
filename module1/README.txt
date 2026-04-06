Module 1 Stage 2 — Shopify Webhook Receiver
=============================================

USAGE
  python webhook.py
  Listens on http://localhost:5000/webhook for Shopify orders/paid webhooks.
  For local testing use ngrok to expose the port, then set the URL in Shopify.

  python test_webhook.py
  Sends a fake Shopify payload to localhost:5000 for testing without Shopify.

CLOUD DEPLOYMENT NOTE
  On Railway/Render, set GDRIVE_KEY_JSON (full service account JSON string).
  GDRIVE_KEY_PATH is for local use only and does not need to be set in the cloud.

SETUP STATUS
  Python                    : 3.11.0
  flask                     : 3.0.3
  google-api-python-client  : 2.149.0
  google-auth               : 2.35.0
  requests                  : 2.32.3

ENVIRONMENT VARIABLES
  GDRIVE_KEY_PATH      : SET
  MAPBOX_TOKEN         : SET
  GDRIVE_ORDERS_DRIVE_ID : SET

NOTES
  - Google Drive service account must have write access to the 'orders' folder.
  - params.json is written to Drive: orders/{order_number}/params.json
  - order.txt is written locally: E:\TerrainTool\orders\{order_number}\order.txt
  - Drive writes are async — the 200 response is never delayed.
  - Run setup.py again if env vars change.
