"""
Rebuild CHIRPS historical NetCDF files from polygon-clipped GeoTIFFs
"""
from datetime import date
from app.workflows.data_processing.precipitation_flow import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

# Delete existing historical files to force rebuild
hist_dir = Path(settings.DATA_DIR) / "chirps_hist"
if hist_dir.exists():
    print(f"Deleting existing historical files in {hist_dir}")
    for nc_file in hist_dir.glob("*.nc"):
        print(f"  Deleting: {nc_file.name}")
        nc_file.unlink()

print(f"\n{'='*80}")
print("Building CHIRPS yearly historical NetCDF files")
print("Using Brazil polygon-clipped GeoTIFFs")
print(f"{'='*80}\n")

# Build all years
result = build_precipitation_yearly_historical(
    source=DataSource.CHIRPS,
    clip_geojson=None  # GeoTIFFs are already polygon-clipped, no need to clip again
)

print(f"\n{'='*80}")
print(f"Completed! Created {len(result)} yearly NetCDF files")
print(f"{'='*80}")

# List the created files
if hist_dir.exists():
    nc_files = sorted(hist_dir.glob("*.nc"))
    print(f"\nHistorical NetCDF files ({len(nc_files)}):")
    for nc_file in nc_files:
        size_mb = nc_file.stat().st_size / (1024 * 1024)
        print(f"  {nc_file.name}: {size_mb:.1f} MB")
