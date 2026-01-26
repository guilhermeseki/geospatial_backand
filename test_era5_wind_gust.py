#!/usr/bin/env python3
"""
Test downloading hourly wind gust data from FULL ERA5 (not ERA5-Land).
This is the correct dataset for wind gust data.
"""
import sys
from pathlib import Path
from datetime import date

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.era5_wind_gust_flow import era5_wind_gust_flow

# Test with 2020-06-30 (Ciclone Bomba)
test_date = date(2020, 6, 30)

print("="*80)
print("TESTING ERA5 WIND GUST DOWNLOAD (FULL ERA5)")
print("="*80)
print(f"Date: {test_date}")
print(f"Source: reanalysis-era5-single-levels (FULL ERA5 - has wind gust!)")
print(f"Variable: instantaneous_10m_wind_gust")
print(f"Processing: Daily maximum from 24 hourly values")
print(f"Output: Daily max wind gust in km/h (for insurance)")
print("="*80)
print()

# Run the flow
result = era5_wind_gust_flow(
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

    # Read new GeoTIFF
    with rasterio.open(result[0]) as src:
        data = src.read(1)
        valid_data = data[~np.isnan(data)]

        if len(valid_data) > 0:
            print(f"\nWind Gust Statistics (2020-06-30 - Ciclone Bomba):")
            print(f"  Min: {valid_data.min():.2f} km/h")
            print(f"  Mean: {valid_data.mean():.2f} km/h")
            print(f"  Max: {valid_data.max():.2f} km/h")
            print(f"  90th percentile: {np.percentile(valid_data, 90):.2f} km/h")

            # Sample at Porto Alegre
            lat, lon = -30.0, -51.0
            for val in src.sample([(lon, lat)]):
                gust_val = val[0]

            print(f"\nAt Porto Alegre ({lat}, {lon}):")
            print(f"  Wind gust: {gust_val:.2f} km/h")

            # Expected range for Ciclone Bomba
            if 80 <= gust_val <= 150:
                print(f"  ✓ Value in expected range for major storm event")
            elif gust_val > 150:
                print(f"  ⚠ Very high value - extreme weather event")
            else:
                print(f"  ? Lower than expected for Ciclone Bomba")

            print("\n✓ SUCCESS! Downloaded ERA5 wind gust data")
            print("  This is the correct dataset for insurance risk assessment")

else:
    print("No files were created")
