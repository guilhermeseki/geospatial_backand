#!/usr/bin/env python3
"""
Fill missing temp_min data gaps:
  - 2022-08-06 to 2022-12-31 (148 days)
  - 2025-11-04 to 2025-11-17 (14 days)
Downloads ERA5 data and processes to both GeoTIFF and historical NetCDF formats
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date

if __name__ == "__main__":
    # Define the exact gaps found
    gaps = [
        (date(2022, 8, 6), date(2022, 12, 31)),   # 148 days
        (date(2025, 11, 4), date(2025, 11, 17)),  # 14 days
    ]

    print("=" * 80)
    print("FILLING temp_min DATA GAPS")
    print("=" * 80)
    total_days = sum((end - start).days + 1 for start, end in gaps)
    print(f"Total gaps to fill: {len(gaps)}")
    for i, (start, end) in enumerate(gaps, 1):
        days = (end - start).days + 1
        print(f"  Gap {i}: {start} to {end} ({days} days)")
    print(f"Total days to download: {total_days}")
    print(f"Variables: 2m_temperature (daily_minimum)")
    print(f"This will create:")
    print(f"  1. GeoTIFF files in temp_min/ directory")
    print(f"  2. Append to temp_min historical NetCDF files")
    print("=" * 80)
    print()

    # Process each gap
    for gap_num, (start_date, end_date) in enumerate(gaps, 1):
        print(f"\n{'=' * 80}")
        print(f"GAP {gap_num}/{len(gaps)}: {start_date} to {end_date}")
        print(f"{'=' * 80}\n")

        try:
            # Run the flow for this gap
            era5_land_daily_flow(
                batch_days=31,  # Download 31 days per CDS request
                start_date=start_date,
                end_date=end_date,
                variables_config=[
                    {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
                ],
                skip_historical_merge=False  # Append to historical NetCDF
            )

            print(f"\n✓ Gap {gap_num}: Processing completed")

        except Exception as e:
            print(f"\n✗ Gap {gap_num} failed: {e}")
            import traceback
            traceback.print_exc()
            print(f"  Continuing with next gap...")

    print(f"\n{'=' * 80}")
    print(f"GAP FILLING COMPLETE")
    print(f"{'=' * 80}")
    print(f"Next steps:")
    print(f"  1. Verify GeoTIFF files exist:")
    print(f"     ls /mnt/workwork/geoserver_data/temp_min/temp_min_20220806.tif")
    print(f"     ls /mnt/workwork/geoserver_data/temp_min/temp_min_20251117.tif")
    print(f"  2. Check NetCDF updated:")
    print(f"     python3 -c 'import xarray as xr; ds=xr.open_dataset(\"/mnt/workwork/geoserver_data/temp_min_hist/temp_min_2022.nc\"); print(f\"Days: {{len(ds.time)}}\"); ds.close()'")
    print(f"  3. Restart GeoServer to refresh mosaic index")
    print(f"  4. Restart FastAPI to reload datasets")
    print(f"{'=' * 80}")
