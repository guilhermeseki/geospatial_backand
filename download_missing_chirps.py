#!/usr/bin/env python3
"""
Download missing CHIRPS data using the updated URL structure
"""
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import sys
import os

# Add app to path
sys.path.insert(0, '/opt/geospatial_backend')

from app.workflows.data_processing.precipitation_flow import precipitation_batch_flow
from app.workflows.data_processing.schemas import DataSource
from app.config.settings import get_settings

def find_missing_dates():
    """Find missing CHIRPS dates"""
    settings = get_settings()
    chirps_dir = Path(settings.DATA_DIR) / "chirps"

    # Get existing files
    existing_files = sorted(chirps_dir.glob("chirps_*.tif"))
    existing_dates = set()

    for f in existing_files:
        try:
            date_str = f.stem.split('_')[1]
            existing_dates.add(pd.to_datetime(date_str, format='%Y%m%d').date())
        except:
            pass

    if not existing_dates:
        print("No existing files found!")
        return []

    # Find missing dates
    start_date = min(existing_dates)
    end_date = date(2025, 10, 31)  # Latest available on server

    missing_dates = []
    current = start_date
    while current <= end_date:
        if current not in existing_dates:
            missing_dates.append(current)
        current += timedelta(days=1)

    return missing_dates

def main():
    print("=" * 80)
    print("CHIRPS Missing Data Download")
    print("=" * 80)
    print()

    # Find missing dates
    missing_dates = find_missing_dates()

    if not missing_dates:
        print("✓ No missing dates found!")
        return

    print(f"Found {len(missing_dates)} missing dates")
    print(f"Date range: {missing_dates[0]} to {missing_dates[-1]}")
    print()

    # Group by year
    by_year = {}
    for d in missing_dates:
        if d.year not in by_year:
            by_year[d.year] = []
        by_year[d.year].append(d)

    print("Missing by year:")
    for year in sorted(by_year.keys()):
        print(f"  {year}: {len(by_year[year])} days")
    print()

    # Download missing data
    response = input(f"Download {len(missing_dates)} missing files? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return

    print()
    print("Starting download...")
    print()

    # Use the precipitation_batch_flow to download
    start_date = missing_dates[0]
    end_date = missing_dates[-1]

    result = precipitation_batch_flow(
        source=DataSource.CHIRPS,
        start_date=start_date,
        end_date=end_date,
        create_historical=False  # Don't rebuild historical yet
    )

    print()
    print("=" * 80)
    print("Download Complete!")
    print("=" * 80)
    print(f"Processed: {len(result) if result else 0} files")
    print()
    print("Next steps:")
    print("1. Verify the downloaded files")
    print("2. Rebuild yearly historical NetCDF files if needed")
    print("3. Restart the API to reload datasets")

if __name__ == "__main__":
    main()
