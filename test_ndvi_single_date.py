#!/usr/bin/env python3
"""
Test NDVI flow for a single date/composite
"""
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date
from pathlib import Path
import xarray as xr
import pandas as pd
from app.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    # Test with a single 16-day composite period
    # MODIS composites are 16-day periods, so we need at least 16 days
    test_date = date(2024, 7, 1)  # Start of July
    start_date = test_date
    end_date = date(2024, 7, 16)  # 16 days = 1 composite period
    
    print("="*80)
    print("NDVI FLOW TEST - SINGLE DATE/COMPOSITE")
    print("="*80)
    print(f"Date range: {start_date} to {end_date}")
    print(f"Source: MODIS (16-day composite)")
    print(f"Expected: 1 composite (end date will be ~{end_date})")
    print("="*80)
    print()
    
    try:
        # Run the NDVI flow
        print("Running NDVI data flow...")
        result = ndvi_data_flow(
            start_date=start_date,
            end_date=end_date,
            sources=['modis'],
            batch_days=16
        )
        
        print(f"\n✓ Flow completed!")
        print(f"  Processed {len(result)} file(s)")
        print()
        
        # Check the yearly file to see what was created
        yearly_file = Path(settings.DATA_DIR) / "ndvi_modis_hist" / "ndvi_modis_2024.nc"
        
        if yearly_file.exists():
            print(f"Checking yearly file: {yearly_file.name}")
            ds = xr.open_dataset(yearly_file)
            times = pd.to_datetime(ds.time.values)
            
            print(f"\n  Total time steps: {len(times)}")
            print(f"  Unique timestamps: {len(set(times))}")
            print(f"\n  All dates in file:")
            for i, t in enumerate(times):
                print(f"    [{i}] {t}")
            
            if len(times) > 0:
                print(f"\n  Date range: {times.min()} to {times.max()}")
                print(f"  Latest date: {times.max()}")
            
            ds.close()
        else:
            print(f"\n⚠️  Yearly file not found: {yearly_file}")
        
        print("\n" + "="*80)
        print("✓ TEST COMPLETE!")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

