"""
Test script for webhook.py — sends a fake Shopify orders/paid payload.

Run webhook.py first:  python webhook.py
Then in a second terminal: python test_webhook.py
"""

import requests
import json

WEBHOOK_URL = "http://localhost:5000/webhook"

payload = {
    "order_number": 99001,
    "line_items": [
        {
            "properties": [
                {"name": "min_lat",  "value": "59.207514"},
                {"name": "max_lat",  "value": "59.432344"},
                {"name": "min_lon",  "value": "17.862776"},
                {"name": "max_lon",  "value": "18.303408"},
                {"name": "area_km",  "value": "50"},
            ]
        }
    ],
}

print(f"Sending test webhook to {WEBHOOK_URL} ...")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

try:
    response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    print(f"HTTP status: {response.status_code}")
    print(f"Body: {response.text}")
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect. Is webhook.py running on port 5000?")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out.")
