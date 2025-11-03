#!/usr/bin/env python3
"""
ERA5 Land Daily Data Download Script
Downloads temperature data (daily_maximum, daily_minimum, daily_mean) for Latin America

PROCESSES YEAR-BY-YEAR to avoid timeouts and CDS request limits
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date, timedelta

if __name__ == "__main__":
    # ERA5-Land has ~5-7 day lag, so end date is 7 days before today
    today = date.today()
    overall_end = today - timedelta(days=7)

    # Download from 2015 to present
    overall_start = date(2015, 1, 1)

    print("="*80)
    print("ERA5 LAND DAILY DATA DOWNLOAD (YEAR-BY-YEAR)")
    print("="*80)
    print(f"Overall range: {overall_start} to {overall_end}")
    print(f"Total days: {(overall_end - overall_start).days + 1}")
    print(f"Variables: 2m_temperature (daily_maximum, daily_minimum, daily_mean)")
    print(f"Region: Latin America")
    print(f"Strategy: Process one year at a time to avoid timeouts")
    print("="*80)
    print()

    total_processed = {'daily_maximum': 0, 'daily_minimum': 0, 'daily_mean': 0}

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
            # batch_days=31 means download 31 days per CDS request
            # skip_historical_merge=True: Just download + create GeoTIFFs, merge later
            era5_land_daily_flow(
                batch_days=31,
                start_date=year_start,
                end_date=year_end,
                variables_config=[
                    {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
                    {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
                    {'variable': '2m_temperature', 'statistic': 'daily_mean'},
                ],
                skip_historical_merge=True  # Skip problematic merge, do it later
            )

            print(f"\n✓ Year {current_year}: Processing completed")

        except Exception as e:
            print(f"\n✗ Year {current_year} failed: {e}")
            print(f"  Continuing with next year...")

        current_year += 1

    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Years processed: {overall_start.year} to {end_year}")
    print(f"Check logs for details on each variable (daily_maximum, daily_minimum, daily_mean)")
    print(f"{'='*80}")
