#!/usr/bin/env python3
"""
Test GLM FED 30-minute max processing for a single day
and verify Brazil coverage from GOES-19.
"""
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import requests
from requests.auth import HTTPBasicAuth
import rioxarray
from pyproj import CRS
import os
import sys

# Add project to path
sys.path.insert(0, '/opt/geospatial_backend')
from app.config.settings import get_settings

settings = get_settings()

# Test date - pick a recent date from 2025
TEST_DATE = date(2025, 11, 15)  # Change this to your desired test date

def get_credentials():
    """Get Earthdata credentials."""
    username = settings.EARTHDATA_USERNAME or os.getenv('EARTHDATA_USERNAME')
    password = settings.EARTHDATA_PASSWORD or os.getenv('EARTHDATA_PASSWORD')

    if not username or not password:
        # Try .netrc
        netrc_file = Path.home() / '.netrc'
        if netrc_file.exists():
            import netrc
            try:
                auth = netrc.netrc().authenticators('urs.earthdata.nasa.gov')
                if auth:
                    username, _, password = auth
            except:
                pass

    if not username or not password:
        raise ValueError("Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD")

    return username, password


def download_single_day_glm(target_date: date, limit: int = 100):
    """
    Download a sample of GLM files for one day to test coverage.

    Args:
        target_date: Date to download
        limit: Max files to download (for quick test)
    """
    print(f"\n{'='*60}")
    print(f"DOWNLOADING GLM FED FOR {target_date}")
    print(f"{'='*60}")

    username, password = get_credentials()

    # Use GOES-19 for 2025
    satellite = "G19"
    print(f"Satellite: GOES-{satellite.replace('G', '')}")

    # CMR API
    cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json"

    start_datetime = f"{target_date}T00:00:00Z"
    end_datetime = f"{target_date}T23:59:59Z"

    params = {
        "short_name": "glmgoesL3",
        "provider": "GHRC_DAAC",
        "temporal": f"{start_datetime},{end_datetime}",
        "page_size": 500
    }

    print(f"Searching CMR for granules...")
    response = requests.get(cmr_url, params=params, timeout=60)
    response.raise_for_status()

    all_granules = response.json()['feed']['entry']

    # Filter for satellite
    granules = [g for g in all_granules if f"_{satellite}_" in g['title']]
    print(f"Found {len(granules)} {satellite} granules (out of {len(all_granules)} total)")

    if len(granules) == 0:
        print("No granules found! Check if GOES-19 data is available for this date.")
        return None

    # Download limited sample (spread across the day)
    step = max(1, len(granules) // limit)
    sample_granules = granules[::step][:limit]
    print(f"Downloading {len(sample_granules)} sample files...")

    # Create temp directory
    temp_dir = Path(settings.DATA_DIR) / "raw" / "glm_test"
    temp_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)

    downloaded_files = []

    for i, granule in enumerate(sample_granules):
        links = granule.get('links', [])
        download_url = None

        for link in links:
            if link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/data#':
                download_url = link.get('href')
                break

        if not download_url:
            continue

        filename = download_url.split('/')[-1]
        local_file = temp_dir / filename

        if not local_file.exists():
            try:
                resp = session.get(download_url, timeout=120, stream=True)
                resp.raise_for_status()

                with open(local_file, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)

                downloaded_files.append(local_file)

                if (i + 1) % 20 == 0:
                    print(f"  Downloaded {i+1}/{len(sample_granules)}")

            except Exception as e:
                print(f"  Failed: {filename}: {e}")
        else:
            downloaded_files.append(local_file)

    print(f"Downloaded {len(downloaded_files)} files")
    return downloaded_files


def parse_timestamp_from_filename(filename: str) -> pd.Timestamp:
    """Parse timestamp from GLM filename."""
    start_idx = filename.find('_s')
    if start_idx == -1:
        return None

    start_time_str = filename[start_idx + 2:]
    if '_' in start_time_str:
        start_time_str = start_time_str.split('_')[0]

    year = int(start_time_str[0:4])
    day_of_year = int(start_time_str[4:7])
    hour = int(start_time_str[7:9])
    minute = int(start_time_str[9:11])
    second = int(start_time_str[11:13])

    timestamp = pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=day_of_year - 1)
    return timestamp.replace(hour=hour, minute=minute, second=second)


def process_to_30min_max(files: list, target_date: date):
    """
    Process files to 30-minute bins and find max.
    Returns the max 30-min FED value for each grid cell.
    """
    print(f"\n{'='*60}")
    print(f"PROCESSING TO 30-MINUTE MAX")
    print(f"{'='*60}")

    # Parse timestamps and load data
    file_data = []

    for f in files:
        try:
            ts = parse_timestamp_from_filename(f.stem)
            if ts is None:
                continue

            ds = xr.open_dataset(f, chunks={'y': 200, 'x': 200})

            # Find FED variable
            var_name = None
            for v in ds.data_vars:
                if 'fed' in v.lower() or 'flash' in v.lower():
                    var_name = v
                    break

            if var_name is None:
                ds.close()
                continue

            fed = ds[var_name]
            fed_with_time = fed.expand_dims(time=[ts])
            file_data.append(fed_with_time)

        except Exception as e:
            print(f"  Error loading {f.name}: {e}")

    if not file_data:
        print("No data loaded!")
        return None

    print(f"Loaded {len(file_data)} files")

    # Concatenate
    time_series = xr.concat(file_data, dim='time', join='outer', fill_value=np.nan)
    time_series = time_series.chunk({'time': 50, 'y': 200, 'x': 200})

    print(f"Time range: {pd.Timestamp(time_series.time.min().values)} to {pd.Timestamp(time_series.time.max().values)}")

    # Resample to 30-minute bins
    print("Resampling to 30-minute bins...")
    binned = time_series.resample(time='30min', label='left', closed='left').sum()

    # Filter to target date
    target_start = pd.Timestamp(target_date)
    target_end = target_start + pd.Timedelta(days=1)

    bins_day = binned.sel(time=slice(target_start, target_end - pd.Timedelta(seconds=1)))

    num_bins = len(bins_day.time)
    print(f"Created {num_bins} 30-minute bins")

    # Find max across all bins
    print("Computing max across bins...")
    max_fed = bins_day.max(dim='time').compute()

    return max_fed, time_series


def check_brazil_coverage(max_fed: xr.DataArray):
    """
    Check and visualize Brazil coverage.
    """
    print(f"\n{'='*60}")
    print(f"CHECKING BRAZIL COVERAGE")
    print(f"{'='*60}")

    # Brazil bounding box
    brazil_bbox = settings.brazil_bbox_raster  # (W, S, E, N)
    W, S, E, N = brazil_bbox
    print(f"Brazil bbox: W={W}, S={S}, E={E}, N={N}")

    # Get data extent
    if 'x' in max_fed.dims and 'y' in max_fed.dims:
        # Still in GOES projection - need to reproject
        print("Data is in GOES geostationary projection")

        sat_height = 35786023.0
        sat_lon = -75.2  # GOES-19

        # Get x,y ranges (in radians originally)
        x_rad = max_fed.x.values
        y_rad = max_fed.y.values

        # Convert to meters
        x_meters = x_rad * sat_height
        y_meters = y_rad * sat_height

        print(f"  X range (radians): {x_rad.min():.4f} to {x_rad.max():.4f}")
        print(f"  Y range (radians): {y_rad.min():.4f} to {y_rad.max():.4f}")

        # Reproject to WGS84
        print("Reprojecting to WGS84...")

        fed_geo = xr.DataArray(
            max_fed.values,
            coords={'y': y_meters, 'x': x_meters},
            dims=['y', 'x']
        )

        goes_crs = CRS.from_cf({
            'grid_mapping_name': 'geostationary',
            'perspective_point_height': sat_height,
            'longitude_of_projection_origin': sat_lon,
            'semi_major_axis': 6378137.0,
            'semi_minor_axis': 6356752.31414,
            'sweep_angle_axis': 'x'
        })
        fed_geo = fed_geo.rio.write_crs(goes_crs)

        max_fed_wgs84 = fed_geo.rio.reproject("EPSG:4326")

        # Get WGS84 extent
        x_wgs = max_fed_wgs84.x.values
        y_wgs = max_fed_wgs84.y.values

        print(f"  Reprojected extent:")
        print(f"    Longitude: {x_wgs.min():.2f} to {x_wgs.max():.2f}")
        print(f"    Latitude:  {y_wgs.min():.2f} to {y_wgs.max():.2f}")

    else:
        max_fed_wgs84 = max_fed
        if 'longitude' in max_fed.dims:
            x_wgs = max_fed.longitude.values
            y_wgs = max_fed.latitude.values
        else:
            x_wgs = max_fed.x.values
            y_wgs = max_fed.y.values

    # Check coverage
    print(f"\nBrazil coverage analysis:")
    print(f"  Brazil W edge ({W}): {'COVERED' if x_wgs.min() <= W else 'NOT COVERED'} (data starts at {x_wgs.min():.2f})")
    print(f"  Brazil E edge ({E}): {'COVERED' if x_wgs.max() >= E else 'NOT COVERED'} (data ends at {x_wgs.max():.2f})")
    print(f"  Brazil S edge ({S}): {'COVERED' if y_wgs.min() <= S else 'NOT COVERED'} (data starts at {y_wgs.min():.2f})")
    print(f"  Brazil N edge ({N}): {'COVERED' if y_wgs.max() >= N else 'NOT COVERED'} (data ends at {y_wgs.max():.2f})")

    # Clip to Brazil
    print("\nClipping to Brazil...")
    try:
        clipped = max_fed_wgs84.rio.clip_box(W, S, E, N)
        print(f"  Clipped shape: {clipped.shape}")

        # Check for valid data
        valid_data = clipped.values[~np.isnan(clipped.values)]
        print(f"  Valid (non-NaN) pixels: {len(valid_data)} / {clipped.size} ({100*len(valid_data)/clipped.size:.1f}%)")

        if len(valid_data) > 0:
            print(f"  FED range: {valid_data.min():.2f} to {valid_data.max():.2f}")

        return clipped

    except Exception as e:
        print(f"  Clipping failed: {e}")
        return max_fed_wgs84


def plot_coverage(max_fed_clipped: xr.DataArray, target_date: date):
    """Plot the coverage map."""
    print(f"\nGenerating coverage plot...")

    fig, ax = plt.subplots(figsize=(12, 10))

    # Get coordinates
    if 'longitude' in max_fed_clipped.dims:
        x = max_fed_clipped.longitude.values
        y = max_fed_clipped.latitude.values
    else:
        x = max_fed_clipped.x.values
        y = max_fed_clipped.y.values

    # Plot
    im = ax.pcolormesh(x, y, max_fed_clipped.values,
                       cmap='hot_r', vmin=0, vmax=100)

    plt.colorbar(im, ax=ax, label='Flash Extent Density (max 30-min bin)')

    # Add Brazil bbox
    brazil_bbox = settings.brazil_bbox_raster
    W, S, E, N = brazil_bbox

    rect = mpatches.Rectangle((W, S), E-W, N-S,
                               linewidth=2, edgecolor='blue',
                               facecolor='none', linestyle='--',
                               label='Brazil bbox')
    ax.add_patch(rect)

    # Add approximate Brazil outline points
    brazil_outline_lon = [-73.99, -57.64, -48.55, -34.85, -35.46, -40.50, -51.83, -53.37, -73.99]
    brazil_outline_lat = [-4.21, -30.22, -28.85, -7.15, -5.27, -2.22, 4.42, -1.42, -4.21]
    ax.plot(brazil_outline_lon, brazil_outline_lat, 'g-', linewidth=2, label='Brazil (approx)')

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(f'GLM FED Max 30-min Window - {target_date}\nGOES-19')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Set extent to Brazil + margin
    ax.set_xlim(W - 5, E + 5)
    ax.set_ylim(S - 5, N + 5)

    output_file = Path('/opt/geospatial_backend/glm_30min_coverage_test.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved plot to: {output_file}")

    plt.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("GLM FED 30-MINUTE MAX COVERAGE TEST")
    print("="*60)
    print(f"Test date: {TEST_DATE}")

    # Download sample
    files = download_single_day_glm(TEST_DATE, limit=100)

    if files and len(files) > 0:
        # Process to 30-min max
        result = process_to_30min_max(files, TEST_DATE)

        if result:
            max_fed, time_series = result

            # Check coverage
            clipped = check_brazil_coverage(max_fed)

            # Plot
            if clipped is not None:
                plot_coverage(clipped, TEST_DATE)

    print("\nDone!")
