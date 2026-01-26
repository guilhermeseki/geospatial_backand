#!/usr/bin/env python3
"""
Test script to verify MERGE alignment issue and validate fix.
"""
import xarray as xr
import rioxarray
from pathlib import Path

def check_alignment():
    """Check alignment between GeoTIFF and historical NetCDF"""

    # Check GeoTIFF
    geotiff_path = Path("/mnt/workwork/geoserver_data/merge/merge_20141101.tif")
    if geotiff_path.exists():
        print("=" * 80)
        print("GEOTIFF FILE (merge_20141101.tif)")
        print("=" * 80)
        da = rioxarray.open_rasterio(geotiff_path, masked=True).squeeze()
        print(f"Shape: {da.shape}")
        print(f"X (longitude) coords:")
        print(f"  First: {float(da.x[0]):.10f}")
        print(f"  Last: {float(da.x[-1]):.10f}")
        print(f"  Spacing: {float(da.x[1] - da.x[0]):.10f}")
        print(f"Y (latitude) coords:")
        print(f"  First: {float(da.y[0]):.10f}")
        print(f"  Last: {float(da.y[-1]):.10f}")
        print(f"  Spacing: {float(da.y[1] - da.y[0]):.10f}")

        # Check the rio transform
        print(f"\nRasterio Transform:")
        print(f"  {da.rio.transform()}")
        print(f"  Origin (upper-left corner): {da.rio.transform().c}, {da.rio.transform().f}")

    # Check Historical NetCDF
    hist_path = Path("/mnt/workwork/geoserver_data/merge_hist/brazil_merge_2015.nc")
    if hist_path.exists():
        print("\n" + "=" * 80)
        print("HISTORICAL NETCDF (brazil_merge_2015.nc)")
        print("=" * 80)
        ds = xr.open_dataset(hist_path)
        print(f"Shape: {ds.precipitation.shape}")
        print(f"Longitude coords:")
        print(f"  First: {float(ds.longitude[0]):.10f}")
        print(f"  Last: {float(ds.longitude[-1]):.10f}")
        print(f"  Spacing: {float(ds.longitude[1] - ds.longitude[0]):.10f}")
        print(f"Latitude coords:")
        print(f"  First: {float(ds.latitude[0]):.10f}")
        print(f"  Last: {float(ds.latitude[-1]):.10f}")
        print(f"  Spacing: {float(ds.latitude[1] - ds.latitude[0]):.10f}")
        ds.close()

    # Calculate offset
    print("\n" + "=" * 80)
    print("ALIGNMENT ANALYSIS")
    print("=" * 80)
    if geotiff_path.exists() and hist_path.exists():
        da = rioxarray.open_rasterio(geotiff_path, masked=True).squeeze()
        ds = xr.open_dataset(hist_path)

        lon_offset = float(ds.longitude[0] - da.x[0])
        lat_offset = float(ds.latitude[0] - da.y[-1])  # Compare with last Y since Y is descending

        print(f"Longitude offset: {lon_offset:.10f}° ({abs(lon_offset)/0.1:.2f} pixels)")
        print(f"Latitude offset: {lat_offset:.10f}° ({abs(lat_offset)/0.1:.2f} pixels)")

        if abs(lon_offset) > 0.01 or abs(lat_offset) > 0.01:
            print("\n⚠️  MISALIGNMENT DETECTED!")
            print(f"   NetCDF is offset by approximately {abs(lon_offset)/0.1:.1f} pixels in longitude")
            print(f"   NetCDF is offset by approximately {abs(lat_offset)/0.1:.1f} pixels in latitude")
        else:
            print("\n✓ Alignment is correct (within tolerance)")

        ds.close()

if __name__ == "__main__":
    check_alignment()
