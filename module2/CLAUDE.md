# Module 2 — DEM Data Acquisition

**STATUS: COMPLETE.**

## Main Script

`acquire.py` — run this to process all pending orders.

## CRITICAL RULES

- **Never import osgeo directly.** All GDAL calls via QGIS Python subprocess.
- **Never write raw_dem.tif to Google Drive.** Local only.
- **Print clear plain-English error messages. Never fail silently.**

## QGIS Python Executable

```
C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat
```

## Credentials & Services

- Google Cloud project: terraintool
- Service account: terraintool-orders@terraintool.iam.gserviceaccount.com
- Credentials: E:\TerrainTool\credentials\gdrive_key.json
- Env vars: GDRIVE_KEY_PATH, OPENTOPO_API_KEY, CDSE_S3_KEY, CDSE_S3_SECRET
- CDSE_S3_KEY and CDSE_S3_SECRET are set but currently unused (GLO-10 disabled)

⚠ Copernicus S3 credentials expire. Regenerate at s3-credentials.dataspace.copernicus.eu.
  Auth failure on any future GLO-10 work = keys need regenerating.

## Dataset Selection

**All orders currently use GLO-30 via OpenTopography regardless of location.**

GLO-10 routing logic exists in acquire.py and eea39_bbox.py but is commented out.
Reason: EEA-10 (10m DEM) requires a Public Authority Copernicus account.
Standard free accounts do not have access.

## Files

```
acquire.py       main script — Drive auth, pending detection, routing, orchestration
dem_download.py  GLO-30 download and gdal_fillnodata
eea39_bbox.py    EEA-39 check (used for routing, GLO-10 branch commented out)
setup.py         done
requirements.txt google-api-python-client, google-auth, requests, boto3 (no gdal)
```

## GLO-30 Pipeline

1. OpenTopography API → GeoTIFF download
2. Validate: check first 4 bytes for TIFF magic number
3. gdal_translate: COG → standard GeoTIFF (OpenTopography returns COG format)
4. gdal_fillnodata: via QGIS subprocess, inline -c argument

## Operational Note

Move completed orders to orders_complete Drive folder manually when volume grows.
Script only scans orders/ — moved orders invisible to it with no code changes needed.
