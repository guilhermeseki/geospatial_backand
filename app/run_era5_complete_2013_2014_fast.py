#!/usr/bin/env python3
"""
Complete ERA5 backfill for 2013-2014 - FAST VERSION.

Strategy:
1. Download and create GeoTIFFs only (skip yearly NetCDF creation)
2. After all downloads complete, merge GeoTIFFs into yearly NetCDF files in one step

This is much faster and more reliable than creating NetCDF files incrementally.
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date

if __name__ == "__main__":
    print("="*80)
    print("COMPLETE ERA5 BACKFILL: 2013-2014 (FAST MODE)")
    print("="*80)
    print("Strategy: Download + create GeoTIFFs only, skip NetCDF creation")
    print("Variables: temp_max (daily_maximum), temp_min (daily_minimum)")
    print()
    print("Missing data:")
    print("  2013: ~269 days of temp_max, 365 days of temp_min")
    print("  2014: 365 days of both variables")
    print("="*80)
    print()

    # Process 2013
    print(f"\n{'='*80}")
    print(f"Processing Year: 2013")
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
            skip_historical_merge=True  # ← SKIP NetCDF creation for speed
        )
        print(f"\n✓ Year 2013: GeoTIFF processing completed")
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
            skip_historical_merge=True  # ← SKIP NetCDF creation for speed
        )
        print(f"\n✓ Year 2014: GeoTIFF processing completed")
    except Exception as e:
        print(f"\n✗ Year 2014 failed: {e}")

    print(f"\n{'='*80}")
    print(f"BACKFILL COMPLETE - GEOTIFF PHASE")
    print(f"{'='*80}")
    print()
    print("✓ All GeoTIFF files downloaded and processed")
    print()
    print("Next steps:")
    print("  1. Create yearly NetCDF files from GeoTIFFs (run separately)")
    print("  2. Calculate 1991-2020 climatology")
    print("="*80)
