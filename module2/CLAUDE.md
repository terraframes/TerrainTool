# Module 2 — DEM Data Acquisition

**STATUS: COMPLETE — but requires fix before use (Shared Drive compatibility).**

## ⚠ Known Issue — Must Fix Before Running

acquire.py was written assuming a regular My Drive folder.
Orders now live in a Shared Drive. The following changes are needed:

All service.files().list() and related calls must add:
- supportsAllDrives=True
- includeItemsFromAllDrives=True
- driveId=<from GDRIVE_ORDERS_DRIVE_ID env var>
- corpora='drive'

Also add GDRIVE_ORDERS_DRIVE_ID to env var reads at startup.
Do a targeted fix — do not rebuild acquire.py from scratch.

## Main Script

`acquire.py` — run this to process all pending orders.

## CRITICAL RULES

- Never import osgeo directly. All GDAL calls via QGIS Python subprocess.
- Never write raw_dem.tif to Google Drive. Local only.
- Print clear plain-English error messages. Never fail silently.

## QGIS Python Executable

```
C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat
```

## Credentials & Services

- Google Cloud project: terraintool
- Service account: terraintool-orders@terraintool.iam.gserviceaccount.com
- Credentials: E:\TerrainTool\credentials\gdrive_key.json
- Shared Drive: 'orders' — ID from GDRIVE_ORDERS_DRIVE_ID env var
- Env vars: GDRIVE_KEY_PATH, OPENTOPO_API_KEY, CDSE_S3_KEY, CDSE_S3_SECRET, GDRIVE_ORDERS_DRIVE_ID

⚠ Copernicus S3 credentials expire. Regenerate at s3-credentials.dataspace.copernicus.eu.

## File Locations

```
Google Shared Drive:  orders/{order_number}/params.json
Local:                E:\TerrainTool\orders\{order_number}\  (raw_dem.tif, etc.)
```

## Pending Detection

params.json on Shared Drive AND raw_dem.tif absent locally.

## Dataset

All orders use GLO-30 via OpenTopography. eea39_bbox.py exists for future
high-res routing but its branch in acquire.py is commented out and not active.

## GLO-30 Pipeline

1. OpenTopography API → GeoTIFF download
2. Validate first 4 bytes for TIFF magic number
3. gdal_translate: COG → standard GeoTIFF
4. gdal_fillnodata: via QGIS subprocess, inline -c argument

## Operational Note

Move completed orders to orders_complete on Shared Drive manually.
Script only scans orders/ — moved orders invisible to it with no code changes.
