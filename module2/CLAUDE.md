# Module 2 — DEM Data Acquisition

**STATUS: COMPLETE.**

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

## Shared Drive

All Drive API calls use:
- supportsAllDrives=True
- includeItemsFromAllDrives=True
- driveId=<GDRIVE_ORDERS_DRIVE_ID>
- corpora='drive'

The Shared Drive root IS the orders folder — driveId used directly as parent ID.
find_orders_folder() was removed; driveId is the scan root.

## Command-Line Flags

- `--sync-only`: downloads params.json files only, skips DEM download.
  Used by operator tool Refresh button.
- `--order {name}`: processes one specific order by name.
  Used by operator tool Download DEM button.

## File Locations

```
Google Shared Drive:  orders/{order_number}/params.json
Local:                E:\TerrainTool\orders\{order_number}\ (raw_dem.tif etc.)
```

## Pending Detection

params.json on Shared Drive AND raw_dem.tif absent locally.

## Dataset

All orders use GLO-30 via OpenTopography. eea39_bbox.py exists for future
high-res routing but its branch is commented out and not active.

## GLO-30 Pipeline

1. OpenTopography API → GeoTIFF download
2. Validate first 4 bytes for TIFF magic number
3. gdal_translate: COG → standard GeoTIFF
4. gdal_fillnodata: via QGIS subprocess, inline -c argument

## Files

```
acquire.py       main script — Drive auth, sync, pending detection, routing
dem_download.py  GLO-30 download and gdal_fillnodata
eea39_bbox.py    EEA-39 check — not active, preserved for future high-res routing
setup.py
requirements.txt google-api-python-client, google-auth, requests, boto3
```

## Operational Note

Move completed orders to orders_complete on Shared Drive manually.
Script only scans orders/ — moved orders invisible with no code changes.
