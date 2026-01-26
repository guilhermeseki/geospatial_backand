#!/usr/bin/env python3
"""
Test script to verify ERA5 reprojection fix works correctly.
Downloads and processes ONE date to check dimensions.
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date
import rioxarray as rxr

print('='*80)
print('TESTING REPROJECTION FIX - Single Date')
print('='*80)
print()

# Download just one date from 2023
test_date = date(2023, 1, 15)

print(f'Testing with date: {test_date}')
print('Variable: temp_max (daily_maximum)')
print()

# Run the flow for just this one date
era5_land_daily_flow(
    batch_days=1,
    start_date=test_date,
    end_date=test_date,
    variables_config=[
        {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
    ],
    skip_historical_merge=True
)

print()
print('='*80)
print('VERIFICATION: Checking file dimensions')
print('='*80)

# Check the created file
test_file = f'/mnt/workwork/geoserver_data/temp_max/temp_max_20230115.tif'
print(f'Reading: {test_file}')

try:
    da = rxr.open_rasterio(test_file)
    print(f'Shape: {da.shape}')
    print(f'Expected: (1, 416, 416)')

    if da.shape == (1, 416, 416):
        print('✅ SUCCESS - Dimensions are correct!')
    else:
        print(f'❌ FAILED - Wrong dimensions: {da.shape}')

except FileNotFoundError:
    print('❌ FAILED - File was not created')
except Exception as e:
    print(f'❌ ERROR - {e}')

print('='*80)
