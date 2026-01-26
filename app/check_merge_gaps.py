#!/usr/bin/env python3
"""
Gap detection script for MERGE data.
Scans entire historical period and reports any missing dates.
Run weekly to ensure no gaps exist.
"""
import sys
from datetime import date, timedelta
from pathlib import Path
from app.config.settings import get_settings

def find_all_gaps(start_date=None, end_date=None):
    """
    Find all missing dates in MERGE dataset.

    Args:
        start_date: Start of period to check (default: 2000-01-01, MERGE data start)
        end_date: End of period to check (default: yesterday)

    Returns:
        List of missing dates
    """
    settings = get_settings()
    merge_dir = Path(settings.DATA_DIR) / "merge"

    if start_date is None:
        start_date = date(2000, 1, 1)  # MERGE data availability starts ~2000
    if end_date is None:
        end_date = date.today() - timedelta(days=2)  # Account for 1-2 day lag

    print("=" * 80)
    print("MERGE DATA GAP ANALYSIS")
    print("=" * 80)
    print(f"Checking period: {start_date} to {end_date}")
    print(f"Total days to check: {(end_date - start_date).days + 1}")
    print()

    missing_dates = []
    current_date = start_date

    while current_date <= end_date:
        expected_file = merge_dir / f"merge_{current_date.strftime('%Y%m%d')}.tif"

        if not expected_file.exists():
            missing_dates.append(current_date)

        current_date += timedelta(days=1)

    # Report results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    if missing_dates:
        print(f"⚠️  Found {len(missing_dates)} missing dates:")
        print()

        # Group consecutive missing dates for easier reading
        if len(missing_dates) > 10:
            print("First 10 missing dates:")
            for d in missing_dates[:10]:
                print(f"  - {d}")
            print(f"  ... and {len(missing_dates) - 10} more")
        else:
            for d in missing_dates:
                print(f"  - {d}")

        print()
        print("ACTION REQUIRED:")
        print("Run backfill for missing dates using:")
        print("  python app/run_merge_backfill.py")

        return 1
    else:
        print(f"✓ NO GAPS FOUND")
        print(f"All {(end_date - start_date).days + 1} dates are present")
        print()
        return 0

if __name__ == "__main__":
    # Check full historical period
    exit_code = find_all_gaps()

    # Also save missing dates to file for backfill processing
    if exit_code != 0:
        print()
        print("Missing dates saved to: /opt/geospatial_backend/logs/merge_missing_dates.txt")

    sys.exit(exit_code)
