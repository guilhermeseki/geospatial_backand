#!/usr/bin/env python3
"""
Complete ERA5 backfill for 2013-2014.

Downloads missing data:
- 2013: Complete temp_max (days 97-365) and all temp_min (days 1-365)
- 2014: All temp_max and temp_min (days 1-365)
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date

if __name__ == "__main__":
    print("="*80)
    print("COMPLETE ERA5 BACKFILL: 2013-2014")
    print("="*80)
    print("Variables: temp_max (daily_maximum), temp_min (daily_minimum)")
    print()
    print("Missing data:")
    print("  2013: ~269 days of temp_max, 365 days of temp_min")
    print("  2014: 365 days of both variables")
    print("="*80)
    print()

    # Process 2013 (will skip already downloaded temp_max files)
    print(f"\n{'='*80}")
    print(f"Processing Year: 2013")
    print(f"  The flow will automatically skip existing temp_max files (days 1-96)")
    print(f"{'='*80}\n")

    try:
        era5_land_daily_flow(
            batch_days=31,
            start_date=date(2013, 1, 1),
            end_date=date(2013, 12, 31),
            variables_config=[
                {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
                {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
            ],
            skip_historical_merge=False  # Create yearly NetCDF after completion
        )
        print(f"\n✓ Year 2013: Processing completed")
    except Exception as e:
        print(f"\n✗ Year 2013 failed: {e}")
        print(f"  Continuing with 2014...")

    # Process 2014
    print(f"\n{'='*80}")
    print(f"Processing Year: 2014")
    print(f"{'='*80}\n")

    try:
        era5_land_daily_flow(
            batch_days=31,
            start_date=date(2014, 1, 1),
            end_date=date(2014, 12, 31),
            variables_config=[
                {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
                {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
            ],
            skip_historical_merge=False  # Create yearly NetCDF after completion
        )
        print(f"\n✓ Year 2014: Processing completed")
    except Exception as e:
        print(f"\n✗ Year 2014 failed: {e}")

    print(f"\n{'='*80}")
    print(f"BACKFILL COMPLETION SUMMARY")
    print(f"{'='*80}")
    print("Next step: Create yearly NetCDF files for 1991-2012")
    print("  (Years 2013-2014 NetCDFs created automatically)")
    print("="*80)
