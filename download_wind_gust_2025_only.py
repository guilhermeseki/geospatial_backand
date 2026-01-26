#!/usr/bin/env python3
"""
Download wind gust data for 2025 only (one year at a time like before).
"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.era5_wind_gust_daily_stats_flow import era5_wind_gust_daily_stats_flow

def main():
    """Download 2025 wind gust data (same approach as 2015-2024 rebuild)."""

    print("=" * 80)
    print("DOWNLOADING WIND GUST DATA FOR 2025")
    print("=" * 80)
    print()

    # Download 2025 only (365 days, same as before)
    start_date = date(2025, 1, 1)
    end_date = date(2025, 12, 31)

    result = era5_wind_gust_daily_stats_flow(
        start_date=start_date,
        end_date=end_date,
        skip_existing=True
    )

    if result:
        print(f"\n✓ Successfully created {len(result)} files for 2025")
    else:
        print(f"\n✓ All 2025 files already exist")

    return 0

if __name__ == "__main__":
    sys.exit(main())
