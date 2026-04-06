"""
resample.py — standalone GDAL processing script for the terrain 3D print pipeline.

DO NOT import this file into Blender. It must only be called via subprocess.run().
Blender's Python and system Python are separate — osgeo lives in system Python only.

What this script does:
  1. Fill nodata holes in the raw DEM (before anything else)
  2. Warp: reproject to EPSG:4326, crop to bounding box, resize to N×N pixels, float32
  3. Normalise: remap actual elevation range to 0.0–1.0, record real min/max metres
  4. Clamp: clip values outside [min_clamp, max_clamp]
  5. Re-normalise: remap clamped range back to 0.0–1.0 (floor is exactly 0)
  6. Gamma: apply gamma correction
  7. Save as float32 single-band GeoTIFF

On success, prints one JSON line to stdout:
  {"elevation_min_m": 0.0, "elevation_max_m": 1850.0, "status": "ok"}

On failure, prints one JSON line to stdout:
  {"status": "error", "message": "description of what went wrong"}
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

import numpy as np
from osgeo import gdal

# Tell GDAL to raise Python exceptions instead of returning error codes silently
gdal.UseExceptions()

# ---------------------------------------------------------------------------
# QGIS Python interpreter — used by any script that calls this file via subprocess
# ---------------------------------------------------------------------------
# This script must be run with QGIS's bundled Python, not system Python,
# because that is where GDAL (osgeo) is installed.
# If QGIS is installed at a different path, update this constant and qgis_config.json.

QGIS_PYTHON = r"C:\Program Files\QGIS 3.44.8\bin\python-qgis-ltr.bat"


# ---------------------------------------------------------------------------
# Step 0 — Fill nodata holes
# ---------------------------------------------------------------------------

def fill_nodata(input_path, output_path):
    """
    Copy the raw DEM and fill any nodata holes before further processing.
    Holes are filled by interpolating from nearby valid pixels.
    maxSearchDist=100 means it will search up to 100 pixels away for valid data.
    """
    src_ds = gdal.Open(input_path, gdal.GA_ReadOnly)
    if src_ds is None:
        raise RuntimeError(f"Could not open input file: {input_path}")

    # Make a full copy so we can write into it
    driver = gdal.GetDriverByName("GTiff")
    dst_ds = driver.CreateCopy(output_path, src_ds, options=["COMPRESS=LZW"])
    src_ds = None

    band = dst_ds.GetRasterBand(1)

    # maskBand=None tells GDAL to use the band's own nodata mask
    gdal.FillNodata(
        targetBand=band,
        maskBand=None,
        maxSearchDist=100,
        smoothingIterations=0,
    )

    band.FlushCache()
    dst_ds = None


# ---------------------------------------------------------------------------
# Step 1 — Warp: reproject, crop, resize
# ---------------------------------------------------------------------------

def warp(input_path, output_path, bbox, resolution):
    """
    Reproject to EPSG:4326 (standard lat/lon), crop to the bounding box,
    and resize to exactly resolution × resolution pixels.

    bbox = (min_lat, max_lat, min_lon, max_lon)
    outputBounds wants (xmin, ymin, xmax, ymax) = (min_lon, min_lat, max_lon, max_lat)

    Two-step warp: first to a padded bbox at slightly larger resolution so the
    cubic kernel always has valid source pixels on all sides, then crop back to
    the exact target bbox at the exact target resolution.
    """
    min_lat, max_lat, min_lon, max_lon = bbox

    lat_pad = (max_lat - min_lat) * 0.05
    lon_pad = (max_lon - min_lon) * 0.05
    padded_bbox = (min_lat - lat_pad, max_lat + lat_pad,
                   min_lon - lon_pad, max_lon + lon_pad)
    padded_resolution = int(resolution * 1.1)

    # Step 1 — warp to padded bbox
    padded_ds = gdal.Warp(
        "",
        input_path,
        format="MEM",
        dstSRS="EPSG:4326",
        outputBounds=(padded_bbox[2], padded_bbox[0], padded_bbox[3], padded_bbox[1]),
        width=padded_resolution,
        height=padded_resolution,
        resampleAlg="cubic",
        outputType=gdal.GDT_Float32,
        srcNodata=None,
        dstNodata=-9999.0,
    )

    if padded_ds is None:
        raise RuntimeError("gdalwarp failed (padded pass) — check that the bounding box overlaps the input DEM")

    # Step 2 — crop to exact target bbox and resolution
    result = gdal.Warp(
        output_path,
        padded_ds,
        dstSRS="EPSG:4326",
        outputBounds=(min_lon, min_lat, max_lon, max_lat),
        width=resolution,
        height=resolution,
        resampleAlg="near",
        outputType=gdal.GDT_Float32,
        srcNodata=-9999.0,
        dstNodata=-9999.0,
        creationOptions=["COMPRESS=LZW", "TILED=YES"],
    )

    padded_ds = None  # close in-memory dataset

    if result is None:
        raise RuntimeError("gdalwarp failed (crop pass) — check that the bounding box overlaps the input DEM")

    result = None  # close the dataset


# ---------------------------------------------------------------------------
# Steps 2–6 — Normalise, clamp, re-normalise, gamma, save
# ---------------------------------------------------------------------------

def process(warped_path, output_path, min_clamp, max_clamp, gamma):
    """
    Reads the warped float32 array, runs all normalisation steps, and saves
    the result as a float32 single-band GeoTIFF.

    Returns (elevation_min_m, elevation_max_m) — the real-world elevation
    range found in the data before any clamping or rescaling.
    """
    ds = gdal.Open(warped_path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Could not open warped file: {warped_path}")

    band = ds.GetRasterBand(1)
    data = band.ReadAsArray().astype(np.float32)
    nodata_val = band.GetNoDataValue()

    # Build a boolean mask of pixels that have real data
    if nodata_val is not None:
        valid = (data != np.float32(nodata_val)) & np.isfinite(data)
    else:
        valid = np.isfinite(data)

    if not np.any(valid):
        raise RuntimeError(
            "No valid pixels found in the warped DEM. "
            "Check that the bounding box actually overlaps the DEM coverage."
        )

    # ------------------------------------------------------------------
    # Edge fill — copy nearest valid row/column inward for any all-invalid edges
    # ------------------------------------------------------------------

    if not np.any(valid[-1, :]):   # last row all invalid
        data[-1, :] = data[-2, :]
    if not np.any(valid[0, :]):    # first row all invalid
        data[0, :] = data[1, :]
    if not np.any(valid[:, -1]):   # last column all invalid
        data[:, -1] = data[:, -2]
    if not np.any(valid[:, 0]):    # first column all invalid
        data[:, 0] = data[:, 1]

    # Rebuild valid mask to include the filled edge pixels
    if nodata_val is not None:
        valid = (data != np.float32(nodata_val)) & np.isfinite(data)
    else:
        valid = np.isfinite(data)

    # ------------------------------------------------------------------
    # Step 2 — Normalise to 0.0–1.0, record real elevation values
    # ------------------------------------------------------------------

    elev_min = float(data[valid].min())
    elev_max = float(data[valid].max())

    if elev_max == elev_min:
        # Completely flat terrain — treat everything as zero
        data[:] = 0.0
    else:
        data[valid] = (data[valid] - elev_min) / (elev_max - elev_min)

    # Nodata pixels become 0 (sea level equivalent) after normalisation
    data[~valid] = 0.0

    # ------------------------------------------------------------------
    # Step 3 — Clamp to [min_clamp, max_clamp]
    # ------------------------------------------------------------------

    data = np.clip(data, min_clamp, max_clamp)

    # ------------------------------------------------------------------
    # Step 4 — Re-normalise so floor is exactly 0.0
    # ------------------------------------------------------------------

    clamped_min = float(data.min())
    clamped_max = float(data.max())

    if clamped_max == clamped_min:
        # Everything clamped to the same value — flat result
        data = np.zeros_like(data)
    else:
        data = (data - clamped_min) / (clamped_max - clamped_min)

    # ------------------------------------------------------------------
    # Step 5 — Gamma correction
    # ------------------------------------------------------------------

    if gamma != 1.0:
        # Protect against any tiny negative values from floating point noise
        data = np.clip(data, 0.0, 1.0)
        data = np.power(data, 1.0 / gamma, dtype=np.float32)

    # Ensure final values are clamped to [0, 1] — no overshoots
    data = np.clip(data, 0.0, 1.0).astype(np.float32)

    # ------------------------------------------------------------------
    # Step 6 — Save as float32 single-band GeoTIFF
    # ------------------------------------------------------------------

    geo_transform = ds.GetGeoTransform()
    projection = ds.GetProjection()
    width = ds.RasterXSize
    height = ds.RasterYSize
    ds = None  # close input before writing output

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        output_path,
        width,
        height,
        1,  # single band
        gdal.GDT_Float32,
        options=["COMPRESS=LZW", "TILED=YES"],
    )

    if out_ds is None:
        raise RuntimeError(f"Could not create output file: {output_path}")

    out_ds.SetGeoTransform(geo_transform)
    out_ds.SetProjection(projection)

    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(data)
    out_band.FlushCache()
    out_ds = None

    return elev_min, elev_max


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Process a raw DEM GeoTIFF into a normalised float32 GeoTIFF."
    )
    parser.add_argument("--input",      required=True,  help="Path to raw_dem.tif")
    parser.add_argument("--output",     required=True,  help="Path to write resampled.tif")
    parser.add_argument("--bbox",       required=True,  nargs=4, type=float,
                        metavar=("MIN_LAT", "MAX_LAT", "MIN_LON", "MAX_LON"))
    parser.add_argument("--resolution", required=True,  type=int,
                        help="Output pixel size (e.g. 256 for preview, 1024 for full res)")
    parser.add_argument("--min_clamp",  default=0.0,    type=float)
    parser.add_argument("--max_clamp",  default=1.0,    type=float)
    parser.add_argument("--gamma",      default=1.0,    type=float)

    args = parser.parse_args()

    # Basic sanity checks before doing any work
    if not os.path.isfile(args.input):
        print(json.dumps({"status": "error", "message": f"Input file not found: {args.input}"}))
        sys.exit(1)

    output_dir = os.path.dirname(os.path.abspath(args.output))
    if not os.path.isdir(output_dir):
        print(json.dumps({"status": "error", "message": f"Output directory does not exist: {output_dir}"}))
        sys.exit(1)

    if args.min_clamp >= args.max_clamp:
        print(json.dumps({"status": "error", "message": "min_clamp must be less than max_clamp"}))
        sys.exit(1)

    if args.gamma <= 0:
        print(json.dumps({"status": "error", "message": "gamma must be greater than 0"}))
        sys.exit(1)

    # All intermediate files go into a temp folder that gets deleted on exit
    temp_dir = tempfile.mkdtemp(prefix="terrain_resample_")

    try:
        filled_path = os.path.join(temp_dir, "filled.tif")
        warped_path = os.path.join(temp_dir, "warped.tif")

        fill_nodata(args.input, filled_path)
        warp(filled_path, warped_path, args.bbox, args.resolution)
        elev_min, elev_max = process(warped_path, args.output, args.min_clamp, args.max_clamp, args.gamma)

        # Only one JSON line on stdout — the Blender addon reads this
        print(json.dumps({
            "elevation_min_m": round(elev_min, 2),
            "elevation_max_m": round(elev_max, 2),
            "status": "ok",
        }))

    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)

    finally:
        # Always clean up temp files, even if something went wrong
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
