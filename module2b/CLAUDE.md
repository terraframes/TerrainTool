# Module 2b — Extended Dataset Acquisition

**STATUS: COMPLETE for local_raster (FO-DEM). api_wcs, api_tiled, LiDAR pipeline not yet built.**

## Location

`E:\TerrainTool\module2b\` — alongside Module 2, not inside it.

## Files

```
module2b\
  local_clip.py         clips stored GeoTIFF to bbox, reprojects, nodata_fill branch
  acquire_extended.py   scans Drive for non-GLO-30 orders, routes to handler
  setup.py / requirements.txt / README.txt
```

## Dataset Registries

**local_datasets.json** (`E:\TerrainTool\datasets\local_datasets.json`):
local_raster entries. Fields: path, coverage, resolution_m, epsg, nodata, nodata_fill, type, dsm, priority.

**api_datasets.json** (`E:\TerrainTool\datasets\api_datasets.json`) — NOT YET CREATED:
api_wcs and api_tiled entries. Fields: endpoint/bucket, coverage, resolution_m, crs, nodata, type, dsm, priority.
Type-specific fields: `wcs_layer` for api_wcs; `stac_catalog_url` for api_tiled.

Priority integers must stay in sync between both files and the widget.

## Dataset Types

| Type | Status | Examples |
|------|--------|---------|
| local_raster | FO-DEM complete | FO-DEM, BE-merged (planned), LU (planned) |
| api_wcs | Not yet built | NL-AHN4, NO-DOM, DK-DHM |
| api_tiled | Not yet built | ArcticDEM, NZ-DSM, EN-EA |
| LiDAR pipeline | Not yet built | SE-LiDAR, US-3DEP |

## ⚠ Critical: Exact Float for nodata

FO-DEM: `3.3999999521443642e+38` — NOT `3.4e+38`.
Use `repr(nodata_value)` in all subprocess strings.

## nodata_fill Field

| Value | When | What |
|-------|------|------|
| "zero" | Coastal/island DEMs | Replace nodata with 0.0, set band nodata to 0.0 |
| "interpolate" | Land DEMs with scan gaps | Call gdal_fillnodata |

FO-DEM uses "zero". Land datasets (NL-AHN4, NO-DOM, etc.) will use "interpolate".

## ⚠ resample.py Guard

If band nodata == 0.0, skip gdal.FillNodata entirely. 0.0 = valid sea level.

## local_clip.py Pipeline

1. Read bbox from params.json, look up dataset in local_datasets.json
2. gdalwarp via QGIS subprocess: reproject to EPSG:4326, crop to bbox, float32
   srcNodata=repr(nodata_value), dstNodata=-9999.0
3. Branch on nodata_fill: "zero" → replace with 0.0; "interpolate" → run_fillnodata
4. Write raw_dem.tif, set processing_status: "ready"

All GDAL via: `C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat`

## Priority & Selection

iterate all datasets in priority order → use first one whose coverage polygon fully contains the order bbox.
Cross-border (no single dataset covers bbox): flag needs_manual_processing, save raw_dem_primary.tif + raw_dem_secondary.tif. Operator merges → raw_dem.tif. Next Refresh promotes status.

## Next: NL-AHN4 (first api_wcs)

Create api_datasets.json, add NL-AHN4 entry:
- Endpoint: https://service.pdok.nl/rws/ahn/wcs/v1_0
- Coverage: dsm_05m, EPSG:28992, nodata 3.4028235e+38, CC-0
- Reproject order bbox to EPSG:28992 before WCS request
