#!/usr/bin/env python3
"""
Re-download 2023 and 2025 temperature data with corrected reprojection.
This uses a fresh Python process to ensure the reprojection fix is applied.
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date, timedelta

# ERA5-Land has ~5-7 day lag
today = date.today()

print('='*80)
print('DOWNLOADING 2023 and 2025 TEMPERATURE DATA (WITH REPROJECTION FIX)')
print('='*80)
print('This will ensure all files have consistent 416x416 dimensions')
print('='*80)
print()

# Download 2023
print('--- YEAR 2023 ---')
print('Downloading temp_max, temp_min, temp for all of 2023')
print()

era5_land_daily_flow(
    batch_days=31,
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31),
    variables_config=[
        {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
        {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
        {'variable': '2m_temperature', 'statistic': 'daily_mean'},
    ],
    skip_historical_merge=True
)

print()
print('--- YEAR 2025 ---')
print(f'Downloading temp_max, temp_min, temp from 2025-01-01 to {today - timedelta(days=7)}')
print()

era5_land_daily_flow(
    batch_days=31,
    start_date=date(2025, 1, 1),
    end_date=today - timedelta(days=7),
    variables_config=[
        {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
        {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
        {'variable': '2m_temperature', 'statistic': 'daily_mean'},
    ],
    skip_historical_merge=True
)

print()
print('='*80)
print('✅ 2023 and 2025 data processing completed')
print('='*80)
print()
print('Next steps:')
print('1. Build historical NetCDF files: python app/build_temperature_historical.py')
print('2. Restart API: sudo systemctl restart geospatial-backend')
print('3. Test temperature endpoints')
print('='*80)
