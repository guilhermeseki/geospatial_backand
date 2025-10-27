#!/usr/bin/env python3
"""
Unified Precipitation Data Processing Script
Creates yearly historical NetCDF from existing CHIRPS and MERGE GeoTIFFs
"""
from app.workflows.data_processing.flows import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource

if __name__ == "__main__":
    print("="*80)
    print("PRECIPITATION YEARLY HISTORICAL BUILD")
    print("="*80)
    print("\nThis will create yearly NetCDF files from existing GeoTIFFs")
    print("- CHIRPS: 3,623 files (2015-10-01 to present)")
    print("- MERGE: 4,009 files (2014-11-01 to present)")
    print("="*80)
    print()

    # Build CHIRPS historical
    print("\n[1/2] Processing CHIRPS...")
    chirps_files = build_precipitation_yearly_historical(DataSource.CHIRPS)
    print(f"\n✓ Created {len(chirps_files)} CHIRPS yearly files")

    # Build MERGE historical
    print("\n[2/2] Processing MERGE...")
    merge_files = build_precipitation_yearly_historical(DataSource.MERGE)
    print(f"\n✓ Created {len(merge_files)} MERGE yearly files")

    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print("="*80)
    print(f"\nTotal yearly files created: {len(chirps_files) + len(merge_files)}")
    print("\nYearly historical files location:")
    print("  CHIRPS: /mnt/workwork/geoserver_data/chirps_hist/")
    print("  MERGE: /mnt/workwork/geoserver_data/merge_hist/")
