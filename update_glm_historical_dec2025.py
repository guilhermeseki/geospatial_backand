#!/usr/bin/env python3
"""
Update GLM FED historical NetCDF with December 2025 data from GeoTIFFs.
This script reads existing GeoTIFF files and appends them to glm_fed_2025.nc
"""
import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import rasterio
import traceback

from app.config.settings import get_settings

settings = get_settings()

def update_glm_historical():
    """Update GLM FED 2025 historical file with December data."""

    geotiff_dir = Path(settings.DATA_DIR) / "glm_fed"
    hist_dir = Path(settings.DATA_DIR) / "glm_fed_hist"
    year_file = hist_dir / "glm_fed_2025.nc"

    print("=" * 80)
    print("UPDATING GLM FED HISTORICAL WITH DECEMBER 2025 DATA")
    print("=" * 80)

    # Load existing historical file
    if not year_file.exists():
        print(f"❌ Historical file not found: {year_file}")
        return

    print(f"\n📂 Loading existing historical file: {year_file.name}")
    with xr.open_dataset(year_file) as existing_ds:
        existing_dates = set(pd.to_datetime(existing_ds.time.values).date)
        print(f"   Current coverage: {min(existing_dates)} to {max(existing_dates)}")
        print(f"   Total days: {len(existing_dates)}")

    # Find all December 2025 GeoTIFF files
    print(f"\n🔍 Searching for December 2025 GeoTIFF files...")
    december_files = sorted(geotiff_dir.glob("glm_fed_202512*.tif"))

    if not december_files:
        print("   ℹ️  No December 2025 files found")
        return

    print(f"   Found {len(december_files)} December files")

    # Check which dates are missing
    new_dates = []
    for tif_file in december_files:
        date_str = tif_file.stem.split('_')[-1]  # Extract YYYYMMDD
        file_date = pd.to_datetime(date_str, format='%Y%m%d').date()

        if file_date not in existing_dates:
            new_dates.append((file_date, tif_file))

    if not new_dates:
        print("\n✅ Historical file is already up to date!")
        return

    print(f"\n📥 Found {len(new_dates)} new dates to add:")
    for file_date, _ in sorted(new_dates)[:5]:
        print(f"   - {file_date}")
    if len(new_dates) > 5:
        print(f"   ... and {len(new_dates) - 5} more")

    # Load all new dates
    print(f"\n⚙️  Loading new GeoTIFF data...")
    new_datasets = []

    for file_date, tif_file in sorted(new_dates):
        try:
            # Load GeoTIFF as xarray Dataset
            with rasterio.open(tif_file) as src:
                data = src.read(1)
                transform = src.transform

                # Get coordinates from transform
                height, width = data.shape

                # Generate coordinates for pixel centers
                lons = np.array([transform * (col + 0.5, 0.5) for col in range(width)])[:, 0]
                lats = np.array([transform * (0.5, row + 0.5) for row in range(height)])[:, 1]

            # Create xarray Dataset
            daily_ds = xr.Dataset(
                {
                    'fed_30min_max': (['latitude', 'longitude'], data)
                },
                coords={
                    'latitude': lats,
                    'longitude': lons,
                    'time': pd.Timestamp(file_date)
                }
            )

            # Expand time dimension
            daily_ds = daily_ds.expand_dims('time')
            new_datasets.append(daily_ds)

            print(f"   ✓ Loaded {file_date}")

        except Exception as e:
            print(f"   ✗ Failed to load {file_date}: {e}")
            traceback.print_exc()

    if not new_datasets:
        print("\n❌ No new data could be loaded")
        return

    # Combine new datasets
    print(f"\n🔗 Combining {len(new_datasets)} new datasets...")
    new_combined = xr.concat(new_datasets, dim='time')
    new_combined = new_combined.sortby('time')

    # Append to existing historical file
    print(f"\n💾 Appending to historical file...")
    try:
        with xr.open_dataset(year_file) as existing_ds:
            # Concatenate along time dimension
            combined_ds = xr.concat([existing_ds, new_combined], dim='time')

            # Sort by time
            combined_ds = combined_ds.sortby('time')

            # Add/update attributes
            combined_ds.attrs['source'] = 'GLM FED GeoTIFF'
            combined_ds.attrs['unit'] = 'flashes/km²/30min'
            combined_ds.attrs['description'] = 'Maximum lightning flash density in any 30-minute window'
            combined_ds.attrs['resolution'] = '~3.23 km × 3.23 km'
            combined_ds.attrs['pixel_area'] = '10.41 km²'
            combined_ds.attrs['normalization'] = 'Values normalized by pixel area'
            combined_ds.attrs['last_updated'] = datetime.now().isoformat()

            # Save with compression
            print(f"   Saving with compression...")
            encoding = {
                'fed_30min_max': {
                    'zlib': True,
                    'complevel': 4,
                    'dtype': 'float32'
                }
            }

            # Create backup first
            backup_file = year_file.with_suffix('.nc.backup')
            print(f"   Creating backup: {backup_file.name}")
            import shutil
            shutil.copy2(year_file, backup_file)

            # Save updated file
            combined_ds.to_netcdf(year_file, encoding=encoding)

            # Verify
            with xr.open_dataset(year_file) as verify_ds:
                final_dates = set(pd.to_datetime(verify_ds.time.values).date)

                print(f"\n✅ SUCCESS!")
                print(f"   Updated coverage: {min(final_dates)} to {max(final_dates)}")
                print(f"   Total days: {len(final_dates)}")
                print(f"   Added: {len(final_dates) - len(existing_dates)} new days")
                print(f"   File: {year_file}")
                print(f"   Backup: {backup_file}")

    except Exception as e:
        print(f"\n❌ Failed to update historical file: {e}")
        traceback.print_exc()

        # Restore from backup if it exists
        backup_file = year_file.with_suffix('.nc.backup')
        if backup_file.exists():
            print(f"\n🔄 Restoring from backup...")
            import shutil
            shutil.copy2(backup_file, year_file)
            print(f"   ✓ Restored")

if __name__ == "__main__":
    update_glm_historical()
