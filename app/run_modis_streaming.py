#!/usr/bin/env python3
"""
MODIS NDVI Backfill using Streaming Approach
Process ONE composite at a time - no memory issues!
"""
from app.workflows.data_processing.ndvi_flow_streaming import modis_streaming_flow
from datetime import date

if __name__ == "__main__":
    # MODIS data from 2015 to present
    overall_start = date(2015, 1, 1)
    overall_end = date.today()

    print("="*80)
    print("MODIS NDVI BACKFILL (STREAMING - MEMORY EFFICIENT)")
    print("="*80)
    print(f"Date range: {overall_start} to {overall_end}")
    print(f"Source: Microsoft Planetary Computer (100% FREE!)")
    print(f"Strategy: Process ONE composite at a time")
    print(f"  - No huge NetCDF files")
    print(f"  - No memory overflow")
    print(f"  - No expired URLs")
    print("="*80)
    print()

    total_files = 0

    # Process year by year
    current_year = overall_start.year
    end_year = overall_end.year

    while current_year <= end_year:
        year_start = date(current_year, 1, 1)
        year_end = date(current_year, 12, 31)

        if year_end > overall_end:
            year_end = overall_end

        print(f"\n{'='*80}")
        print(f"Processing Year: {current_year}")
        print(f"  Date range: {year_start} to {year_end}")
        print(f"{'='*80}\n")

        try:
            results = modis_streaming_flow(
                start_date=year_start,
                end_date=year_end,
                batch_days=16  # MODIS composites are 16-day periods
            )

            total_files += len(results)
            print(f"\n✓ Year {current_year}: Created {len(results)} GeoTIFF files")

        except Exception as e:
            print(f"\n✗ Year {current_year} failed: {e}")
            print(f"  Continuing with next year...")
            import traceback
            traceback.print_exc()

        current_year += 1

    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Total GeoTIFF files created: {total_files}")
    print(f"Years processed: {overall_start.year} to {end_year}")
    print(f"Storage location: /mnt/workwork/geoserver_data/ndvi_modis/")
    print(f"{'='*80}")
