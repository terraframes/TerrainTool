# Module 2b — Extended Dataset Acquisition

**STATUS: FO-DEM (local_raster) + ArcticDEM (api_tiled) complete.**

## Location

`E:\TerrainTool\module2b\` — alongside Module 2, not inside it.

## Files

```
module2b\
  local_clip.py         stored GeoTIFF → bbox clip, reproject, nodata_fill branch
  acquire_tiled.py      api_tiled handler: STAC query, vsicurl VRT, gdalwarp
  acquire_extended.py   loads both registries, merges, routes by type
  setup.py / requirements.txt / README.txt  (pystac-client added)
```

## Registry Files

**local_datasets.json** (`E:\TerrainTool\datasets\`): local_raster entries.
Fields: path, coverage, resolution_m, epsg, nodata, nodata_fill, type, dsm, priority.

**api_datasets.json** (`E:\TerrainTool\datasets\`): api_wcs and api_tiled entries.
Fields: endpoint/bucket, coverage, resolution_m, crs, nodata, nodata_fill, type, dsm, priority.
Type-specific: `wcs_layer` for api_wcs; `stac_api_url`, `stac_collection`, `stac_asset_key` for api_tiled.

acquire_extended.py loads both, merges (local_datasets wins on collision), routes by ds_entry["type"].

## Dataset Status

| Type | Dataset | Status |
|------|---------|--------|
| local_raster | FO-DEM | Complete |
| api_tiled | ArcticDEM | Complete |
| api_wcs | NL-AHN4, NO-DOM, DK-DHM | Planned |
| api_tiled | NZ-DSM, EN-EA | Planned |
| local_raster | BE-merged, LU | Planned (offline QGIS) |
| LiDAR pipeline | SE-LiDAR, US-3DEP | Planned |

## ⚠ Critical nodata Rules

- FO-DEM exact float: `3.3999999521443642e+38` — NOT `3.4e+38`
- Use `repr(nodata_value)` in all subprocess strings
- `nodata_fill: "zero"` for coastal/island DEMs (ocean = 0.0 = sea level)
- `nodata_fill: "interpolate"` for land DEMs (ArcticDEM, NL-AHN4, etc.)
- resample.py guard: if band nodata == 0.0, skip gdal.FillNodata entirely

## acquire_tiled.py — ArcticDEM Pattern

```
1. Bbox + 5% padding
2. pystac_client.Client.open(stac_api_url).search(collections, bbox)
3. Get dem asset href → s3:// → https:// → /vsicurl/ prefix
4. Multiple tiles: gdal.BuildVRT (capital V — BuildVrt does not exist)
5. gdalwarp via QGIS subprocess with GDAL_HTTP_UNSAFESSL=YES,
   CPL_VSIL_CURL_ALLOWED_EXTENSIONS=.tif,
   GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR,
   CPL_VSIL_CURL_USE_CACHE=YES
6. Output float32 raw_dem.tif, delete VRT
```

vsicurl fetches only byte ranges covering the bbox (~5–10MB) instead of full tiles (~500MB–1GB).

## ArcticDEM Registry Entry

```json
{
  "ArcticDEM": {
    "stac_api_url": "https://stac.pgc.umn.edu/api/v1/",
    "stac_collection": "arcticdem-mosaics-v4.1-2m",
    "stac_asset_key": "dem",
    "coverage": "E:\\TerrainTool\\datasets\\arcticdem\\arcticdem_coverage.geojson",
    "resolution_m": 2, "epsg": 3413, "nodata": -9999.0,
    "nodata_fill": "interpolate", "type": "api_tiled", "dsm": true, "priority": 1
  }
}
```

## Priority & Selection

Iterate both registries in priority order (ascending integer). Use first dataset whose coverage polygon fully contains the order bbox. GLO-30 (priority 99) always the fallback.

Cross-border: flag needs_manual_processing, save raw_dem_primary.tif + raw_dem_secondary.tif. Operator merges → raw_dem.tif. Refresh promotes.

## Next: NL-AHN4 (first api_wcs)

Add to api_datasets.json:
- Endpoint: https://service.pdok.nl/rws/ahn/wcs/v1_0
- Coverage: dsm_05m, EPSG:28992, nodata 3.4028235e+38 (set explicitly — not auto-detected), CC-0
- Reproject order bbox to EPSG:28992 before WCS request
