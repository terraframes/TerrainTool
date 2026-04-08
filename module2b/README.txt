Module 2b -- Extended Dataset Acquisition
==========================================

WHAT THIS MODULE DOES

Module 2b handles high-resolution DEM acquisition for orders that use a
local raster dataset instead of the standard GLO-30 (OpenTopography).

When an order's dataset field is NOT "GLO-30", Module 2 skips it.
Module 2b picks those orders up instead.

Currently supported dataset type:
  Local raster -- a GeoTIFF stored on this machine is clipped to the
  order's bounding box and reprojected to EPSG:4326. Example: the
  Faroe Islands national DSM (FO-DEM, 2m resolution).

Output is raw_dem.tif in E:\TerrainTool\orders\{order_number}\,
the same file that Module 3 expects. After a successful clip,
processing_status is set to "ready" in params.json.


HOW TO RUN SETUP

Run once per machine before using this module:

  cd E:\TerrainTool\module2b
  python setup.py

Setup will:
  - Check Python 3.11 is active
  - Install pip dependencies (google-api-python-client, google-auth, requests)
  - Verify QGIS 3.44.8 is installed
  - Check E:\TerrainTool\datasets\local_datasets.json exists
  - Prompt for GDRIVE_KEY_PATH and GDRIVE_ORDERS_DRIVE_ID if not set
  - Write setup_complete.txt on success

If setup prompts for env vars, restart your terminal afterwards so the
new values take effect, then run acquire_extended.py.


HOW TO RUN

  cd E:\TerrainTool\module2b
  python acquire_extended.py

Full run: scans Google Drive for pending non-GLO-30 orders, downloads
params.json, clips the source DEM to the order bbox, runs void-fill,
and writes raw_dem.tif locally.

FLAGS

  --sync-only
      Download params.json for pending orders but skip DEM processing.
      Use this to check what non-GLO-30 orders are waiting without
      doing any heavy GDAL work. The operator tool Refresh button uses
      this flag.

  --order {order_number}
      Process a single order by name instead of all pending orders.
      The order folder must exist on Google Drive.
      Example: python acquire_extended.py --order 10042


REQUIRED ENVIRONMENT VARIABLES

  GDRIVE_KEY_PATH
      Full path to the Google Drive service account JSON key file.
      Example: E:\TerrainTool\credentials\gdrive_key.json

  GDRIVE_ORDERS_DRIVE_ID
      The ID of the Google Shared Drive that holds the orders folders.
      Find this in the Drive URL when browsing the shared drive.

Both variables are set by setup.py if not already present. Restart
your terminal after setup writes them.


ADDING A NEW LOCAL DATASET

To add a new local raster dataset (e.g. a national DEM for another country):

1. Copy the source GeoTIFF file(s) to E:\TerrainTool\datasets\{name}\

2. Author a coverage GeoJSON polygon (EPSG:4326) showing where the
   dataset covers. Save it alongside the GeoTIFF.

3. Add an entry to E:\TerrainTool\datasets\local_datasets.json:

   {
     "MY-DATASET-KEY": {
       "description": "Human-readable description",
       "files": ["E:\\TerrainTool\\datasets\\name\\file.tif"],
       "nodata_value": -9999,
       "coverage": "E:\\TerrainTool\\datasets\\name\\coverage.geojson",
       "resolution_m": 10,
       "type": "local_raster",
       "dsm": false
     }
   }

   The "files" list supports multiple GeoTIFFs -- they are merged into
   a VRT mosaic automatically before clipping.

4. When creating an order in the widget, select this dataset. Set the
   dataset field in params.json to match the key above (e.g. "MY-DATASET-KEY").

acquire_extended.py routes the order to local_clip.py automatically.


PROCESSING STATUS VALUES

After a successful DEM clip, acquire_extended.py writes
processing_status into the local params.json:

  "ready"
      DEM acquisition complete. Module 3 will process this order.

  (absent)
      Order has not been processed yet, or processing is in progress.

  "needs_manual_processing"
      Reserved for future use -- cross-border orders that require
      operator review before Module 3 can run.


HOW THIS FITS IN THE PIPELINE

  Module 1  -- customer selects map area, Shopify captures payment
  Module 2  -- handles GLO-30 orders (acquire.py)
  Module 2b -- handles non-GLO-30 orders (this module)
  Module 3  -- Blender refinement, reads raw_dem.tif
  Module 4  -- Blender displacement and STL export
