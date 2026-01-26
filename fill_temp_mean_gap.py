#!/usr/bin/env python3
"""
Fill missing temp_mean data for 2022 and 2024 (entire years missing)
Downloads ERA5 data and processes to both GeoTIFF and historical NetCDF formats
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date

if __name__ == "__main__":
    # Define the missing years
    gaps = [
        (date(2022, 1, 1), date(2022, 12, 31)),   # 365 days
        (date(2024, 1, 1), date(2024, 12, 31)),   # 366 days (leap year)
    ]

    print("=" * 80)
    print("FILLING temp_mean DATA GAPS")
    print("=" * 80)
    total_days = sum((end - start).days + 1 for start, end in gaps)
    print(f"Missing years: 2022, 2024")
    for i, (start, end) in enumerate(gaps, 1):
        days = (end - start).days + 1
        print(f"  Gap {i}: {start} to {end} ({days} days)")
    print(f"Total days to download: {total_days}")
    print(f"Variables: 2m_temperature (daily_mean)")
    print(f"This will create:")
    print(f"  1. GeoTIFF files in temp_mean/ directory")
    print(f"  2. Create temp_mean_2022.nc and temp_mean_2024.nc historical NetCDF files")
    print("=" * 80)
    print()

    # Process each gap (each year)
    for gap_num, (start_date, end_date) in enumerate(gaps, 1):
        year = start_date.year
        print(f"\n{'=' * 80}")
        print(f"GAP {gap_num}/{len(gaps)}: Year {year} ({start_date} to {end_date})")
        print(f"{'=' * 80}\n")

        try:
            # Run the flow for this year
            era5_land_daily_flow(
                batch_days=31,  # Download 31 days per CDS request
                start_date=start_date,
                end_date=end_date,
                variables_config=[
                    {'variable': '2m_temperature', 'statistic': 'daily_mean'},
                ],
                skip_historical_merge=False  # Create historical NetCDF
            )

            print(f"\n✓ Gap {gap_num} (Year {year}): Processing completed")

        except Exception as e:
            print(f"\n✗ Gap {gap_num} (Year {year}) failed: {e}")
            import traceback
            traceback.print_exc()
            print(f"  Continuing with next gap...")

    print(f"\n{'=' * 80}")
    print(f"GAP FILLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"Next steps:")
    print(f"  1. Verify GeoTIFF files exist:")
    print(f"     ls /mnt/workwork/geoserver_data/temp_mean/temp_mean_20220101.tif")
    print(f"     ls /mnt/workwork/geoserver_data/temp_mean/temp_mean_20241231.tif")
    print(f"  2. Check NetCDF created:")
    print(f"     ls -lh /mnt/workwork/geoserver_data/temp_mean_hist/temp_mean_2022.nc")
    print(f"     ls -lh /mnt/workwork/geoserver_data/temp_mean_hist/temp_mean_2024.nc")
    print(f"  3. Verify NetCDF data:")
    print(f"     python3 -c 'import xarray as xr; ds=xr.open_dataset(\"/mnt/workwork/geoserver_data/temp_mean_hist/temp_mean_2022.nc\"); print(f\"Days: {{len(ds.time)}}\"); ds.close()'")
    print(f"  4. Restart FastAPI to reload datasets")
    print(f"{'=' * 80}")
