"""
Reclip all existing CHIRPS GeoTIFFs with Brazil polygon
This is much faster than re-downloading since it just reprocesses existing files
"""
from pathlib import Path
import subprocess
from app.config.settings import get_settings
import rioxarray
import numpy as np
from tqdm import tqdm

settings = get_settings()

chirps_dir = Path(settings.DATA_DIR) / "chirps"
shapefile = Path("/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp")

if not shapefile.exists():
    print(f"❌ Shapefile not found: {shapefile}")
    exit(1)

# Find all CHIRPS GeoTIFFs
geotiff_files = sorted(chirps_dir.glob("chirps_*.tif"))
print(f"Found {len(geotiff_files)} CHIRPS GeoTIFF files")

# Check first file to see if already clipped
if geotiff_files:
    test_file = geotiff_files[0]
    ds = rioxarray.open_rasterio(test_file, masked=True).squeeze()
    nan_pct = (np.count_nonzero(np.isnan(ds.values)) / ds.size) * 100
    print(f"\nFirst file: {test_file.name}")
    print(f"  Current NaN%: {nan_pct:.1f}%")

    if nan_pct > 40:
        print("\n✓ Files appear to be already polygon-clipped")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted")
            exit(0)

print(f"\n{'='*80}")
print("Starting reclipping process...")
print(f"{'='*80}\n")

success_count = 0
error_count = 0

for tif_file in tqdm(geotiff_files, desc="Reclipping CHIRPS files"):
    temp_file = tif_file.with_suffix(".tmp.tif")

    try:
        # Rename original to temp
        tif_file.rename(temp_file)

        # Run gdalwarp with polygon clip
        result = subprocess.run([
            "gdalwarp",
            "-q",
            "-cutline", str(shapefile),
            "-crop_to_cutline",
            "-dstnodata", "nan",
            "-overwrite",
            "-co", "COMPRESS=LZW",
            "-co", "TILED=YES",
            str(temp_file),
            str(tif_file)
        ], capture_output=True, text=True, timeout=60, check=True)

        # Delete temp file
        temp_file.unlink()
        success_count += 1

    except subprocess.CalledProcessError as e:
        error_count += 1
        print(f"\n❌ Failed: {tif_file.name}")
        print(f"   Error: {e.stderr[:200]}")
        # Restore original file
        if temp_file.exists():
            temp_file.rename(tif_file)
    except Exception as e:
        error_count += 1
        print(f"\n❌ Failed: {tif_file.name}")
        print(f"   Error: {e}")
        # Restore original file
        if temp_file.exists():
            temp_file.rename(tif_file)

print(f"\n{'='*80}")
print(f"Reclipping complete!")
print(f"  Success: {success_count}")
print(f"  Errors: {error_count}")
print(f"{'='*80}")

# Verify a sample
if success_count > 0:
    print("\nVerifying sample files...")
    sample_files = geotiff_files[::len(geotiff_files)//5][:5]  # Sample 5 files evenly distributed

    for tif_file in sample_files:
        ds = rioxarray.open_rasterio(tif_file, masked=True).squeeze()
        nan_pct = (np.count_nonzero(np.isnan(ds.values)) / ds.size) * 100
        print(f"  {tif_file.name}: {ds.shape}, NaN: {nan_pct:.1f}%")
