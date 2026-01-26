"""
Rebuild CHIRPS 2024-2025 historical NetCDF files with correct resolution
"""
from datetime import date
from app.workflows.data_processing.precipitation_flow import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

print(f"\n{'='*80}")
print("Rebuilding CHIRPS 2024-2025 yearly historical NetCDF files")
print("From polygon-clipped GeoTIFFs at 0.05° resolution")
print(f"{'='*80}\n")

# Build only 2024-2025
result = build_precipitation_yearly_historical(
    source=DataSource.CHIRPS,
    clip_geojson=None,  # GeoTIFFs are already polygon-clipped
    start_year=2024,
    end_year=2025
)

print(f"\n{'='*80}")
print(f"Completed! Created {len(result)} yearly NetCDF files")
print(f"{'='*80}")

# List the created files
hist_dir = Path(settings.DATA_DIR) / "chirps_hist"
if hist_dir.exists():
    nc_files = sorted(hist_dir.glob("brazil_chirps_202[45].nc"))
    print(f"\nRebuilt files ({len(nc_files)}):")
    for nc_file in nc_files:
        size_mb = nc_file.stat().st_size / (1024 * 1024)
        print(f"  {nc_file.name}: {size_mb:.1f} MB")
