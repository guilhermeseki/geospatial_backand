#!/usr/bin/env python3
"""
ERA5 Wind Data Test Script
Tests wind data download with a small date range (1 month) before running full backfill
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date

if __name__ == "__main__":
    # Test with just one month of recent data
    start_date = date(2024, 10, 1)
    end_date = date(2024, 10, 31)

    print("="*80)
    print("ERA5 WIND DATA DOWNLOAD - TEST RUN")
    print("="*80)
    print(f"Date range: {start_date} to {end_date} (1 month)")
    print(f"Variables: 10m_wind_speed (daily_mean)")
    print(f"Region: Latin America")
    print(f"This is a TEST to verify wind processing works")
    print("="*80)
    print()

    try:
        # Test with just wind speed mean for one month
        era5_land_daily_flow(
            batch_days=31,
            start_date=start_date,
            end_date=end_date,
            variables_config=[
                {'variable': '10m_wind_speed', 'statistic': 'daily_mean'},
            ]
        )

        print(f"\n{'='*80}")
        print(f"✓ TEST SUCCESSFUL!")
        print(f"{'='*80}")
        print(f"Wind speed data processed successfully")
        print(f"Check /mnt/workwork/geoserver_data/wind_speed/ for GeoTIFF files")
        print(f"Check /mnt/workwork/geoserver_data/wind_speed_hist/ for NetCDF")
        print(f"\nIf this worked, you can now run: python app/run_wind.py")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"✗ TEST FAILED!")
        print(f"{'='*80}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*80}")
