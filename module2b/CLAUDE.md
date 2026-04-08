# Module 2b — Extended Dataset Acquisition

**STATUS: COMPLETE. Real order end-to-end confirmed with clean terrain.**

## Location

`E:\TerrainTool\module2b\` — alongside Module 2, not inside it.

## Files

```
module2b\
  local_clip.py         clips source DEM, reprojects, branches on nodata_fill
  acquire_extended.py   scans Drive for non-GLO-30 orders, routes to handler
  setup.py / requirements.txt / README.txt
```

## Datasets Registry

`E:\TerrainTool\datasets\local_datasets.json`

Current entry: **FO-DEM**
```json
{
  "FO-DEM": {
    "path": "E:\\TerrainTool\\datasets\\faroe_islands\\FO_DSM_2015_FOTM_2M.tif",
    "coverage": "E:\\TerrainTool\\datasets\\faroe_islands\\faroe_islands_coverage.geojson",
    "resolution_m": 2,
    "epsg": 5316,
    "nodata": 3.3999999521443642e+38,
    "nodata_fill": "zero",
    "type": "local_raster",
    "dsm": true
  }
}
```

## ⚠ Critical: Exact Float for nodata

Use the exact value `3.3999999521443642e+38` — NOT the rounded `3.4e+38`.
Rounded value causes GDAL to fail to match nodata pixels during warp.
Use `repr(nodata_value)` in all subprocess string interpolation.

## nodata_fill Field

| Value | When to use | What it does |
|-------|-------------|--------------|
| "zero" | Island/coastal DEMs (Faroe Islands) | Replaces nodata with 0.0, sets band nodata to 0.0. Ocean = sea level. |
| "interpolate" | Land DEMs with scan gaps | Calls gdal_fillnodata via Module 2 run_fillnodata. |

FO-DEM uses "zero" — ocean areas become sea level, not interpolated guesswork.

## ⚠ resample.py Guard (in Module 3)

resample.py has a guard: if band nodata == 0.0, skip gdal.FillNodata.
Reason: 0.0 is valid sea level elevation for coastal/island DEMs.
Without this guard, fill_nodata re-interpolates the correctly zero-filled ocean
pixels, creating jagged coastline artefacts in Blender.

## local_clip.py Pipeline

1. Read bbox from params.json
2. Look up dataset in local_datasets.json (key from params.json dataset field)
3. gdalwarp via QGIS subprocess: reproject to EPSG:4326, crop to bbox, float32
   — srcNodata=repr(nodata_value) for full float precision
   — dstNodata=-9999.0
4. Branch on nodata_fill:
   - "zero": replace nodata (-9999) with 0.0, set band nodata to 0.0
   - "interpolate": call Module 2's run_fillnodata
5. Write raw_dem.tif to local order folder
6. Write processing_status: "ready" to params.json

QGIS Python: C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat
Never import osgeo directly.

## Integration

- Module 2 acquire.py: four-line filter skips non-GLO-30 orders
- Module 3 LoadOrder: blocks if processing_status is 'pending_lidar_review' or
  'needs_manual_processing' — absent or 'ready' proceeds
- Operator tool: Download DEM routes to acquire_extended.py for non-GLO-30
- webhook.py: reads dataset from Shopify line item properties, defaults to 'GLO-30'

## Future: Lantmäteriet Laserdata Skog

CC0, free via FTP. Will add nodata_fill: "interpolate" (land DEM, not coastal).
Requires tile download, mandatory QGIS point cloud review, lidar_review.py.
