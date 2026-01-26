#!/usr/bin/env python3
"""
Clip all MERGE NetCDF files to Brazil GeoJSON boundary.
Creates backup of originals before clipping.
"""
import xarray as xr
import geopandas as gpd
import rioxarray
from pathlib import Path
import shutil
import time
import numpy as np

# Configuration
MERGE_DIR = Path("/mnt/workwork/geoserver_data/merge_hist")
BRAZIL_GEOJSON = Path("/opt/geospatial_backend/data/shapefiles/br_shp/brazil.geojson")
BACKUP_DIR = MERGE_DIR / "backup_unclipped"

print("="*80)
print("CLIPPING MERGE NETCDF FILES TO BRAZIL BOUNDARY")
print("="*80)

# Load Brazil geometry
print("\nLoading Brazil GeoJSON...")
brazil_gdf = gpd.read_file(BRAZIL_GEOJSON)
print(f"✓ Loaded: {len(brazil_gdf)} feature(s)")

# Find all MERGE files
nc_files = sorted(MERGE_DIR.glob("brazil_merge_*.nc"))
print(f"\nFound {len(nc_files)} MERGE files to clip:")
for f in nc_files:
    size_mb = f.stat().st_size / 1024 / 1024
    print(f"  {f.name} ({size_mb:.0f} MB)")

# Confirm
print(f"\n⚠️  This will:")
print(f"  1. Create backups in: {BACKUP_DIR}")
print(f"  2. Clip all files to Brazil boundary (remove ~56% of pixels)")
print(f"  3. Overwrite original files with clipped versions")
response = input("\nContinue? (yes/no): ")
if response.lower() != 'yes':
    print("Cancelled")
    exit(0)

# Create backup directory
BACKUP_DIR.mkdir(exist_ok=True)
print(f"\n✓ Created backup directory: {BACKUP_DIR}")

# Process each file
total_start = time.time()
success_count = 0

for i, nc_file in enumerate(nc_files, 1):
    print(f"\n{'='*80}")
    print(f"[{i}/{len(nc_files)}] Processing: {nc_file.name}")
    print('='*80)

    try:
        # Create backup
        backup_path = BACKUP_DIR / nc_file.name
        if not backup_path.exists():
            print(f"Creating backup...")
            shutil.copy2(nc_file, backup_path)
            print(f"✓ Backup: {backup_path}")

        # Load dataset
        print(f"Loading dataset...")
        start = time.time()
        ds = xr.open_dataset(nc_file)
        print(f"✓ Loaded in {time.time()-start:.1f}s")
        print(f"  Dimensions: {dict(ds.dims)}")
        print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]}")

        # Prepare for clipping
        print(f"Preparing spatial dimensions...")
        ds = ds.rio.write_crs("EPSG:4326")
        ds = ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude")

        # Clip
        print(f"Clipping to Brazil boundary...")
        start = time.time()
        clipped = ds.rio.clip(brazil_gdf.geometry.values, brazil_gdf.crs, drop=False)
        elapsed = time.time() - start
        print(f"✓ Clipped in {elapsed:.1f}s")

        # Check results
        original_pixels = ds['precip'].values.size
        clipped_valid = np.sum(~np.isnan(clipped['precip'].values))
        masked_pixels = np.sum(np.isnan(clipped['precip'].values))
        print(f"  Masked {masked_pixels:,} pixels ({100*masked_pixels/(masked_pixels+clipped_valid):.1f}%)")

        # Save to temporary file first (to avoid locked file issues)
        print(f"Saving clipped dataset...")
        start = time.time()
        temp_file = nc_file.parent / f"{nc_file.stem}_clipped_temp.nc"
        encoding = {
            'precip': {'zlib': True, 'complevel': 4, 'dtype': 'float32'},
            'latitude': {'dtype': 'float32'},
            'longitude': {'dtype': 'float32'}
        }
        clipped.to_netcdf(temp_file, encoding=encoding)

        # Close datasets to release file handles
        ds.close()
        clipped.close()

        # Move temp file to replace original
        import os
        os.replace(temp_file, nc_file)
        elapsed = time.time() - start
        print(f"✓ Saved in {elapsed:.1f}s")

        # Get new file size
        new_size_mb = nc_file.stat().st_size / 1024 / 1024
        old_size_mb = backup_path.stat().st_size / 1024 / 1024
        savings = 100 * (old_size_mb - new_size_mb) / old_size_mb
        print(f"  New size: {new_size_mb:.0f} MB (saved {savings:.1f}%)")

        success_count += 1
        print(f"✓ SUCCESS")

    except Exception as e:
        print(f"✗ ERROR: {e}")
        # Restore from backup if clipping failed
        if backup_path.exists():
            shutil.copy2(backup_path, nc_file)
            print(f"  Restored from backup")

# Summary
total_elapsed = time.time() - total_start
print(f"\n{'='*80}")
print("CLIPPING COMPLETE")
print('='*80)
print(f"Processed: {success_count}/{len(nc_files)} files")
print(f"Total time: {total_elapsed/60:.1f} minutes")
print(f"\nBackups saved in: {BACKUP_DIR}")
print(f"To remove backups: rm -rf {BACKUP_DIR}")
