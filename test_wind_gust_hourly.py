#!/usr/bin/env python3
"""
Test downloading hourly wind gust data and computing daily maximum.
This is the correct approach for insurance risk assessment.
"""
import sys
from pathlib import Path
from datetime import date

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.wind_gust_flow import wind_gust_hourly_flow

# Test with 2020-06-30 (Ciclone Bomba)
test_date = date(2020, 6, 30)

print("="*80)
print("TESTING HOURLY WIND GUST DOWNLOAD")
print("="*80)
print(f"Date: {test_date}")
print(f"Source: reanalysis-era5-land (hourly)")
print(f"Variable: 10m_wind_gust (instantaneous gust)")
print(f"Processing: Daily maximum from 24 hourly values")
print(f"Output: Daily max wind gust in km/h (for insurance)")
print("="*80)
print()

# Run the flow
result = wind_gust_hourly_flow(
    start_date=test_date,
    end_date=test_date,
    skip_existing=False  # Force reprocess
)

print()
print("="*80)
print("TEST COMPLETE")
print("="*80)

if result and len(result) > 0:
    print(f"Created: {result[0]}")

    # Verify values
    import xarray as xr
    import numpy as np
    import rasterio

    print("\nVerifying values...")

    # Load raw verification data (hourly u/v components)
    raw_ds = xr.open_dataset('/tmp/wind_verification/data_0.nc')
    u = raw_ds['u10']
    v = raw_ds['v10']

    # Compute wind speed from u/v components
    wind_speed = np.sqrt(u**2 + v**2)
    time_dim = 'valid_time' if 'valid_time' in wind_speed.dims else 'time'
    daily_max_speed = wind_speed.max(dim=time_dim)

    # Sample at Porto Alegre
    lat, lon = -30.0, -51.0
    expected_speed = float(daily_max_speed.sel(latitude=lat, longitude=lon, method='nearest').values)
    expected_speed_kmh = expected_speed * 3.6

    # Read new GeoTIFF (wind GUST, should be higher than wind speed)
    with rasterio.open(result[0]) as src:
        for val in src.sample([(lon, lat)]):
            gust_val = val[0]

    print(f"\nAt Porto Alegre ({lat}, {lon}):")
    print(f"  Expected wind SPEED max: {expected_speed:.4f} m/s = {expected_speed_kmh:.4f} km/h")
    print(f"  Downloaded wind GUST max: {gust_val:.4f} km/h")
    print(f"  Gust/Speed ratio: {gust_val / expected_speed_kmh:.2f}x")
    print()
    print(f"  Note: Wind gusts are typically 1.3-1.5x higher than sustained wind")
    print(f"        Gusts represent the actual peak force that damages structures")

    if gust_val > expected_speed_kmh:
        print(f"\n✓ CORRECT! Wind gust ({gust_val:.1f} km/h) > wind speed ({expected_speed_kmh:.1f} km/h)")
        print(f"  This is expected and correct for insurance risk assessment")
    else:
        print(f"\n? Unexpected: Gust should be higher than sustained wind speed")

else:
    print("No files were created")
