#!/usr/bin/env python3
"""
Test script to verify the historical file detection fix
Tests with a small date range that partially exists
"""
from app.workflows.data_processing.ndvi_flow import check_missing_dates
from datetime import date

if __name__ == "__main__":
    print("="*80)
    print("TESTING HISTORICAL FILE DETECTION FIX")
    print("="*80)

    # Test 1: Check detection for existing data
    print("\nTest 1: Checking August 2024 (should find existing data)")
    print("-"*80)

    start_date = date(2024, 8, 1)
    end_date = date(2024, 8, 31)

    result = check_missing_dates(start_date, end_date, 'modis')

    print(f"\nResults:")
    print(f"  Missing from GeoTIFF: {len(result['geotiff'])} dates")
    print(f"  Missing from historical: {len(result['historical'])} dates")
    print(f"  Need to download: {len(result['download'])} dates")

    if len(result['historical']) < 31:
        print(f"\n✅ SUCCESS: Found existing historical data!")
        print(f"   Found {31 - len(result['historical'])} existing dates in historical files")
    else:
        print(f"\n❌ FAILED: Did not detect existing historical data")
        print(f"   Expected to find 1-2 existing dates, but found 0")

    # Test 2: Check detection for brand new data
    print("\n" + "="*80)
    print("Test 2: Checking December 2024 (should be all missing)")
    print("-"*80)

    start_date = date(2024, 12, 1)
    end_date = date(2024, 12, 15)

    result = check_missing_dates(start_date, end_date, 'modis')

    print(f"\nResults:")
    print(f"  Missing from GeoTIFF: {len(result['geotiff'])} dates")
    print(f"  Missing from historical: {len(result['historical'])} dates")
    print(f"  Need to download: {len(result['download'])} dates")

    if len(result['download']) == 15:
        print(f"\n✅ SUCCESS: Correctly identified all dates as missing")
    else:
        print(f"\n❌ FAILED: Expected 15 missing dates, got {len(result['download'])}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
