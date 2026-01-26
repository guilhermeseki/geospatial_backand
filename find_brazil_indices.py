#!/usr/bin/env python3
"""
Find the correct GOES pixel indices that cover ALL of Brazil.
This will help us update the spatial subset in glm_fed_flow.py
"""
import sys
from pathlib import Path
import xarray as xr
import numpy as np
from pyproj import CRS, Transformer

sys.path.insert(0, str(Path(__file__).parent))

# Open existing GLM file before subsetting
test_file = Path("/mnt/workwork/geoserver_data/raw/glm_fed/glm_fed_daily_20250415.nc")

print("=" * 80)
print("FINDING CORRECT GOES INDICES FOR FULL BRAZIL COVERAGE")
print("=" * 80)

# Brazil bounding box - FULL country
BRAZIL_BBOX = {
    'lat_min': -35.0,   # Rio Grande do Sul south
    'lat_max': 6.5,     # Roraima north
    'lon_min': -75.0,   # Acre west
    'lon_max': -33.5    # Paraíba east coast
}

print(f"\nTarget: Full Brazil")
print(f"  Latitude:  {BRAZIL_BBOX['lat_min']}° to {BRAZIL_BBOX['lat_max']}°")
print(f"  Longitude: {BRAZIL_BBOX['lon_min']}° to {BRAZIL_BBOX['lon_max']}°")

# Open original file (need to check what indices were used before subsetting)
# We need a file BEFORE the subset is applied
print(f"\nNote: The file at {test_file.name} was already subsetted.")
print(f"We need to analyze the FULL GOES disk to find correct indices.")

print(f"\n{'=' * 80}")
print("SOLUTION: Download a sample GOES file to find indices")
print("=" * 80)

# Download a single GLM 30-minute file to analyze
from app.config.settings import get_settings
import requests
from requests.auth import HTTPBasicAuth
import tempfile

settings = get_settings()

if not settings.EARTHDATA_USERNAME or not settings.EARTHDATA_PASSWORD:
    print("ERROR: Earthdata credentials not found")
    sys.exit(1)

# Try to download a recent single 30-min file (NOT the daily aggregate)
year, month, day, hour = 2025, 4, 15, 12
satellite = "G19"
filename = f"OR_GLM-L3-GLMF-M3_G19_s2025{105:03d}{hour:02d}0000_e2025{105:03d}{hour:02d}3000_c*.nc"

# Use CMR to find the file
print(f"\nSearching for GLM file from April 15, 2025 12:00 UTC...")

cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json"
params = {
    "short_name": "glmgoesL3",
    "provider": "GHRC_DAAC",
    "temporal": f"2025-04-15T12:00:00Z,2025-04-15T12:30:00Z",
    "page_size": 10
}

try:
    response = requests.get(cmr_url, params=params, timeout=60)
    response.raise_for_status()
    granules = response.json()['feed']['entry']

    # Filter for G19
    g19_granules = [g for g in granules if '_G19_' in g['title']]

    if not g19_granules:
        print("ERROR: No GOES-19 granules found for this date")
        print("Trying different approach: analyzing GOES projection math...")

        # GOES geostationary projection parameters
        sat_lon = -75.2  # GOES-19 longitude
        sat_height = 35786023.0  # meters

        # GOES full disk is 5424x5424 pixels in x,y radians
        # Typical range: -0.151844 to +0.151844 radians

        # For GOES at -75.2°W looking at Brazil:
        # Brazil spans -35° to 6.5° lat, -75° to -33.5° lon

        print(f"\n{'=' * 80}")
        print("MATHEMATICAL APPROACH")
        print("=" * 80)
        print(f"\nGOES-19 parameters:")
        print(f"  Satellite longitude: {sat_lon}°W")
        print(f"  Height: {sat_height / 1e6:.1f} thousand km")

        # Create GOES CRS
        goes_crs = CRS.from_cf({
            'grid_mapping_name': 'geostationary',
            'perspective_point_height': sat_height,
            'longitude_of_projection_origin': sat_lon,
            'semi_major_axis': 6378137.0,
            'semi_minor_axis': 6356752.31414,
            'sweep_angle_axis': 'x'
        })

        wgs84_crs = CRS.from_epsg(4326)

        # Transform Brazil corners to GOES projection
        transformer = Transformer.from_crs(wgs84_crs, goes_crs, always_xy=True)

        # Brazil corners in lat/lon
        corners = [
            (BRAZIL_BBOX['lon_min'], BRAZIL_BBOX['lat_min']),  # SW
            (BRAZIL_BBOX['lon_max'], BRAZIL_BBOX['lat_min']),  # SE
            (BRAZIL_BBOX['lon_min'], BRAZIL_BBOX['lat_max']),  # NW
            (BRAZIL_BBOX['lon_max'], BRAZIL_BBOX['lat_max']),  # NE
        ]

        print(f"\nBrazil corners in GOES projection:")
        x_coords = []
        y_coords = []

        for i, (lon, lat) in enumerate(corners):
            x, y = transformer.transform(lon, lat)
            x_coords.append(x)
            y_coords.append(y)
            corner_name = ['SW', 'SE', 'NW', 'NE'][i]
            print(f"  {corner_name} ({lat:>6.2f}°, {lon:>6.2f}°) → x={x/sat_height:.6f} rad, y={y/sat_height:.6f} rad")

        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        print(f"\nBrazil bbox in GOES projection (radians):")
        print(f"  X: {x_min/sat_height:.6f} to {x_max/sat_height:.6f}")
        print(f"  Y: {y_min/sat_height:.6f} to {y_max/sat_height:.6f}")

        # GOES full disk typical range
        full_disk_min = -0.151844
        full_disk_max = 0.151844
        full_disk_pixels = 5424  # typical GOES ABI full disk

        # But GLM uses 8km resolution, which is different
        # GLM typical: ~10800 x 10800 pixels for full disk
        # Let's estimate from the existing subsetted file

        ds = xr.open_dataset(test_file)
        current_x = ds.x.values
        current_y = ds.y.values

        print(f"\n{'=' * 80}")
        print("CURRENT SUBSET (from existing file)")
        print("=" * 80)
        print(f"  X range: {current_x.min():.6f} to {current_x.max():.6f} rad")
        print(f"  Y range: {current_y.min():.6f} to {current_y.max():.6f} rad")
        print(f"  X pixels: {len(current_x)}")
        print(f"  Y pixels: {len(current_y)}")
        print(f"  Shape: {ds.dims}")

        # The current subset was: y=slice(1200, 3800), x=slice(1000, 3900)
        # That gave us y=2600 pixels, x=2900 pixels

        print(f"\nCurrent subset indices (from code):")
        print(f"  y: 1200 to 3800 (2600 pixels)")
        print(f"  x: 1000 to 3900 (2900 pixels)")

        # Calculate what the full disk size must be
        # If x goes from index 1000 to 3900 (2900 pixels)
        # and covers -0.095844 to 0.066500 radians (0.162344 rad span)
        # then pixel size = 0.162344 / 2900 = 0.000056 rad/pixel

        x_span = current_x.max() - current_x.min()
        y_span = current_y.max() - current_y.min()

        pixel_size_x = x_span / len(current_x)
        pixel_size_y = y_span / len(current_y)

        print(f"\nEstimated pixel size:")
        print(f"  X: {pixel_size_x:.8f} rad/pixel")
        print(f"  Y: {pixel_size_y:.8f} rad/pixel")

        # Estimate full disk based on typical GOES range
        estimated_full_x = (full_disk_max - full_disk_min) / pixel_size_x
        estimated_full_y = (full_disk_max - full_disk_min) / pixel_size_y

        print(f"\nEstimated full disk size:")
        print(f"  X: ~{estimated_full_x:.0f} pixels")
        print(f"  Y: ~{estimated_full_y:.0f} pixels")

        # Now calculate what indices we need for full Brazil
        # Brazil in GOES: x from {x_min/sat_height:.6f} to {x_max/sat_height:.6f}
        #                y from {y_min/sat_height:.6f} to {y_max/sat_height:.6f}

        brazil_x_min_rad = x_min / sat_height
        brazil_x_max_rad = x_max / sat_height
        brazil_y_min_rad = y_min / sat_height
        brazil_y_max_rad = y_max / sat_height

        # Convert to indices (assuming full disk starts at -0.151844)
        # index = (coord - full_disk_min) / pixel_size

        # But we need to know what the actual full disk coordinates are
        # Let's work backwards from the current subset

        # Current x at index 1000 = current_x.min() = -0.095844
        # So: -0.095844 = full_disk_x[1000]
        # If full disk starts at index 0 with value full_disk_min
        # Then: full_disk_x[i] = full_disk_min + i * pixel_size_x
        # So: -0.095844 = full_disk_min + 1000 * pixel_size_x
        # full_disk_min = -0.095844 - 1000 * pixel_size_x

        estimated_full_disk_x_min = current_x.min() - 1000 * pixel_size_x
        estimated_full_disk_y_min = current_y.min() - 1200 * pixel_size_y

        print(f"\nEstimated full disk origin:")
        print(f"  X min: {estimated_full_disk_x_min:.6f} rad")
        print(f"  Y min: {estimated_full_disk_y_min:.6f} rad")

        # Calculate indices for Brazil
        brazil_x_start_idx = int((brazil_x_min_rad - estimated_full_disk_x_min) / pixel_size_x)
        brazil_x_end_idx = int((brazil_x_max_rad - estimated_full_disk_x_min) / pixel_size_x)
        brazil_y_start_idx = int((brazil_y_min_rad - estimated_full_disk_y_min) / pixel_size_y)
        brazil_y_end_idx = int((brazil_y_max_rad - estimated_full_disk_y_min) / pixel_size_y)

        print(f"\n{'=' * 80}")
        print("RECOMMENDED INDICES FOR FULL BRAZIL")
        print("=" * 80)
        print(f"\nTo cover Brazil completely:")
        print(f"  x: slice({brazil_x_start_idx}, {brazil_x_end_idx})")
        print(f"  y: slice({brazil_y_start_idx}, {brazil_y_end_idx})")
        print(f"\nPixels:")
        print(f"  X: {brazil_x_end_idx - brazil_x_start_idx} pixels")
        print(f"  Y: {brazil_y_end_idx - brazil_y_start_idx} pixels")
        print(f"  Total: {(brazil_x_end_idx - brazil_x_start_idx) * (brazil_y_end_idx - brazil_y_start_idx):,} pixels")

        # Add safety margin
        margin_pixels_x = int(50 / pixel_size_x * 0.01)  # ~50 km margin
        margin_pixels_y = int(50 / pixel_size_y * 0.01)

        safe_x_start = max(0, brazil_x_start_idx - margin_pixels_x)
        safe_x_end = brazil_x_end_idx + margin_pixels_x
        safe_y_start = max(0, brazil_y_start_idx - margin_pixels_y)
        safe_y_end = brazil_y_end_idx + margin_pixels_y

        print(f"\nRECOMMENDED (with safety margin):")
        print(f"  fed_data.isel(y=slice({safe_y_start}, {safe_y_end}), x=slice({safe_x_start}, {safe_x_end}))")

        print(f"\n{'=' * 80}")
        print("COMPARISON")
        print("=" * 80)
        print(f"Current:     y=slice(1200, 3800), x=slice(1000, 3900)")
        print(f"             → {2600} x {2900} pixels = {2600 * 2900:,} pixels")
        print(f"\nRecommended: y=slice({safe_y_start}, {safe_y_end}), x=slice({safe_x_start}, {safe_x_end})")
        print(f"             → {safe_y_end - safe_y_start} x {safe_x_end - safe_x_start} pixels = {(safe_y_end - safe_y_start) * (safe_x_end - safe_x_start):,} pixels")

        increase_pct = ((safe_y_end - safe_y_start) * (safe_x_end - safe_x_start)) / (2600 * 2900) * 100 - 100
        print(f"\nIncrease: {increase_pct:+.1f}% more pixels")

        ds.close()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
