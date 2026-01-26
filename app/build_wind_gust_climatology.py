#!/usr/bin/env python3
"""
Build complete wind gust climatology (1991-2020):
- Downloads daily max wind gust from ERA5 sis-agrometeorological-indicators
- Creates yearly NetCDF files
- Consolidates into single climatology file
- Cleans up old data
"""
import sys
from pathlib import Path
from datetime import date
from prefect import flow

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config.settings import get_settings
from app.workflows.data_processing.wind_gust_daily_flow import (
    download_and_process_wind_gust_daily
)


@flow(name="build_wind_gust_climatology_1991_2020")
def build_wind_gust_climatology(start_year: int = 1991, end_year: int = 2020):
    """
    Build complete wind gust climatology from ERA5 data.

    Downloads and processes daily maximum wind gust for 1991-2020,
    then consolidates into climatology directory.
    """
    settings = get_settings()

    print("="*80)
    print("BUILD WIND GUST CLIMATOLOGY: 1991-2020")
    print("="*80)
    print()
    print("Data source: ERA5 sis-agrometeorological-indicators")
    print("Variable: 10m_wind_gust")
    print("Statistic: maximum (daily)")
    print("Period: 1991-2020 (WMO climatology reference period)")
    print()
    print("This will:")
    print("  1. Download daily max wind gust from ERA5 (1991-2020)")
    print("  2. Create daily GeoTIFF files")
    print("  3. Create yearly NetCDF files")
    print("  4. Consolidate into wind_gust_1991-2020.nc")
    print("  5. Clean up old data to save space")
    print()

    # Download and process all data year by year
    for year in range(start_year, end_year + 1):
        print(f"\n{'='*80}")
        print(f"Processing year: {year}")
        print(f"{'='*80}\n")

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        try:
            # Use existing flow to download and process
            download_and_process_wind_gust_daily(
                start_date=start_date,
                end_date=end_date
            )
            print(f"✓ Year {year} completed")
        except Exception as e:
            print(f"✗ Year {year} failed: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "="*80)
    print("DOWNLOAD AND PROCESSING COMPLETE")
    print("="*80)
    print()
    print("Next step: Run consolidation script")
    print("  python app/consolidate_wind_gust_climatology.py")
    print("="*80)


def main():
    build_wind_gust_climatology(start_year=1991, end_year=2020)


if __name__ == "__main__":
    main()
