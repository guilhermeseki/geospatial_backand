"""Verify solar radiation outputs"""
import xarray as xr
from pathlib import Path

print("="*80)
print("Verifying Solar Radiation Data Files")
print("="*80)

# Check GeoTIFFs
geotiff_dir = Path("/mnt/workwork/geoserver_data/solar_radiation")
geotiffs = sorted(geotiff_dir.glob("solar_radiation_*.tif"))
print(f"\n📁 GeoTIFF Files: {len(geotiffs)} files")
for tif in geotiffs:
    print(f"  ✓ {tif.name} ({tif.stat().st_size / 1024:.0f} KB)")

# Check historical NetCDF
hist_dir = Path("/mnt/workwork/geoserver_data/solar_radiation_hist")
hist_files = sorted(hist_dir.glob("solar_radiation_*.nc"))
print(f"\n📁 Historical NetCDF Files: {len(hist_files)} files")
for nc_file in hist_files:
    print(f"\n  📊 {nc_file.name} ({nc_file.stat().st_size / 1024:.0f} KB)")

    # Inspect contents
    ds = xr.open_dataset(nc_file)
    print(f"     Variables: {list(ds.data_vars)}")
    print(f"     Dimensions: {dict(ds.dims)}")

    if 'solar_radiation' in ds.data_vars:
        da = ds['solar_radiation']
        print(f"     Time range: {da.time.min().values} to {da.time.max().values}")
        print(f"     Days: {len(da.time)}")
        print(f"     Value range: {float(da.min().values):.2f} - {float(da.max().values):.2f} kWh/m²/day")
        print(f"     Attributes: {da.attrs}")

        # Show timestamps
        print(f"     Timestamps:")
        for t in da.time.values:
            print(f"       - {t}")

    ds.close()

print("\n" + "="*80)
print("✓ Solar radiation data verification complete!")
print("="*80)
