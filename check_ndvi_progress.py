#!/usr/bin/env python3
"""
Check MODIS NDVI download progress by scanning existing files
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
    end_date = date.today()

    # MODIS has 16-day composites, approximately 23 per year
    years = end_date.year - start_date.year + 1
    approx_total_composites = years * 23

    print("="*80)
    print("MODIS NDVI DOWNLOAD PROGRESS CHECK")
    print("="*80)
    print(f"Target date range: {start_date} to {end_date}")
    print(f"Estimated composites: ~{approx_total_composites} (23/year × {years} years)")
    print()

    source = 'modis'
    var_name = 'ndvi_modis'

    print(f"MODIS NDVI ({var_name}):")
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

    print(f"  GeoTIFF files: {len(geotiff_files):,}")
    if geotiff_dates:
        print(f"  Date range: {min(geotiff_dates)} to {max(geotiff_dates)}")

    # Check yearly historical files
    hist_dir = data_dir / f"{var_name}_hist"
    if hist_dir.exists():
        yearly_files = sorted(hist_dir.glob(f"{var_name}_*.nc"))
        print(f"  Yearly historical files: {len(yearly_files)}")

        total_hist_composites = 0
        for yf in yearly_files:
            try:
                import xarray as xr
                ds = xr.open_dataset(yf)
                composites = len(ds.time)
                total_hist_composites += composites
                year = yf.stem.split('_')[-1]
                print(f"    {year}: {composites:,} composites")
                ds.close()
            except Exception as e:
                print(f"    {yf.name}: Error reading ({e})")

        print(f"  Total historical composites: {total_hist_composites:,}")
        if approx_total_composites > 0:
            percent = (total_hist_composites / approx_total_composites) * 100
            print(f"  Progress: {percent:.1f}%")
    else:
        print(f"  Yearly files: 0 (directory doesn't exist yet)")

    print()
    print("="*80)

if __name__ == "__main__":
    check_progress()
