# Module 2b — Extended Dataset Acquisition

**STATUS: COMPLETE. Faroe Islands end-to-end tested.**

## Location

`E:\TerrainTool\module2b\` — alongside Module 2, not inside it.

## Purpose

High-resolution dataset acquisition for specific regions.
Module 2 (GLO-30) skips non-GLO-30 orders via a four-line filter; this module picks them up.

## Files

```
module2b\
  local_clip.py         clips source DEM to bbox, reprojects, runs fillnodata
  acquire_extended.py   mirrors acquire.py structure, routes non-GLO-30 orders
  setup.py / requirements.txt / README.txt
```

## Datasets Registry

`E:\TerrainTool\datasets\local_datasets.json` — maps dataset keys to paths and metadata.

Current entry: **FO-DEM**
```json
{
  "FO-DEM": {
    "path": "E:\\TerrainTool\\datasets\\faroe_islands\\FO_DSM_2015_FOTM_2M.tif",
    "coverage": "E:\\TerrainTool\\datasets\\faroe_islands\\faroe_islands_coverage.geojson",
    "resolution_m": 2,
    "epsg": 5316,
    "nodata": 3.4e+38,
    "type": "local_raster",
    "dsm": true
  }
}
```

## Faroe Islands DEM

Source: FO_DSM_2015_FOTM_2M.tif — 2m, DSM, EPSG:5316, nodata 3.4e+38, 1.3GB, single file.
Coverage: faroe_islands_coverage.geojson — manually drawn in QGIS, EPSG:4326.
Test: TEST_FO_001 passed end-to-end. raw_dem.tif verified in QGIS, Blender preview correct.

## local_clip.py — What It Does

1. Read bbox from params.json
2. Look up dataset in local_datasets.json using params.json dataset field
3. gdalwarp via QGIS subprocess: reproject to EPSG:4326, crop to bbox, float32
   — correct nodata handling (3.4e+38 → flagged properly, dstNodata=-9999)
4. gdal_fillnodata via QGIS subprocess (imports from Module 2's dem_download.py)
5. Write raw_dem.tif to local order folder

All GDAL via QGIS Python subprocess: C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat
Never import osgeo directly.

## acquire_extended.py — What It Does

- Scans Drive for pending orders where dataset != GLO-30
- Checks local_datasets.json to find the right handler
- Calls local_clip.py for local raster datasets
- Writes processing_status: "ready" to params.json on success

## Integration (all complete)

- Module 2 acquire.py: four-line filter skips non-GLO-30 orders
- Module 3 LoadOrder: blocks if processing_status is 'pending_lidar_review'
  or 'needs_manual_processing' — treats absent or 'ready' as green light
- Operator tool: Download DEM routes to acquire_extended.py for non-GLO-30

## Operator Tool Routing

- GLO-30 orders → acquire.py --order {name}
- Non-GLO-30 orders → acquire_extended.py --order {name}
- 'ready' status shows in orders tab and enables Open in Blender

## Next: Lantmäteriet LiDAR

Laserdata Skog — CC0, free via FTP. After widget coverage polygon system is built.
Will require: tile download, mandatory QGIS point cloud review, lidar_review.py script.
