#!/usr/bin/env python3
"""
ERA5 Land Wind Data Download Script
Downloads 10m wind data (u/v components and wind speed) for Latin America

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
    print("ERA5 LAND WIND DATA DOWNLOAD (YEAR-BY-YEAR)")
    print("="*80)
    print(f"Overall range: {overall_start} to {overall_end}")
    print(f"Total days: {(overall_end - overall_start).days + 1}")
    print(f"Variables: 10m wind (u-component, v-component)")
    print(f"Statistics: daily_maximum (to get peak wind intensity)")
    print(f"Note: Wind speed will be calculated from u and v components")
    print(f"Region: Latin America")
    print(f"Strategy: Process one year at a time to avoid timeouts")
    print("="*80)
    print()

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
            # Download MAXIMUM u and v components to get peak wind intensity
            print(f"\n--- Processing Wind U Component (Maximum) ---")
            era5_land_daily_flow(
                batch_days=31,
                start_date=year_start,
                end_date=year_end,
                variables_config=[
                    {'variable': '10m_u_component_of_wind', 'statistic': 'daily_maximum'},
                ],
                skip_historical_merge=True  # Skip merge, do it later
            )

            print(f"\n--- Processing Wind V Component (Maximum) ---")
            era5_land_daily_flow(
                batch_days=31,
                start_date=year_start,
                end_date=year_end,
                variables_config=[
                    {'variable': '10m_v_component_of_wind', 'statistic': 'daily_maximum'},
                ],
                skip_historical_merge=True  # Skip merge, do it later
            )

            print(f"\n✓ Year {current_year}: Processing completed")

        except Exception as e:
            print(f"\n✗ Year {current_year} failed: {e}")
            print(f"  Continuing with next year...")
            import traceback
            traceback.print_exc()

        current_year += 1

    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Years processed: {overall_start.year} to {end_year}")
    print(f"Wind variables created:")
    print(f"  - wind_u_max (eastward component - daily maximum)")
    print(f"  - wind_v_max (northward component - daily maximum)")
    print(f"")
    print(f"To calculate wind speed (intensity): sqrt(u² + v²)")
    print(f"{'='*80}")
