#!/usr/bin/env python3
"""
ERA5 Land Daily Data Download Script
Downloads temperature data (daily_maximum and daily_minimum) for Latin America
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date, timedelta

if __name__ == "__main__":
    # ERA5-Land has ~5-7 day lag, so end date is 7 days before today
    today = date.today()
    end_date = today - timedelta(days=7)

    # Download from 2015 to present
    start_date = date(2015, 1, 1)

    print("="*80)
    print("ERA5 LAND DAILY DATA DOWNLOAD")
    print("="*80)
    print(f"Date range: {start_date} to {end_date}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    print(f"Variables: 2m_temperature (daily_maximum, daily_minimum)")
    print(f"Region: Latin America")
    print("="*80)
    print()

    # Run the flow
    # batch_days=31 means download 31 days per CDS request (default)
    # The flow will automatically:
    # - Check which dates already exist
    # - Skip existing data
    # - Create yearly historical NetCDF files
    # - Create GeoTIFF files for GeoServer
    era5_land_daily_flow(
        batch_days=31,
        start_date=start_date,
        end_date=end_date,
        variables_config=[
            {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
            {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
        ]
    )
