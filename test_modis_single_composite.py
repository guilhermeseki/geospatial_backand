#!/usr/bin/env python3
"""
Test MODIS processing with just ONE composite to verify timestamp fix
This will process only 1 composite instead of the normal ~16
"""
from app.workflows.data_processing.ndvi_flow import download_modis_batch, process_ndvi_to_geotiff, append_to_yearly_historical_ndvi
from app.config.settings import get_settings
from datetime import date
from pathlib import Path
import xarray as xr
import pandas as pd
import sys

# Allow more items to find one with valid data, then deduplication will keep only 1 timestep
import app.workflows.data_processing.ndvi_flow as ndvi_module
ndvi_module._TEST_MAX_ITEMS = 5  # Process up to 5 tiles to find one with valid data

if __name__ == "__main__":
    settings = get_settings()
    
    # Use a 16-day date range to get exactly 1 MODIS composite period
    # MODIS composites are 16-day periods, so 16 days = 1 composite
    # But multiple overlapping tiles may exist - deduplication will keep only 1 per composite date
    # Using a date range that should have good data coverage
    start_date = date(2024, 6, 1)  # Start of June (dry season in Brazil, better MODIS coverage)
    end_date = date(2024, 6, 16)  # 16 days later - exactly 1 composite period
    
    print("="*80)
    print("MODIS SINGLE COMPOSITE TEST")
    print("="*80)
    print(f"Date range: {start_date} to {end_date} (16 days = 1 MODIS composite period)")
    print(f"Max items: 5 (will try up to 5 tiles, deduplication keeps only 1 timestep)")
    print(f"Expected: EXACTLY 1 unique timestep in output (after deduplication)")
    print(f"Testing: Timestamp uniqueness fix and tile deduplication")
    print("="*80)
    print()
    
    # Check if raw file already exists and delete it to force fresh download
    raw_dir = Path(settings.DATA_DIR) / "raw" / "modis"
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    existing_batch = raw_dir / f"modis_ndvi_{start_str}_{end_str}.nc"
    
    if existing_batch.exists():
        print(f"Found existing raw file: {existing_batch.name}")
        print("  Deleting to force fresh download and test timestamp fix...")
        existing_batch.unlink()
        print("  ✓ Deleted")
        print()
    
    try:
        # Download batch (will limit to 1 composite by modifying max_items)
        print("Step 1: Downloading MODIS batch (max 1 composite for testing)...")
        batch_path = download_modis_batch(
            start_date=start_date,
            end_date=end_date,
            area=settings.latam_bbox_cds
        )
        print(f"✓ Downloaded: {batch_path}")
        
        # Check the downloaded file for timestamps
        print("\nStep 2: Checking timestamps in downloaded file...")
        ds = xr.open_dataset(batch_path)
        time_values = ds.time.values
        time_list = pd.to_datetime(time_values)
        
        print(f"  Total time steps: {len(time_list)}")
        print(f"  Unique timestamps: {len(set(time_list))}")
        print(f"  Time values:")
        for i, t in enumerate(time_list[:5]):  # Show first 5
            print(f"    [{i}] {t}")
        
        if len(time_list) > 5:
            print(f"    ... and {len(time_list) - 5} more")
        
        # Check for duplicates
        if len(time_list) != len(set(time_list)):
            print(f"\n⚠️  WARNING: Found duplicate timestamps!")
            duplicates = [t for t in set(time_list) if list(time_list).count(t) > 1]
            print(f"   Duplicate values: {duplicates}")
        else:
            print(f"\n✓ SUCCESS: All timestamps are unique!")
        
        ds.close()
        
        # Process to GeoTIFF (optional, skip if you just want to test download)
        print("\nStep 3: Processing to GeoTIFF...")
        geotiff_paths = process_ndvi_to_geotiff(
            batch_path,
            source='modis',
            bbox=settings.latam_bbox_raster,
            dates_to_process=None
        )
        print(f"✓ Created {len(geotiff_paths)} GeoTIFF file(s)")
        
        # Append to yearly historical
        print("\nStep 4: Appending to yearly historical...")
        yearly_files = append_to_yearly_historical_ndvi(
            batch_path,
            source='modis',
            bbox=settings.latam_bbox_raster,
            dates_to_append=None
        )
        print(f"✓ Updated {len(yearly_files)} yearly file(s)")
        
        # Check the final yearly file
        if yearly_files:
            yearly_file = yearly_files[0]
            print(f"\nStep 5: Checking final yearly file: {yearly_file.name}")
            ds_final = xr.open_dataset(yearly_file)
            time_final = pd.to_datetime(ds_final.time.values)
            
            print(f"  Total time steps in yearly file: {len(time_final)}")
            print(f"  Unique timestamps: {len(set(time_final))}")
            
            if len(time_final) != len(set(time_final)):
                print(f"\n⚠️  WARNING: Yearly file still has duplicate timestamps!")
                duplicates = [t for t in set(time_final) if list(time_final).count(t) > 1]
                print(f"   Duplicate values: {duplicates[:5]}...")
            else:
                print(f"\n✓✓ SUCCESS: Yearly file has all unique timestamps!")
            
            print(f"\n  First few timestamps:")
            for i, t in enumerate(time_final[:min(5, len(time_final))]):
                print(f"    [{i}] {t}")
            
            ds_final.close()
        
        print("\n" + "="*80)
        print("✓ TEST COMPLETE!")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

