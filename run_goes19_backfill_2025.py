#!/usr/bin/env python3
"""
Backfill GOES-19 GLM FED historical NetCDF for all existing 2025 GeoTIFF dates
"""
from datetime import date
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

if __name__ == "__main__":
    print("=" * 80)
    print("GOES-19 GLM FED 2025 BACKFILL")
    print("=" * 80)
    print()
    print("This will process all existing 2025 GeoTIFF files and create")
    print("the yearly historical NetCDF file: glm_fed_2025.nc")
    print()

    # Based on the directory listing, we have data from April 15 - July 30, 2025
    start_date = date(2025, 4, 15)
    end_date = date(2025, 7, 30)

    print(f"Processing: {start_date} to {end_date}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    print()
    print("Expected results:")
    print("  - Coordinate conversion: x/y → latitude/longitude")
    print("  - Satellite: GOES-19 at -75.2°W")
    print("  - Output: /mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc")
    print()
    print("Starting backfill...")
    print("=" * 80)
    print()

    # Run the flow for the date range
    result = glm_fed_flow(
        start_date=start_date,
        end_date=end_date
    )

    print()
    print("=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)

    if result:
        print("✓ SUCCESS: All 2025 data processed")
        print()
        print("Next steps:")
        print("  1. Verify: ls -lh /mnt/workwork/geoserver_data/glm_fed_hist/")
        print("  2. Check dimensions: ncdump -h /mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc")
        print("  3. Restart FastAPI to load the new historical data")
    else:
        print("✗ FAILED: Check logs for errors")
