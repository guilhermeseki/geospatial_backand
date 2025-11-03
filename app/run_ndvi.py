#!/usr/bin/env python3
"""
NDVI MODIS Data Download Script
Downloads MODIS NDVI data (250m, 16-day composites) for Latin America
Uses Microsoft Planetary Computer (100% FREE, no authentication!)

PROCESSES YEAR-BY-YEAR to avoid timeouts from too many composites per batch
"""
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date

if __name__ == "__main__":
    # MODIS data from 2015 to present
    overall_start = date(2015, 1, 1)
    overall_end = date.today()

    print("="*80)
    print("MODIS NDVI DATA DOWNLOAD (YEAR-BY-YEAR)")
    print("="*80)
    print(f"Overall range: {overall_start} to {overall_end}")
    print(f"Source: MODIS MOD13Q1.061 (250m resolution, 16-day composites)")
    print(f"Provider: Microsoft Planetary Computer (FREE!)")
    print(f"Region: Latin America")
    print(f"Strategy: Process one year at a time to avoid timeouts")
    print("="*80)
    print()

    total_processed = 0

    # Process year by year
    current_year = overall_start.year
    end_year = overall_end.year

    while current_year <= end_year:
        # Define year boundaries
        year_start = date(current_year, 1, 1)
        year_end = date(current_year, 12, 31)

        # Don't go past overall_end
        if year_end > overall_end:
            year_end = overall_end

        print(f"\n{'='*80}")
        print(f"Processing Year: {current_year}")
        print(f"  Date range: {year_start} to {year_end}")
        print(f"{'='*80}\n")

        try:
            # Run the flow for this year
            # batch_days=16 means ~1 composite per download (16-day interval)
            # This reduces memory usage and timeout risk
            result = ndvi_data_flow(
                start_date=year_start,
                end_date=year_end,
                sources=['modis'],
                batch_days=16  # Smaller batches = fewer composites per request
            )

            total_processed += len(result)
            print(f"\n✓ Year {current_year}: Processed {len(result)} files")

        except Exception as e:
            print(f"\n✗ Year {current_year} failed: {e}")
            print(f"  Continuing with next year...")

        current_year += 1

    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Total files processed: {total_processed}")
    print(f"Years processed: {overall_start.year} to {end_year}")
    print(f"{'='*80}")