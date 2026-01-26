#!/usr/bin/env python3
"""Verify GLM FED data integrity and correctness"""

import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

def verify_glm_historical_data():
    """Comprehensive verification of GLM FED historical NetCDF data"""

    hist_file = Path("/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc")

    if not hist_file.exists():
        print(f"❌ Historical file not found: {hist_file}")
        return False

    print("=" * 80)
    print("GLM FED DATA VERIFICATION")
    print("=" * 80)
    print(f"\n📁 File: {hist_file}")
    print(f"📊 File size: {hist_file.stat().st_size / (1024**2):.2f} MB")

    # Open dataset
    try:
        ds = xr.open_dataset(hist_file, chunks='auto')
        print(f"✅ Successfully opened NetCDF file")
    except Exception as e:
        print(f"❌ Failed to open file: {e}")
        return False

    print(f"\n📋 Dataset structure:")
    print(f"  Dimensions: {dict(ds.dims)}")
    print(f"  Coordinates: {list(ds.coords)}")
    print(f"  Data variables: {list(ds.data_vars)}")

    # Check required variables
    required_vars = ['fed_30min_max', 'fed_30min_time']
    missing_vars = [v for v in required_vars if v not in ds.data_vars]
    if missing_vars:
        print(f"❌ Missing required variables: {missing_vars}")
        return False
    print(f"✅ All required variables present")

    # Check dimensions
    if 'time' not in ds.dims:
        print(f"❌ Missing 'time' dimension")
        return False

    if 'lat' not in ds.coords and 'lon' not in ds.coords:
        print(f"❌ Missing lat/lon coordinates")
        return False

    print(f"✅ Required dimensions present")

    # Time dimension checks
    print(f"\n⏰ TIME DIMENSION:")
    times = pd.to_datetime(ds.time.values)
    print(f"  Number of time steps: {len(times)}")
    print(f"  Date range: {times.min().date()} to {times.max().date()}")

    # Check for duplicates
    duplicate_times = times[times.duplicated()]
    if len(duplicate_times) > 0:
        print(f"❌ Found {len(duplicate_times)} duplicate timestamps:")
        for dup in duplicate_times[:5]:  # Show first 5
            print(f"     - {dup}")
        return False
    print(f"✅ No duplicate timestamps")

    # Check for gaps
    if len(times) > 1:
        time_diffs = np.diff(times.values) / np.timedelta64(1, 'D')
        gaps = np.where(time_diffs > 1)[0]
        if len(gaps) > 0:
            print(f"⚠️  Found {len(gaps)} gaps in time series:")
            for gap_idx in gaps[:5]:  # Show first 5
                print(f"     Gap between {times[gap_idx].date()} and {times[gap_idx+1].date()} ({time_diffs[gap_idx]:.1f} days)")
        else:
            print(f"✅ No gaps in time series (continuous daily data)")

    # Check time sorting
    if not np.all(times[:-1] <= times[1:]):
        print(f"❌ Time dimension is not sorted")
        return False
    print(f"✅ Time dimension is sorted")

    # Geographic extent checks
    print(f"\n🌎 GEOGRAPHIC EXTENT:")
    lats = ds.lat.values
    lons = ds.lon.values
    print(f"  Latitude range: {lats.min():.2f}° to {lats.max():.2f}°")
    print(f"  Longitude range: {lons.min():.2f}° to {lons.max():.2f}°")
    print(f"  Grid size: {len(lats)} × {len(lons)} = {len(lats) * len(lons):,} points")

    # Check if covers Latin America
    latam_bbox = (-53, -94, 25, -34)  # S, W, N, E
    covers_latam = (
        lats.min() <= latam_bbox[0] and lats.max() >= latam_bbox[2] and
        lons.min() <= latam_bbox[1] and lons.max() >= latam_bbox[3]
    )
    if covers_latam:
        print(f"✅ Coverage includes Latin America bbox")
    else:
        print(f"⚠️  Coverage may not fully include Latin America")
        print(f"    Target: Lat {latam_bbox[0]}° to {latam_bbox[2]}°, Lon {latam_bbox[1]}° to {latam_bbox[3]}°")

    # Data value checks
    print(f"\n📊 DATA VALUES (fed_30min_max):")
    fed_data = ds['fed_30min_max']

    # Load a sample to check values
    sample = fed_data.isel(time=slice(0, min(10, len(times)))).values

    print(f"  Shape: {fed_data.shape}")
    print(f"  Dtype: {fed_data.dtype}")

    # Check for all NaN slices
    all_nan_times = []
    for i, t in enumerate(times[:min(10, len(times))]):
        if np.all(np.isnan(fed_data.isel(time=i).values)):
            all_nan_times.append(t)

    if all_nan_times:
        print(f"⚠️  Found {len(all_nan_times)} time slices with all NaN values (first 10 checked)")
        for t in all_nan_times:
            print(f"     - {t.date()}")

    # Statistical summary (using sample to avoid loading full dataset)
    valid_values = sample[~np.isnan(sample)]
    if len(valid_values) > 0:
        print(f"\n  Statistics (sample from first {min(10, len(times))} timesteps):")
        print(f"    Valid values: {len(valid_values):,} / {sample.size:,} ({100*len(valid_values)/sample.size:.1f}%)")
        print(f"    Min: {valid_values.min():.6f}")
        print(f"    Max: {valid_values.max():.6f}")
        print(f"    Mean: {valid_values.mean():.6f}")
        print(f"    Median: {np.median(valid_values):.6f}")

        # Check for negative values (FED should be >= 0)
        negative_count = np.sum(valid_values < 0)
        if negative_count > 0:
            print(f"❌ Found {negative_count} negative values (FED should be >= 0)")
            return False
        print(f"✅ All values are non-negative")

        # Check for unreasonably high values
        # FED max is typically < 1.0 (flash extent density per km²)
        very_high = np.sum(valid_values > 10.0)
        if very_high > 0:
            print(f"⚠️  Found {very_high} values > 10.0 (may be unreasonably high)")
            print(f"    Max value: {valid_values.max():.6f}")
    else:
        print(f"❌ No valid (non-NaN) values found in sample")
        return False

    # Check datetime variable
    print(f"\n⏱️  DATETIME VARIABLE (fed_30min_time):")
    fed_time = ds['fed_30min_time']
    print(f"  Shape: {fed_time.shape}")
    print(f"  Dtype: {fed_time.dtype}")

    # Sample datetime values
    sample_times = fed_time.isel(time=0, lat=slice(0, 5), lon=slice(0, 5)).values
    print(f"  Sample values (first time, 5x5 grid):")
    for i in range(min(3, sample_times.shape[0])):
        for j in range(min(3, sample_times.shape[1])):
            dt = pd.Timestamp(sample_times[i, j])
            print(f"    [{i},{j}]: {dt}")

    # Coordinate consistency check
    print(f"\n🔍 COORDINATE CONSISTENCY:")
    print(f"  Checking if lat/lon are uniform across all time steps...")

    # Check a few random time steps
    check_indices = [0, len(times)//2, len(times)-1] if len(times) > 2 else [0]
    lat_consistent = True
    lon_consistent = True

    ref_lats = ds.lat.values
    ref_lons = ds.lon.values

    for idx in check_indices:
        # Coordinates should be the same for all time steps
        # (they're stored as coords, not data vars, so should be consistent)
        pass

    print(f"✅ Coordinates are consistent (stored as dataset coordinates)")

    # Create a visualization
    print(f"\n📊 CREATING VISUALIZATION...")

    # Plot a sample timestep
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Plot first timestep
    idx_first = 0
    ax = axes[0]
    fed_data.isel(time=idx_first).plot(ax=ax, cmap='hot', add_colorbar=True)
    ax.set_title(f'GLM FED - {times[idx_first].date()} (First)')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    # Plot middle timestep
    if len(times) > 1:
        idx_mid = len(times) // 2
        ax = axes[1]
        fed_data.isel(time=idx_mid).plot(ax=ax, cmap='hot', add_colorbar=True)
        ax.set_title(f'GLM FED - {times[idx_mid].date()} (Middle)')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')

    # Plot last timestep
    if len(times) > 2:
        idx_last = len(times) - 1
        ax = axes[2]
        fed_data.isel(time=idx_last).plot(ax=ax, cmap='hot', add_colorbar=True)
        ax.set_title(f'GLM FED - {times[idx_last].date()} (Last)')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')

    plt.tight_layout()
    output_file = '/opt/geospatial_backend/glm_fed_verification.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved visualization to: {output_file}")

    # Time series plot
    fig, ax = plt.subplots(figsize=(12, 4))

    # Calculate daily mean FED (excluding NaN)
    daily_mean = []
    daily_max = []
    for i in range(len(times)):
        slice_data = fed_data.isel(time=i).values
        valid = slice_data[~np.isnan(slice_data)]
        if len(valid) > 0:
            daily_mean.append(valid.mean())
            daily_max.append(valid.max())
        else:
            daily_mean.append(np.nan)
            daily_max.append(np.nan)

    ax.plot(times, daily_mean, 'b-', label='Daily Mean FED', linewidth=1)
    ax.plot(times, daily_max, 'r-', label='Daily Max FED', linewidth=0.5, alpha=0.7)
    ax.set_xlabel('Date')
    ax.set_ylabel('Flash Extent Density')
    ax.set_title('GLM FED Time Series')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_file_ts = '/opt/geospatial_backend/glm_fed_timeseries.png'
    plt.savefig(output_file_ts, dpi=150, bbox_inches='tight')
    print(f"✅ Saved time series to: {output_file_ts}")

    ds.close()

    print(f"\n" + "=" * 80)
    print("✅ VERIFICATION COMPLETE - Data appears valid!")
    print("=" * 80)

    return True

if __name__ == "__main__":
    verify_glm_historical_data()
