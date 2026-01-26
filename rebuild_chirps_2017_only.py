"""
Rebuild CHIRPS 2017 historical NetCDF file only
"""
from datetime import date
from app.workflows.data_processing.precipitation_flow import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

print(f"\n{'='*80}")
print("Rebuilding CHIRPS 2017 yearly historical NetCDF file")
print("From GeoTIFF files at 0.05° resolution")
print(f"{'='*80}\n")

# Build only 2017
result = build_precipitation_yearly_historical(
    source=DataSource.CHIRPS,
    clip_geojson=None,  # GeoTIFFs are already clipped
    start_year=2017,
    end_year=2017
)

print(f"\n{'='*80}")
print(f"Completed! Created {len(result)} yearly NetCDF file(s)")
print(f"{'='*80}")

# List the created file
hist_dir = Path(settings.DATA_DIR) / "chirps_hist"
if hist_dir.exists():
    nc_file = hist_dir / "chirps_2017.nc"
    if nc_file.exists():
        size_mb = nc_file.stat().st_size / (1024 * 1024)
        print(f"\nRebuilt file:")
        print(f"  {nc_file.name}: {size_mb:.1f} MB")
