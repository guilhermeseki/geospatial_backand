#!/usr/bin/env python3
"""
Check ERA5 download progress by scanning existing files
"""
from pathlib import Path
from datetime import date, timedelta
import pandas as pd
from app.config.settings import get_settings

def check_progress():
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)

    # Date range
    start_date = date(2015, 1, 1)
    end_date = date.today() - timedelta(days=7)
    total_days = (end_date - start_date).days + 1

    print("="*80)
    print("ERA5 DOWNLOAD PROGRESS CHECK")
    print("="*80)
    print(f"Target date range: {start_date} to {end_date}")
    print(f"Total days needed: {total_days:,}")
    print()

    for var_name, var_label in [('temp_max', 'Daily Maximum Temperature'),
                                  ('temp_min', 'Daily Minimum Temperature')]:
        print(f"\n{var_label} ({var_name}):")
        print("-"*80)

        # Check GeoTIFF files
        geotiff_dir = data_dir / var_name
        geotiff_files = list(geotiff_dir.glob(f"{var_name}_*.tif")) if geotiff_dir.exists() else []

        geotiff_dates = set()
        for f in geotiff_files:
            try:
                date_str = f.stem.split('_')[-1]
                geotiff_dates.add(pd.to_datetime(date_str, format='%Y%m%d').date())
            except:
                pass

        print(f"  GeoTIFF files: {len(geotiff_files):,} / {total_days:,} ({len(geotiff_files)/total_days*100:.1f}%)")

        if geotiff_dates:
            print(f"  Date range: {min(geotiff_dates)} to {max(geotiff_dates)}")

        # Check yearly historical files
        hist_dir = data_dir / f"{var_name}_hist"
        if hist_dir.exists():
            yearly_files = sorted(hist_dir.glob(f"{var_name}_*.nc"))
            print(f"  Yearly files: {len(yearly_files)}")

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
                except:
                    pass

            print(f"  Total historical days: {total_hist_days:,} / {total_days:,} ({total_hist_days/total_days*100:.1f}%)")
        else:
            print(f"  Yearly files: 0 (directory doesn't exist yet)")

    print()
    print("="*80)

if __name__ == "__main__":
    check_progress()
