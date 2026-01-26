#!/usr/bin/env python3
"""
Test GOES-19 GLM FED download for a single recent date
"""
from datetime import date
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

if __name__ == "__main__":
    # Test with a recent 2025 date (GOES-19 operational)
    # Use Oct 25, 2024 = day 299 (the date from the failed log)
    # Actually, GOES-19 became operational in 2025, so let's use a 2025 date

    print("=" * 80)
    print("TESTING GOES-19 GLM FED DOWNLOAD")
    print("=" * 80)
    print()
    print("This will download and process a single day of GOES-19 data")
    print("to verify timestamp parsing and coordinate conversion fixes.")
    print()

    # Use a recent 2025 date
    test_date = date(2025, 4, 15)  # First date we have in the directory

    print(f"Test date: {test_date}")
    print(f"Expected satellite: GOES-19 (automatic based on year >= 2025)")
    print()

    # Run the flow for a single date
    result = glm_fed_flow(
        start_date=test_date,
        end_date=test_date
    )

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    if result:
        print("✓ SUCCESS: GOES-19 data downloaded and processed")
        print()
        print("Verify the following:")
        print(f"  1. GeoTIFF exists: /mnt/workwork/geoserver_data/glm_fed/glm_fed_{test_date.strftime('%Y%m%d')}.tif")
        print(f"  2. Historical NC: /mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc")
        print("  3. Check logs for timestamp parsing (should show ~1440 files loaded)")
        print("  4. Check logs for reprojection (should show GOES-19 with -75.2°W)")
    else:
        print("✗ FAILED: Check logs for errors")
