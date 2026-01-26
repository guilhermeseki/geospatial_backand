#!/usr/bin/env python3
"""
Test downloading maximum_10m_wind_speed directly from CDS API.
This should give us the correct daily maximum wind speed.
"""
import sys
from pathlib import Path
from datetime import date

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from app.config.settings import get_settings

settings = get_settings()

# Test with 2020-06-30 (Ciclone Bomba)
test_date = date(2020, 6, 30)

print("="*80)
print("TESTING CORRECT WIND GUST DOWNLOAD (FOR INSURANCE)")
print("="*80)
print(f"Date: {test_date}")
print(f"Variable: maximum_10m_wind_gust_since_previous_post_processing")
print(f"Statistic: daily_maximum")
print(f"Note: Wind GUST (not average) - more accurate for damage assessment")
print("="*80)
print()

# Process using the updated flow
result = era5_land_daily_flow(
    start_date=test_date,
    end_date=test_date,
    variables_config=[
        {'variable': 'maximum_10m_wind_gust_since_previous_post_processing', 'statistic': 'daily_maximum'}
    ],
    skip_historical_merge=True  # Just test GeoTIFF creation for now
)

print()
print("="*80)
print("TEST COMPLETE")
print("="*80)
if result and len(result) > 0:
    print(f"Processed files: {len(result)}")
    print(f"\nCreated: {result[0]}")

    # Compare with raw download
    import xarray as xr
    import numpy as np
    import rasterio

    print("\nVerifying values...")

    # Load raw verification data
    raw_ds = xr.open_dataset('/tmp/wind_verification/data_0.nc')
    u = raw_ds['u10']
    v = raw_ds['v10']
    wind_speed = np.sqrt(u**2 + v**2)
    time_dim = 'valid_time' if 'valid_time' in wind_speed.dims else 'time'
    daily_max = wind_speed.max(dim=time_dim)

    # Sample at Porto Alegre
    lat, lon = -30.0, -51.0
    expected_val = float(daily_max.sel(latitude=lat, longitude=lon, method='nearest').values)
    expected_kmh = expected_val * 3.6

    # Read new GeoTIFF
    with rasterio.open(result[0]) as src:
        for val in src.sample([(lon, lat)]):
            new_val = val[0]

    print(f"\nAt Porto Alegre ({lat}, {lon}):")
    print(f"  Expected (from hourly max): {expected_val:.4f} m/s = {expected_kmh:.4f} km/h")
    print(f"  New GeoTIFF: {new_val:.4f} km/h")
    print(f"  Match: {abs(new_val - expected_kmh) < 0.1} (diff: {abs(new_val - expected_kmh):.4f} km/h)")

    if abs(new_val - expected_kmh) < 0.1:
        print("\n✓ SUCCESS! New wind data matches expected daily maximum!")
    else:
        print(f"\n✗ MISMATCH: Expected {expected_kmh:.2f} km/h, got {new_val:.2f} km/h")
        print(f"  Ratio: {new_val / expected_kmh:.4f}")
else:
    print("No files were created (may already exist)")
