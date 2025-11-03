#!/usr/bin/env python3
"""
NDVI MODIS Test Script
Tests the MODIS download with a small date range (1 month)
Use this to verify the fixes work before running the full year-by-year script
"""
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date

if __name__ == "__main__":
    # Test with just one month of recent data
    start_date = date(2024, 10, 1)
    end_date = date(2024, 10, 31)

    print("="*80)
    print("MODIS NDVI DATA DOWNLOAD - TEST RUN")
    print("="*80)
    print(f"Date range: {start_date} to {end_date} (1 month)")
    print(f"Source: MODIS MOD13Q1.061 (250m resolution, 16-day composites)")
    print(f"Provider: Microsoft Planetary Computer (FREE!)")
    print(f"Region: Latin America")
    print(f"This is a TEST to verify the timeout fixes work")
    print("="*80)
    print()

    try:
        # Run the flow with small batch size
        result = ndvi_data_flow(
            start_date=start_date,
            end_date=end_date,
            sources=['modis'],
            batch_days=16  # Small batches
        )

        print(f"\n{'='*80}")
        print(f"✓ TEST SUCCESSFUL!")
        print(f"{'='*80}")
        print(f"Processed {len(result)} files")
        print(f"If this worked, you can now run: python app/run_ndvi.py")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"✗ TEST FAILED!")
        print(f"{'='*80}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*80}")
