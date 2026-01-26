#!/usr/bin/env python3
"""
Quick test: Download one day and check coverage.
Run as current user to avoid permission issues.
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.glm_fed_flow import download_glm_fed_daily
from app.config.settings import get_settings
import xarray as xr
from pyproj import Transformer, CRS

settings = get_settings()

# Test date - use one that already exists
test_date = date(2025, 4, 15)

print("=" * 80)
print("GLM BRAZIL COVERAGE QUICK TEST")
print("=" * 80)
print(f"Test date: {test_date}")
print("Using existing file to check coverage")
print("=" * 80)

# Check existing file
raw_file = Path(settings.DATA_DIR) / "raw" / "glm_fed" / f"glm_fed_daily_{test_date.strftime('%Y%m%d')}.nc"

if not raw_file.exists():
    print(f"\n✗ File not found: {raw_file}")
    print("Let's use an existing file instead...")

    # Find any existing file
    raw_dir = Path(settings.DATA_DIR) / "raw" / "glm_fed"
    existing_files = list(raw_dir.glob("glm_fed_daily_*.nc"))

    if not existing_files:
        print("No existing files found. Need to download.")
        sys.exit(1)

    raw_file = existing_files[0]
    print(f"Using: {raw_file.name}")

# Brazil bbox
BRAZIL = {'lat_min': -35.0, 'lat_max': 6.5, 'lon_min': -75.0, 'lon_max': -33.5}

print(f"\nBrazil target: lat [{BRAZIL['lat_min']}, {BRAZIL['lat_max']}], lon [{BRAZIL['lon_min']}, {BRAZIL['lon_max']}]")

# Open and check
print(f"\nOpening: {raw_file.name}")
ds = xr.open_dataset(raw_file)

print(f"  Variables: {list(ds.data_vars)}")
print(f"  Dimensions: {dict(ds.dims)}")
print(f"  Coords: {list(ds.coords)}")

# Check if this is the OLD subset or NEW full disk
x_vals = ds.x.values
y_vals = ds.y.values
x_pixels = len(x_vals)
y_pixels = len(y_vals)

print(f"\n  Spatial extent:")
print(f"    X: {x_vals.min():.6f} to {x_vals.max():.6f} rad ({x_pixels} pixels)")
print(f"    Y: {y_vals.min():.6f} to {y_vals.max():.6f} rad ({y_pixels} pixels)")

# Check if this is old subset
if x_pixels == 2900 and y_pixels == 2600:
    print(f"\n⚠️  This is the OLD SUBSET (2600 x 2900 pixels)")
    print(f"    This file was created BEFORE the fix")
    print(f"    Need to download a new file to test the fix")
elif x_pixels > 5000 and y_pixels > 5000:
    print(f"\n✓ This is the FULL DISK ({y_pixels} x {x_pixels} pixels)")
    print(f"   This should cover all of Brazil!")
else:
    print(f"\n? Unknown subset size: {y_pixels} x {x_pixels} pixels")

# GOES params
sat_lon = -75.2
sat_height = 35786023.0

goes_crs = CRS.from_cf({
    'grid_mapping_name': 'geostationary',
    'perspective_point_height': sat_height,
    'longitude_of_projection_origin': sat_lon,
    'semi_major_axis': 6378137.0,
    'semi_minor_axis': 6356752.31414,
    'sweep_angle_axis': 'x'
})
wgs84 = CRS.from_epsg(4326)
to_latlon = Transformer.from_crs(goes_crs, wgs84, always_xy=True)

# Convert corners
corners_xy = [
    (x_vals.min(), y_vals.min()),
    (x_vals.max(), y_vals.min()),
    (x_vals.min(), y_vals.max()),
    (x_vals.max(), y_vals.max()),
]

lats, lons = [], []
for x, y in corners_xy:
    lon, lat = to_latlon.transform(x * sat_height, y * sat_height)
    lats.append(lat)
    lons.append(lon)

file_lat_min, file_lat_max = min(lats), max(lats)
file_lon_min, file_lon_max = min(lons), max(lons)

print(f"\n  Coverage in lat/lon:")
print(f"    Latitude:  {file_lat_min:>7.2f}° to {file_lat_max:>7.2f}°")
print(f"    Longitude: {file_lon_min:>7.2f}° to {file_lon_max:>7.2f}°")

# Check Brazil coverage
lat_covered = (file_lat_min <= BRAZIL['lat_min']) and (file_lat_max >= BRAZIL['lat_max'])
lon_covered = (file_lon_min <= BRAZIL['lon_min']) and (file_lon_max >= BRAZIL['lon_max'])

print(f"\n{'=' * 80}")
print("BRAZIL COVERAGE CHECK")
print("=" * 80)

if lat_covered and lon_covered:
    print("✓✓✓ FULL BRAZIL COVERAGE CONFIRMED! ✓✓✓")
    print(f"\n  All of Brazil is covered:")
    print(f"    - North to south: {BRAZIL['lat_min']}° to {BRAZIL['lat_max']}°")
    print(f"    - West to east: {BRAZIL['lon_min']}° to {BRAZIL['lon_max']}°")
else:
    print("✗ INCOMPLETE COVERAGE")

    if not lat_covered:
        print(f"\n  Latitude: ✗ MISSING")
        if file_lat_min > BRAZIL['lat_min']:
            missing = BRAZIL['lat_min'] - file_lat_min
            print(f"    Missing SOUTH: {file_lat_min:.2f}° to {BRAZIL['lat_min']}° ({abs(missing):.1f}° gap)")
            print(f"    → Missing southern Rio Grande do Sul")
        if file_lat_max < BRAZIL['lat_max']:
            missing = BRAZIL['lat_max'] - file_lat_max
            print(f"    Missing NORTH: {file_lat_max:.2f}° to {BRAZIL['lat_max']}° ({missing:.1f}° gap)")
            print(f"    → Missing northern Roraima")
    else:
        print(f"  Latitude: ✓ COVERED")

    if not lon_covered:
        print(f"\n  Longitude: ✗ MISSING")
        if file_lon_min > BRAZIL['lon_min']:
            missing = BRAZIL['lon_min'] - file_lon_min
            print(f"    Missing WEST: {file_lon_min:.2f}° to {BRAZIL['lon_min']}° ({abs(missing):.1f}° gap)")
            print(f"    → Missing western Acre")
        if file_lon_max < BRAZIL['lon_max']:
            missing = BRAZIL['lon_max'] - file_lon_max
            print(f"    Missing EAST: {file_lon_max:.2f}° to {BRAZIL['lon_max']}° ({abs(missing):.1f}° gap)")
            print(f"    → Missing eastern coastline")
    else:
        print(f"  Longitude: ✓ COVERED")

ds.close()

print(f"\n{'=' * 80}")

if x_pixels == 2900 and y_pixels == 2600:
    print("NOTE: This file uses the OLD subset code.")
    print("To test the NEW code, delete this file and download again:")
    print(f"  rm {raw_file}")
    print(f"  python app/run_glm_fed_test.py")

print("=" * 80)
