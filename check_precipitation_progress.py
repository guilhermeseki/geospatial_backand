#!/usr/bin/env python3
"""
Check precipitation data progress (CHIRPS and MERGE)
"""
from pathlib import Path
from datetime import date
import pandas as pd
from app.config.settings import get_settings

def check_progress():
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)

    print("="*80)
    print("PRECIPITATION DATA PROGRESS CHECK")
    print("="*80)
    print()

    for source in ['chirps', 'merge']:
        print(f"{source.upper()}:")
        print("-"*80)

        # Check GeoTIFF files
        geotiff_dir = data_dir / source
        geotiff_files = list(geotiff_dir.glob(f"{source}_*.tif")) if geotiff_dir.exists() else []

        geotiff_dates = set()
        for f in geotiff_files:
            try:
                date_str = f.stem.split('_')[-1]
                geotiff_dates.add(pd.to_datetime(date_str, format='%Y%m%d').date())
            except:
                pass

        print(f"  GeoTIFF files: {len(geotiff_files):,}")
        if geotiff_dates:
            print(f"  Date range: {min(geotiff_dates)} to {max(geotiff_dates)}")

        # Check yearly historical files
        hist_dir = data_dir / f"{source}_hist"
        if hist_dir.exists():
            yearly_files = sorted(hist_dir.glob(f"{source}_*.nc"))
            print(f"  Yearly historical files: {len(yearly_files)}")

            total_hist_days = 0
            for yf in yearly_files:
                try:
                    import xarray as xr
                    ds = xr.open_dataset(yf)
                    days = len(ds.time)
                    total_hist_days += days
                    year = yf.stem.split('_')[-1]
                    print(f"    {year}: {days:,} days")
                    ds.close()
                except Exception as e:
                    print(f"    {yf.name}: Error reading ({e})")

            print(f"  Total historical days: {total_hist_days:,}")
        else:
            print(f"  Yearly files: 0 (directory doesn't exist yet)")

        print()

    print("="*80)

if __name__ == "__main__":
    check_progress()
