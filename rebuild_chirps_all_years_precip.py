"""
Rebuild ALL CHIRPS yearly NetCDF files with "precip" variable name
"""
from datetime import date
from app.workflows.data_processing.precipitation_flow import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

print(f"\n{'='*80}")
print("Rebuilding ALL CHIRPS yearly historical NetCDF files")
print("Variable name: 'precip' (standardized)")
print(f"{'='*80}\n")

# Delete old files with "precipitation" variable name
hist_dir = Path(settings.DATA_DIR) / "chirps_hist"
if hist_dir.exists():
    old_files = list(hist_dir.glob("chirps_*.nc"))
    print(f"Deleting {len(old_files)} old CHIRPS NetCDF files...")
    for old_file in old_files:
        print(f"  - {old_file.name}")
        old_file.unlink()
    print()

# Build all years (2015-2025)
result = build_precipitation_yearly_historical(
    source=DataSource.CHIRPS,
    clip_geojson=None,  # GeoTIFFs are already clipped
    start_year=2015,
    end_year=2025
)

print(f"\n{'='*80}")
print(f"Completed! Created {len(result)} yearly NetCDF file(s)")
print(f"{'='*80}")

# List the created files
if hist_dir.exists():
    nc_files = sorted(hist_dir.glob("chirps_*.nc"))
    print(f"\nRebuilt files ({len(nc_files)}):")
    for nc_file in nc_files:
        size_mb = nc_file.stat().st_size / (1024 * 1024)
        print(f"  {nc_file.name}: {size_mb:.1f} MB")
        
    # Verify variable name
    if nc_files:
        import xarray as xr
        test_ds = xr.open_dataset(nc_files[0])
        print(f"\nVariable name in first file: {list(test_ds.data_vars)}")
        test_ds.close()
