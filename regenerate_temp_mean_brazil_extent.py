#!/usr/bin/env python3
"""
Regenerate temp_mean GeoTIFF files for 2023 and 2025 with Brazil extent.
This will make all temp_mean files have consistent 416x416 grid.
"""
from datetime import date
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from app.config.settings import get_settings
import os

# Temporarily override the bbox to Brazil extent
# Brazil-only extent from the 2015-2021 files: [-75 to -33.5°W, -35 to 6.5°N]
BRAZIL_BBOX_CDS = [6.5, -75.0, -35.0, -33.5]  # [N, W, S, E] for CDS API
BRAZIL_BBOX_RASTER = (-75.0, -35.0, -33.5, 6.5)  # (W, S, E, N) for rasterio

if __name__ == "__main__":
    settings = get_settings()

    print("=" * 80)
    print("REGENERATING temp_mean FILES WITH BRAZIL EXTENT")
    print("=" * 80)
    print(f"Target extent: {BRAZIL_BBOX_RASTER}")
    print(f"This will create consistent 416×416 grid across all years")
    print("=" * 80)
    print()

    # Temporarily override settings
    original_cds = settings.latam_bbox_cds
    original_raster = settings.latam_bbox_raster

    settings.latam_bbox_cds = BRAZIL_BBOX_CDS
    settings.latam_bbox_raster = BRAZIL_BBOX_RASTER

    print(f"Original bbox (LatAm): {original_cds}")
    print(f"Override bbox (Brazil): {BRAZIL_BBOX_CDS}")
    print()

    # Years to regenerate
    years_to_regenerate = [2023, 2025]

    for year in years_to_regenerate:
        print(f"\n{'='*80}")
        print(f"REGENERATING YEAR: {year}")
        print(f"{'='*80}\n")

        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        # For 2025, only go to today minus 7 days (ERA5 lag)
        if year == 2025:
            from datetime import datetime, timedelta
            today = datetime.now().date()
            year_end = min(year_end, today - timedelta(days=7))

        print(f"Date range: {year_start} to {year_end}")
        print(f"Variable: 2m_temperature (daily_mean)")
        print()

        try:
            # Delete existing files for this year first
            import shutil
            from pathlib import Path

            temp_mean_dir = Path(settings.DATA_DIR) / "temp_mean"
            hist_dir = Path(settings.DATA_DIR) / "temp_mean_hist"

            # Backup then delete GeoTIFFs for this year
            print(f"Deleting existing temp_mean GeoTIFFs for {year}...")
            deleted_count = 0
            for tif_file in temp_mean_dir.glob(f"temp_mean_{year}*.tif"):
                tif_file.unlink()
                deleted_count += 1
            print(f"  Deleted {deleted_count} GeoTIFF files")

            # Delete historical NetCDF for this year
            hist_file = hist_dir / f"temp_mean_{year}.nc"
            if hist_file.exists():
                hist_file.unlink()
                print(f"  Deleted {hist_file.name}")

            print()
            print("Starting ERA5 download and processing...")
            print()

            # Run the flow
            era5_land_daily_flow(
                batch_days=31,
                start_date=year_start,
                end_date=year_end,
                variables_config=[
                    {'variable': '2m_temperature', 'statistic': 'daily_mean'},
                ],
                skip_historical_merge=True  # We'll rebuild NetCDF later
            )

            print(f"\n✓ Year {year}: Regeneration completed")

        except Exception as e:
            print(f"\n✗ Year {year} failed: {e}")
            import traceback
            traceback.print_exc()
            print(f"  Continuing with next year...")

    # Restore original settings
    settings.latam_bbox_cds = original_cds
    settings.latam_bbox_raster = original_raster

    print(f"\n{'='*80}")
    print(f"REGENERATION COMPLETE")
    print(f"{'='*80}")
    print(f"Next step: Run build_temperature_historical.py to rebuild NetCDF files")
    print(f"{'='*80}")
