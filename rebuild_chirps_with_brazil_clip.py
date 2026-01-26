#!/usr/bin/env python3
"""
Rebuild CHIRPS historical NetCDF files with Brazil GeoJSON clipping
This will significantly improve API query performance
"""
import sys
sys.path.insert(0, '/opt/geospatial_backend')

from pathlib import Path
from app.workflows.data_processing.precipitation_flow import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource

def main():
    print("="*80)
    print("REBUILD CHIRPS HISTORICAL WITH BRAZIL CLIPPING")
    print("="*80)
    print()

    # Brazil GeoJSON path
    brazil_geojson = "/opt/geospatial_backend/data/processed/brazil_dissolved_buffered_simplified.geojson"

    if not Path(brazil_geojson).exists():
        print(f"❌ Brazil GeoJSON not found: {brazil_geojson}")
        return

    print(f"Using Brazil GeoJSON: {brazil_geojson}")
    print()

    print("Expected improvements:")
    print("  • File size: ~3x smaller (512 MB → ~180 MB per year)")
    print("  • Memory usage: ~3x less RAM")
    print("  • Query speed: ~3x faster")
    print("  • API startup: ~3x faster")
    print()

    # Ask for confirmation
    print("This will:")
    print("  1. Delete existing chirps_YYYY.nc files (keeps brazil_chirps_YYYY.nc)")
    print("  2. Rebuild all years (2015-2025) with Brazil clipping")
    print("  3. Take approximately 30-45 minutes")
    print()

    response = input("Proceed? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return

    print()
    print("Starting rebuild...")
    print()

    # Delete existing chirps_YYYY.nc files (not brazil_chirps_YYYY.nc)
    hist_dir = Path("/mnt/workwork/geoserver_data/chirps_hist")
    for nc_file in hist_dir.glob("chirps_*.nc"):
        if not nc_file.name.startswith("brazil_"):
            print(f"Deleting: {nc_file.name}")
            nc_file.unlink()

    print()

    # Rebuild all years with Brazil clipping
    result = build_precipitation_yearly_historical(
        source=DataSource.CHIRPS,
        start_year=2015,
        end_year=2025,
        clip_geojson=brazil_geojson
    )

    print()
    print("="*80)
    print("REBUILD COMPLETE!")
    print("="*80)

    if result:
        print(f"✓ Created {len(result)} file(s)")
        print()
        print("Files created:")
        for f in result:
            size_mb = f.stat().st_size / (1024**2)
            print(f"  • {f.name} ({size_mb:.1f} MB)")

    print()
    print("Next steps:")
    print("1. Restart the API to reload CHIRPS datasets")
    print("2. Test query performance")
    print("3. Optionally delete old brazil_chirps_*.nc files")

if __name__ == "__main__":
    main()
