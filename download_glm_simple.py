#!/usr/bin/env python3
"""
Simple GLM FED downloader based on user's ChatGPT example.
Downloads a single 30-minute GLM file and clips to Brazil.

Usage:
    python download_glm_simple.py
    python download_glm_simple.py --year 2025 --month 3 --day 1 --hour 14
"""
import os
import sys
import argparse
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
import xarray as xr
import rioxarray

# Add parent to path for settings
sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------
# LOAD CREDENTIALS FROM .ENV
# ---------------------------------------------------
from app.config.settings import get_settings

settings = get_settings()

if not settings.EARTHDATA_USERNAME or not settings.EARTHDATA_PASSWORD:
    print("ERROR: Earthdata credentials not found in .env file")
    print("Expected: EARTHDATA_USERNAME and EARTHDATA_PASSWORD")
    sys.exit(1)

username = settings.EARTHDATA_USERNAME
password = settings.EARTHDATA_PASSWORD

print(f"✓ Loaded credentials for: {username}")

# ---------------------------------------------------
# USER SETTINGS (from command line or defaults)
# ---------------------------------------------------
parser = argparse.ArgumentParser(description='Download single GLM FED 30-minute file')
parser.add_argument('--year', type=int, default=2025, help='Year (default: 2025)')
parser.add_argument('--month', type=int, default=3, help='Month (default: 3)')
parser.add_argument('--day', type=int, default=1, help='Day (default: 1)')
parser.add_argument('--hour', type=int, default=14, help='Hour UTC (default: 14)')
parser.add_argument('--satellite', type=str, default='G19',
                    choices=['G16', 'G18', 'G19'],
                    help='Satellite (default: G19)')
parser.add_argument('--out-dir', type=str, default='glm_brazil',
                    help='Output directory (default: glm_brazil)')

args = parser.parse_args()

year = args.year
month = args.month
day = args.day
hour = args.hour
satellite = args.satellite

# Brazil bounding box (from settings)
lat_min, lat_max = -35, 5
lon_min, lon_max = -75, -35  # degrees West

out_dir = args.out_dir
os.makedirs(out_dir, exist_ok=True)

# ---------------------------------------------------
# Build file name and URL
# ---------------------------------------------------

filename = f"GLM-L3-{satellite}_Fed30_{year:04d}{month:02d}{day:02d}_t{hour:02d}00.nc"
url = f"https://data.ghrc.earthdata.nasa.gov/ghrcwsc/GLMGOESL3.1/{year}/{filename}"

local_nc = os.path.join(out_dir, filename)
local_tif = os.path.join(out_dir, filename.replace(".nc", "_BRAZIL.tif"))

print("=" * 80)
print("GLM FED SIMPLE DOWNLOAD")
print("=" * 80)
print(f"Date/Time: {year}-{month:02d}-{day:02d} {hour:02d}:00 UTC")
print(f"Satellite: GOES-{satellite.replace('G', '')}")
print(f"File: {filename}")
print(f"URL: {url}")
print(f"Output NetCDF: {local_nc}")
print(f"Output GeoTIFF: {local_tif}")
print("=" * 80)

# ---------------------------------------------------
# Download file
# ---------------------------------------------------

if not os.path.exists(local_nc):
    print(f"\nDownloading: {filename}")
    print(f"This may take a few minutes (file is ~2-5 MB)...")

    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password), stream=True)

        if response.status_code != 200:
            print(f"ERROR: HTTP {response.status_code}")
            if response.status_code == 401:
                print("Authentication failed - check your Earthdata credentials")
            elif response.status_code == 404:
                print(f"File not found - this date/hour may not be available yet")
                print(f"Try an older date or different hour")
            else:
                print(f"Response: {response.text[:200]}")
            raise SystemExit("Download failed.")

        # Download with progress
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(local_nc, "wb") as f:
            for chunk in response.iter_content(chunk_size=4096):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    print(f"\rProgress: {pct:.1f}% ({downloaded / 1024 / 1024:.2f} MB)", end='')

        print(f"\n✓ Download complete: {local_nc}")

    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Network error: {e}")
        sys.exit(1)
else:
    print(f"\n✓ File already exists: {local_nc}")

# ---------------------------------------------------
# Open, clip to Brazil, save GeoTIFF
# ---------------------------------------------------

print(f"\nOpening dataset...")
try:
    ds = xr.open_dataset(local_nc)

    # Print available variables
    print(f"Available variables: {list(ds.data_vars)}")

    # Find FED variable
    # variable names usually:
    # - FED (Flash Extent Density)
    # - flash_extent_density
    fed_vars = [v for v in ds.data_vars if "FED" in v.upper() or "flash" in v.lower()]

    if not fed_vars:
        print(f"ERROR: No FED variable found in dataset")
        print(f"Available variables: {list(ds.data_vars)}")
        sys.exit(1)

    varname = fed_vars[0]
    print(f"Using variable: {varname}")

    fed = ds[varname]

    print(f"Original shape: {fed.shape}")
    print(f"Original coords: {list(fed.coords)}")

    # Check if data is in GOES projection or lat/lon
    if 'latitude' in fed.coords or 'lat' in fed.coords:
        print(f"\nData is already in lat/lon coordinates")

        # Determine coordinate names
        if 'latitude' in fed.coords:
            lat_name, lon_name = 'latitude', 'longitude'
        else:
            lat_name, lon_name = 'lat', 'lon'

        # Ensure CRS
        if not fed.rio.crs:
            fed = fed.rio.write_crs("EPSG:4326")

        print(f"Clipping to Brazil bbox: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]...")

        # Clip to Brazil
        fed_br = fed.sel(
            {lat_name: slice(lat_max, lat_min),   # north → south (reversed for decreasing coords)
             lon_name: slice(lon_min, lon_max)}   # west → east
        )

    else:
        # Data is in GOES geostationary projection - need to reproject
        print(f"\nData is in GOES projection - need to reproject to WGS84")
        print(f"This may take a few minutes...")

        # Get satellite parameters from metadata
        if hasattr(ds, 'platform_ID') or 'goes_imager_projection' in ds:
            # Try to get sat lon from projection variable
            if 'goes_imager_projection' in ds:
                proj = ds['goes_imager_projection']
                sat_lon = proj.attrs.get('longitude_of_projection_origin', -75.2)
            else:
                # Default for GOES-16/19 (East)
                sat_lon = -75.2
        else:
            sat_lon = -75.2

        print(f"Using satellite longitude: {sat_lon}°W")

        # Import pyproj for CRS conversion
        from pyproj import CRS

        sat_height = 35786023.0  # Geostationary orbit height in meters

        # Convert x,y from radians to meters if needed
        if 'x' in fed.coords and 'y' in fed.coords:
            x_vals = fed.x.values
            y_vals = fed.y.values

            # Check if values are in radians (small numbers) or meters (large numbers)
            if abs(x_vals.max()) < 1:  # Likely radians
                print(f"Converting from radians to meters...")
                x_meters = x_vals * sat_height
                y_meters = y_vals * sat_height
            else:  # Already in meters
                x_meters = x_vals
                y_meters = y_vals

            # Create DataArray with proper coordinates
            fed_geo = xr.DataArray(
                fed.values,
                coords={'y': y_meters, 'x': x_meters},
                dims=['y', 'x']
            )

            # Set GOES CRS
            goes_crs = CRS.from_cf({
                'grid_mapping_name': 'geostationary',
                'perspective_point_height': sat_height,
                'longitude_of_projection_origin': sat_lon,
                'semi_major_axis': 6378137.0,
                'semi_minor_axis': 6356752.31414,
                'sweep_angle_axis': 'x'
            })

            fed_geo = fed_geo.rio.write_crs(goes_crs)

            # Reproject to WGS84
            fed_wgs84 = fed_geo.rio.reproject("EPSG:4326")

            # Clip to Brazil
            fed_br = fed_wgs84.rio.clip_box(lon_min, lat_min, lon_max, lat_max)
        else:
            print(f"ERROR: Could not determine coordinate system")
            print(f"Available coords: {list(fed.coords)}")
            sys.exit(1)

    print(f"Clipped shape: {fed_br.shape}")

    # Save GeoTIFF
    print(f"\nSaving Brazil GeoTIFF: {local_tif}")
    fed_br.rio.to_raster(local_tif, driver="COG", compress="LZW")

    # Get file size
    tif_size = os.path.getsize(local_tif) / 1024 / 1024

    print(f"✓ Done!")
    print("=" * 80)
    print(f"Output files:")
    print(f"  NetCDF: {local_nc} ({os.path.getsize(local_nc) / 1024 / 1024:.2f} MB)")
    print(f"  GeoTIFF: {local_tif} ({tif_size:.2f} MB)")
    print("=" * 80)

    # Print data stats
    print(f"\nData statistics:")
    print(f"  Min FED: {float(fed_br.min()):.4f}")
    print(f"  Max FED: {float(fed_br.max()):.4f}")
    print(f"  Mean FED: {float(fed_br.mean()):.4f}")

    ds.close()

except Exception as e:
    print(f"\nERROR: Failed to process file: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
