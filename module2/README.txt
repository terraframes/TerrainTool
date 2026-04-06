Module 2 — DEM Data Acquisition
========================================

USAGE
  python acquire.py
  Scans Google Drive for pending orders and downloads params.json locally.
  Run from E:\TerrainTool\module2\

SETUP STATUS
  Python         : 3.11.0
  google-api     : 2.149.0
  google-auth    : 2.35.0
  requests       : 2.32.3
  boto3          : 1.35.74
  QGIS bat       : OK

ENVIRONMENT VARIABLES
  GDRIVE_KEY_PATH      : SET
  OPENTOPO_API_KEY     : NOT SET (restart terminal if just set)
  CDSE_USER            : NOT SET (restart terminal if just set)
  CDSE_PASS            : NOT SET (restart terminal if just set)

NOTES
  - Google Drive service account must be shared on the 'orders' folder.
  - params.json downloaded to E:\TerrainTool\orders\{order_number}\
  - raw_dem.tif is NEVER written to Google Drive.
  - Run setup.py again if env vars change.
