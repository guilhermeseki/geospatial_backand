"""
Rebuild CHIRPS 2015-2017 historical NetCDF files to complete the dataset
"""
from datetime import date
from app.workflows.data_processing.precipitation_flow import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

# Delete incomplete 2017 file
hist_dir = Path(settings.DATA_DIR) / "chirps_hist"
old_2017 = hist_dir / "brazil_chirps_2017.nc"
if old_2017.exists():
    print(f"Deleting incomplete 2017 file: {old_2017}")
    old_2017.unlink()

print(f"\n{'='*80}")
print("Building CHIRPS 2015-2017 yearly historical NetCDF files")
print("From polygon-clipped GeoTIFFs at 0.05° resolution")
print(f"{'='*80}\n")

# Build 2015-2017
result = build_precipitation_yearly_historical(
    source=DataSource.CHIRPS,
    clip_geojson=None,  # GeoTIFFs are already polygon-clipped
    start_year=2015,
    end_year=2017
)

print(f"\n{'='*80}")
print(f"Completed! Created {len(result)} yearly NetCDF files")
print(f"{'='*80}")

# List the created files
if hist_dir.exists():
    nc_files = sorted(hist_dir.glob("*chirps_201[567].nc"))
    print(f"\nRebuilt files ({len(nc_files)}):")
    for nc_file in nc_files:
        size_mb = nc_file.stat().st_size / (1024 * 1024)
        print(f"  {nc_file.name}: {size_mb:.1f} MB")
