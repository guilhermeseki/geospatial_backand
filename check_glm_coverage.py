#!/usr/bin/env python3
"""
Check if GLM FED files cover Brazil region.
Downloads a sample file and verifies spatial coverage.
"""
import os
import sys
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
import xarray as xr
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import get_settings

settings = get_settings()

# Brazil bounding box
BRAZIL_BBOX = {
    'lat_min': -35.0,
    'lat_max': 6.5,
    'lon_min': -75.0,
    'lon_max': -33.5
}

print("=" * 80)
print("GLM FED BRAZIL COVERAGE CHECK")
print("=" * 80)
print(f"Brazil bbox: lat [{BRAZIL_BBOX['lat_min']}, {BRAZIL_BBOX['lat_max']}]")
print(f"             lon [{BRAZIL_BBOX['lon_min']}, {BRAZIL_BBOX['lon_max']}]")
print("=" * 80)

# Try to find existing file first
test_file = None
raw_dir = Path(settings.DATA_DIR) / "raw" / "glm_fed"

if raw_dir.exists():
    nc_files = list(raw_dir.glob("glm_fed_daily_*.nc"))
    if nc_files:
        test_file = nc_files[0]
        print(f"\n✓ Found existing file: {test_file.name}")

if not test_file:
    # Download a sample file
    print("\nNo existing file found. Downloading sample file...")
    print("Date: 2025-11-16 12:00 UTC (3 days ago)")

    if not settings.EARTHDATA_USERNAME or not settings.EARTHDATA_PASSWORD:
        print("ERROR: Earthdata credentials not found in .env")
        sys.exit(1)

    # Try to download a single 30-minute file
    year, month, day, hour = 2025, 11, 16, 12
    satellite = "G19"
    filename = f"GLM-L3-{satellite}_Fed30_{year:04d}{month:02d}{day:02d}_t{hour:02d}00.nc"
    url = f"https://data.ghrc.earthdata.nasa.gov/ghrcwsc/GLMGOESL3.1/{year}/{filename}"

    temp_dir = Path("glm_temp")
    temp_dir.mkdir(exist_ok=True)
    test_file = temp_dir / filename

    print(f"Downloading: {filename}")
    print(f"URL: {url}")

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD),
            stream=True,
            timeout=120
        )

        if response.status_code != 200:
            print(f"ERROR: HTTP {response.status_code}")
            if response.status_code == 404:
                print("File not available - trying different date...")
                # Try 7 days ago
                year, month, day = 2025, 11, 12
                filename = f"GLM-L3-{satellite}_Fed30_{year:04d}{month:02d}{day:02d}_t{hour:02d}00.nc"
                url = f"https://data.ghrc.earthdata.nasa.gov/ghrcwsc/GLMGOESL3.1/{year}/{filename}"
                test_file = temp_dir / filename

                response = requests.get(
                    url,
                    auth=HTTPBasicAuth(settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD),
                    stream=True,
                    timeout=120
                )

                if response.status_code != 200:
                    print(f"ERROR: Still failed with HTTP {response.status_code}")
                    sys.exit(1)

        with open(test_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Downloaded: {test_file} ({test_file.stat().st_size / 1024 / 1024:.2f} MB)")

    except Exception as e:
        print(f"ERROR: Download failed: {e}")
        sys.exit(1)

# Open and check coverage
print(f"\n{'=' * 80}")
print("ANALYZING FILE COVERAGE")
print("=" * 80)

try:
    ds = xr.open_dataset(test_file)

    print(f"\nFile: {test_file.name}")
    print(f"Variables: {list(ds.data_vars)}")
    print(f"Coordinates: {list(ds.coords)}")
    print(f"Dimensions: {dict(ds.dims)}")

    # Find FED variable
    fed_vars = [v for v in ds.data_vars if "FED" in v.upper() or "flash" in v.lower()]
    if not fed_vars:
        print("\nERROR: No FED variable found")
        sys.exit(1)

    varname = fed_vars[0]
    fed = ds[varname]

    print(f"\nFED Variable: {varname}")
    print(f"Shape: {fed.shape}")

    # Check coordinate system
    print(f"\n{'=' * 80}")
    print("COORDINATE SYSTEM")
    print("=" * 80)

    if 'latitude' in fed.coords or 'lat' in fed.coords:
        # Data in lat/lon
        if 'latitude' in fed.coords:
            lats = fed.latitude.values
            lons = fed.longitude.values
        else:
            lats = fed.lat.values
            lons = fed.lon.values

        print(f"✓ Data is in lat/lon coordinates")
        print(f"  Latitude range: {lats.min():.2f} to {lats.max():.2f}")
        print(f"  Longitude range: {lons.min():.2f} to {lons.max():.2f}")

    elif 'x' in fed.coords and 'y' in fed.coords:
        # Data in GOES projection
        x_vals = fed.x.values
        y_vals = fed.y.values

        print(f"⚠ Data is in GOES geostationary projection")
        print(f"  X range: {x_vals.min():.6f} to {x_vals.max():.6f}")
        print(f"  Y range: {y_vals.min():.6f} to {y_vals.max():.6f}")

        # Check if radians or meters
        if abs(x_vals.max()) < 1:
            print(f"  Units: Radians (need conversion to lat/lon)")
        else:
            print(f"  Units: Meters (need conversion to lat/lon)")

        # Try to convert to lat/lon to check coverage
        print(f"\n  Converting to lat/lon to check coverage...")

        try:
            from pyproj import CRS, Transformer
            import rioxarray

            # Get satellite parameters
            sat_lon = -75.2  # GOES-19 default
            if 'goes_imager_projection' in ds:
                sat_lon = ds['goes_imager_projection'].attrs.get('longitude_of_projection_origin', -75.2)

            sat_height = 35786023.0

            # Convert to meters if in radians
            if abs(x_vals.max()) < 1:
                x_meters = x_vals * sat_height
                y_meters = y_vals * sat_height
            else:
                x_meters = x_vals
                y_meters = y_vals

            # Create transformer
            goes_crs = CRS.from_cf({
                'grid_mapping_name': 'geostationary',
                'perspective_point_height': sat_height,
                'longitude_of_projection_origin': sat_lon,
                'semi_major_axis': 6378137.0,
                'semi_minor_axis': 6356752.31414,
                'sweep_angle_axis': 'x'
            })

            wgs84_crs = CRS.from_epsg(4326)
            transformer = Transformer.from_crs(goes_crs, wgs84_crs, always_xy=True)

            # Convert corner points
            x_min, x_max = x_meters.min(), x_meters.max()
            y_min, y_max = y_meters.min(), y_meters.max()

            # Sample points around the edge
            lon_sw, lat_sw = transformer.transform(x_min, y_min)
            lon_se, lat_se = transformer.transform(x_max, y_min)
            lon_nw, lat_nw = transformer.transform(x_min, y_max)
            lon_ne, lat_ne = transformer.transform(x_max, y_max)

            all_lons = [lon_sw, lon_se, lon_nw, lon_ne]
            all_lats = [lat_sw, lat_se, lat_nw, lat_ne]

            lats = np.array(all_lats)
            lons = np.array(all_lons)

            print(f"  Converted bounds to lat/lon:")
            print(f"    Latitude range: {lats.min():.2f} to {lats.max():.2f}")
            print(f"    Longitude range: {lons.min():.2f} to {lons.max():.2f}")

        except Exception as e:
            print(f"  WARNING: Could not convert to lat/lon: {e}")
            lats = None
            lons = None
    else:
        print(f"ERROR: Unknown coordinate system")
        print(f"Available coords: {list(fed.coords)}")
        sys.exit(1)

    # Check Brazil coverage
    print(f"\n{'=' * 80}")
    print("BRAZIL COVERAGE CHECK")
    print("=" * 80)

    if lats is not None and lons is not None:
        lat_min_file = lats.min()
        lat_max_file = lats.max()
        lon_min_file = lons.min()
        lon_max_file = lons.max()

        # Check if Brazil bbox is within file bounds
        brazil_lat_covered = (lat_min_file <= BRAZIL_BBOX['lat_min']) and (lat_max_file >= BRAZIL_BBOX['lat_max'])
        brazil_lon_covered = (lon_min_file <= BRAZIL_BBOX['lon_min']) and (lon_max_file >= BRAZIL_BBOX['lon_max'])

        print(f"\nFile coverage:")
        print(f"  Latitude:  {lat_min_file:.2f} to {lat_max_file:.2f}")
        print(f"  Longitude: {lon_min_file:.2f} to {lon_max_file:.2f}")

        print(f"\nBrazil needs:")
        print(f"  Latitude:  {BRAZIL_BBOX['lat_min']:.2f} to {BRAZIL_BBOX['lat_max']:.2f}")
        print(f"  Longitude: {BRAZIL_BBOX['lon_min']:.2f} to {BRAZIL_BBOX['lon_max']:.2f}")

        print(f"\nCoverage check:")
        if brazil_lat_covered:
            print(f"  ✓ Latitude coverage: FULL")
        else:
            if lat_min_file > BRAZIL_BBOX['lat_min']:
                print(f"  ✗ Latitude coverage: PARTIAL (missing south: {BRAZIL_BBOX['lat_min']:.2f} to {lat_min_file:.2f})")
            if lat_max_file < BRAZIL_BBOX['lat_max']:
                print(f"  ✗ Latitude coverage: PARTIAL (missing north: {lat_max_file:.2f} to {BRAZIL_BBOX['lat_max']:.2f})")

        if brazil_lon_covered:
            print(f"  ✓ Longitude coverage: FULL")
        else:
            if lon_min_file > BRAZIL_BBOX['lon_min']:
                print(f"  ✗ Longitude coverage: PARTIAL (missing west: {BRAZIL_BBOX['lon_min']:.2f} to {lon_min_file:.2f})")
            if lon_max_file < BRAZIL_BBOX['lon_max']:
                print(f"  ✗ Longitude coverage: PARTIAL (missing east: {lon_max_file:.2f} to {BRAZIL_BBOX['lon_max']:.2f})")

        print(f"\n{'=' * 80}")
        if brazil_lat_covered and brazil_lon_covered:
            print("✓ RESULT: FILE FULLY COVERS BRAZIL REGION")
        else:
            print("⚠ RESULT: FILE ONLY PARTIALLY COVERS BRAZIL")
            print("\nNOTE: GOES satellites have different coverage:")
            print("  - GOES-16 (G16, -75.2°W): Best for Brazil/South America")
            print("  - GOES-18 (G18, -137.2°W): Best for Pacific/West Coast")
            print("  - GOES-19 (G19, -75.2°W): Replaces GOES-16, best for Brazil")
            print("\nFor Brazil, use G16 (2018-2024) or G19 (2025+)")
        print("=" * 80)

        # Calculate overlap percentage
        if not brazil_lat_covered or not brazil_lon_covered:
            # Calculate actual overlap
            overlap_lat_min = max(lat_min_file, BRAZIL_BBOX['lat_min'])
            overlap_lat_max = min(lat_max_file, BRAZIL_BBOX['lat_max'])
            overlap_lon_min = max(lon_min_file, BRAZIL_BBOX['lon_min'])
            overlap_lon_max = min(lon_max_file, BRAZIL_BBOX['lon_max'])

            if overlap_lat_max > overlap_lat_min and overlap_lon_max > overlap_lon_min:
                brazil_area = (BRAZIL_BBOX['lat_max'] - BRAZIL_BBOX['lat_min']) * (BRAZIL_BBOX['lon_max'] - BRAZIL_BBOX['lon_min'])
                overlap_area = (overlap_lat_max - overlap_lat_min) * (overlap_lon_max - overlap_lon_min)
                coverage_pct = (overlap_area / brazil_area) * 100
                print(f"\nBrazil coverage: {coverage_pct:.1f}%")

    ds.close()

except Exception as e:
    print(f"\nERROR: Failed to analyze file: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
