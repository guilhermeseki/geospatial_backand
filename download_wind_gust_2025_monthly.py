#!/usr/bin/env python3
"""
Download wind gust data for 2025 month by month (avoids CDS cost limits).
"""
import sys
from pathlib import Path
from datetime import date
import calendar

sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.era5_wind_gust_daily_stats_flow import era5_wind_gust_daily_stats_flow

def main():
    """Download 2025 wind gust data month by month."""

    print("=" * 80)
    print("DOWNLOADING WIND GUST DATA FOR 2025 (MONTHLY)")
    print("=" * 80)
    print()

    # Process month by month to avoid CDS cost limits
    # ERA5 has 5-7 day lag, so only up to early January 2026
    months = [
        (2025, 1),   # January 2025
        (2025, 2),   # February 2025
        (2025, 3),   # March 2025
        (2025, 4),   # April 2025
        (2025, 5),   # May 2025
        (2025, 6),   # June 2025
        (2025, 7),   # July 2025
        (2025, 8),   # August 2025
        (2025, 9),   # September 2025
        (2025, 10),  # October 2025
        (2025, 11),  # November 2025
        (2025, 12),  # December 2025
        (2026, 1),   # January 2026 (partial - up to 2nd)
    ]

    total_files = 0
    failed_months = []

    for year, month in months:
        if year == 2026 and month == 1:
            # Only up to Jan 2nd for 2026
            start_date = date(year, month, 1)
            end_date = date(year, month, 2)
        else:
            start_date = date(year, month, 1)
            _, last_day = calendar.monthrange(year, month)
            end_date = date(year, month, last_day)

        print(f"\n{'='*80}")
        print(f"PROCESSING {calendar.month_name[month]} {year}")
        print(f"{'='*80}")

        try:
            result = era5_wind_gust_daily_stats_flow(
                start_date=start_date,
                end_date=end_date,
                skip_existing=True
            )

            if result:
                total_files += len(result)
                print(f"✓ {calendar.month_name[month]} {year}: Created {len(result)} files")
            else:
                print(f"✓ {calendar.month_name[month]} {year}: All files already exist")

        except Exception as e:
            print(f"✗ {calendar.month_name[month]} {year} FAILED: {e}")
            failed_months.append(f"{calendar.month_name[month]} {year}")
            continue

    print(f"\n{'='*80}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"Total new files created: {total_files}")

    if failed_months:
        print(f"Failed months: {', '.join(failed_months)}")
        return 1
    else:
        print("✓ All months processed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
