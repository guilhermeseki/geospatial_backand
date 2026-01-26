#!/usr/bin/env python3
"""
Download wind gust data for 2025 (up to ERA5 data availability).
Uses the corrected ERA5 daily statistics flow.
"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.era5_wind_gust_daily_stats_flow import era5_wind_gust_daily_stats_flow

def main():
    """Download 2025 wind gust data."""

    # ERA5 has 5-7 day lag, so download up to ~7 days ago
    # Today is 2026-01-09, so available up to about 2026-01-02
    start_date = date(2025, 1, 1)
    end_date = date(2026, 1, 2)  # Adjust based on ERA5 availability

    print("=" * 80)
    print("DOWNLOADING WIND GUST DATA FOR 2025")
    print("=" * 80)
    print(f"Date range: {start_date} to {end_date}")
    print(f"Dataset: ERA5 daily statistics (maximum wind gust)")
    print("=" * 80)
    print()

    result = era5_wind_gust_daily_stats_flow(
        start_date=start_date,
        end_date=end_date,
        skip_existing=True
    )

    if result:
        print(f"\n✓ Successfully created {len(result)} files")
    else:
        print(f"\n✓ All files already exist or no new data available")

    return 0

if __name__ == "__main__":
    sys.exit(main())
