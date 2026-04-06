# Module 4 — Displacement & Export (Blender Addon)

**STATUS: COMPLETE. Do not rebuild. Reference this as the working baseline for Module 3.**

## What Was Built

Blender 4.5 LTS addon. N-panel under the Terrain Export tab. Two sequential buttons.
No GDAL or external Python dependencies — GeoTIFF loaded via Blender's OIIO image loader.

## Input Requirements

- Order folder containing params.json and resampled.tif
- resampled.tif: float32 single-band GeoTIFF, values nominally 0–1
  (minor overshoots handled — addon remaps actual min/max to 0–1 on load,
  prints original range to console)
- params.json fields required: subdivision_level, displacement_scale,
  target_triangles, base_thickness_mm, print_size_mm

## Step 1 — Bake Full Res

1. Plane created at 10×10 Blender units
2. UVs explicitly reset to clean 0–1 square grid BEFORE subdivision
   (Blender default post-subdivision UVs produced diagonal artefacts)
3. Subdivided to subdivision_level using 10 iterations (~2M triangles at 1024)
4. resampled.tif loaded via OIIO — extension=EXTEND, interpolation=Linear
5. Displace modifier: mid_level=0.0, strength=displacement_scale (ratio of plane width)
6. Modifier applied to real geometry
7. Decimated to target_triangles
8. displaced.obj (pre-decimate) and simplified.obj (post-decimate) written to order folder

## Step 2 — Add Base and Export

1. Perimeter vertices identified via boundary edge detection
2. Perimeter vertices kept at exact displaced Z — NOT snapped to zero
3. Perimeter loop extruded straight down along Z (clean vertical walls)
4. Bottom face capped flat
5. All vertices scaled so XY = print_size_mm (sole scaling operation)
6. Base bottom sits at Z = -base_thickness_mm (absolute, independent of terrain scale)
7. Non-manifold check — export blocked if any found
8. final.stl written to order folder

## Output Files

- displaced.obj — full res, pre-decimation, no base
- simplified.obj — decimated to ~1M triangles, no base
- final.stl — watertight, scaled to print_size_mm, flat base, print-ready

## params.json Fields This Module Reads and Writes

```json
{
  "subdivision_level": 1024,
  "displacement_scale": 0.3,
  "target_triangles": 1000000,
  "base_thickness_mm": 10,
  "print_size_mm": 200
}
```

## Known Limitations (as of completion)

- Input TIF placed manually — Module 3 resampling not yet built
- displacement_scale is visual/aesthetic, not physically calibrated to real elevation
- No 256x256 live preview — comes with Module 3 integration
- setup.py installs Blender 4.5 LTS via winget, numpy/Pillow for system Python
  GDAL is explicitly excluded from Module 4 dependencies

## Important Behavioural Note for Module 3

The flat base extrudes from actual perimeter Z values — it does NOT snap them to zero.
Module 3's re-normalise step still ensures the lowest interior point = 0,
but edge vertices may sit slightly above 0 depending on terrain shape.
This is correct and intentional.
