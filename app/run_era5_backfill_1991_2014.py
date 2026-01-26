#!/usr/bin/env python3
"""
ERA5 Land Daily Data Backfill: 1991-2014
Downloads temperature data for the missing years needed for 1991-2020 climatology.

This will download:
- temp_max (daily_maximum)
- temp_min (daily_minimum)

For years 1991-2014 to complete the 30-year climatology reference period.
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date

if __name__ == "__main__":
    # Backfill period: 1991-2014
    start_year = 1991
    end_year = 2014

    print("="*80)
    print("ERA5 LAND HISTORICAL BACKFILL (1991-2014)")
    print("="*80)
    print(f"Years to download: {start_year} to {end_year} ({end_year - start_year + 1} years)")
    print(f"Variables: 2m_temperature (daily_maximum, daily_minimum)")
    print(f"Region: Brazil (ERA5-Land)")
    print(f"Purpose: Complete 1991-2020 climatology reference period")
    print(f"Strategy: Process one year at a time to avoid timeouts")
    print("="*80)
    print()
    print("⚠️  NOTE: This will take several hours to complete!")
    print("    Each year downloads ~730 MB of data")
    print(f"    Total estimated download: ~{(end_year - start_year + 1) * 0.73:.1f} GB")
    print("="*80)
    print()

    # Process year by year
    for current_year in range(start_year, end_year + 1):
        year_start = date(current_year, 1, 1)
        year_end = date(current_year, 12, 31)

        print(f"\n{'='*80}")
        print(f"Processing Year: {current_year} ({current_year - start_year + 1}/{end_year - start_year + 1})")
        print(f"  Date range: {year_start} to {year_end}")
        print(f"{'='*80}\n")

        try:
            # Run the flow for this year
            # Only download temp_max and temp_min (not temp_mean)
            era5_land_daily_flow(
                batch_days=31,  # Download 31 days per CDS request (monthly chunks)
                start_date=year_start,
                end_date=year_end,
                variables_config=[
                    {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
                    {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
                ],
                skip_historical_merge=True  # Just download + create GeoTIFFs, merge to yearly NetCDF later
            )

            print(f"\n✓ Year {current_year}: Processing completed")

        except Exception as e:
            print(f"\n✗ Year {current_year} failed: {e}")
            print(f"  You can re-run this script - it will skip already downloaded data")
            print(f"  Continuing with next year...")
            continue

    print(f"\n{'='*80}")
    print(f"BACKFILL COMPLETE")
    print(f"{'='*80}")
    print(f"Downloaded years: {start_year} to {end_year}")
    print()
    print("Next steps:")
    print("  1. Merge daily GeoTIFFs into yearly NetCDF files (if needed)")
    print("  2. Run climatology calculation:")
    print("     python app/calculate_temperature_climatology.py --all --start-year 1991 --end-year 2020")
    print(f"{'='*80}")
