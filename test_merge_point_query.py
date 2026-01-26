#!/usr/bin/env python3
"""
Test point queries on MERGE data to verify alignment.
"""
import xarray as xr
import rioxarray
from pathlib import Path

def test_point_alignment():
    """Test if point queries return the same values from GeoTIFF and historical NetCDF"""
    print("=" * 80)
    print("TESTING MERGE POINT QUERY ALIGNMENT")
    print("=" * 80)

    # Test coordinates (somewhere in Brazil)
    test_lat = -10.0
    test_lon = -50.0
    test_date = "2015-11-01"

    print(f"\nTest point: ({test_lat}, {test_lon})")
    print(f"Test date: {test_date}")

    # 1. Query GeoTIFF directly
    print("\n" + "-" * 80)
    print("1. GEOTIFF QUERY")
    print("-" * 80)
    geotiff_path = Path(f"/mnt/workwork/geoserver_data/merge/merge_20151101.tif")
    if geotiff_path.exists():
        da = rioxarray.open_rasterio(geotiff_path, masked=True).squeeze()
        print(f"GeoTIFF shape: {da.shape}")
        print(f"GeoTIFF X range: {float(da.x.min())} to {float(da.x.max())}")
        print(f"GeoTIFF Y range: {float(da.y.min())} to {float(da.y.max())}")

        # Find nearest point
        value_tif = da.sel(x=test_lon, y=test_lat, method='nearest')
        actual_lon = float(value_tif.x)
        actual_lat = float(value_tif.y)
        value = float(value_tif.values)

        print(f"\nNearest pixel in GeoTIFF:")
        print(f"  Coordinates: ({actual_lat}, {actual_lon})")
        print(f"  Value: {value:.2f} mm/day")
    else:
        print(f"✗ GeoTIFF not found: {geotiff_path}")
        value_tif = None

    # 2. Query historical NetCDF
    print("\n" + "-" * 80)
    print("2. HISTORICAL NETCDF QUERY")
    print("-" * 80)
    hist_path = Path("/mnt/workwork/geoserver_data/merge_hist/brazil_merge_2015.nc")
    if hist_path.exists():
        ds = xr.open_dataset(hist_path)
        print(f"NetCDF shape: {ds.precip.shape}")
        print(f"NetCDF lon range: {float(ds.longitude.min())} to {float(ds.longitude.max())}")
        print(f"NetCDF lat range: {float(ds.latitude.min())} to {float(ds.latitude.max())}")

        # Find nearest point
        value_nc = ds.precip.sel(
            longitude=test_lon,
            latitude=test_lat,
            time=test_date,
            method='nearest'
        )
        actual_lon_nc = float(value_nc.longitude)
        actual_lat_nc = float(value_nc.latitude)
        value_nc_val = float(value_nc.values)

        print(f"\nNearest pixel in NetCDF:")
        print(f"  Coordinates: ({actual_lat_nc}, {actual_lon_nc})")
        print(f"  Value: {value_nc_val:.2f} mm/day")

        ds.close()
    else:
        print(f"✗ NetCDF not found: {hist_path}")
        value_nc_val = None

    # 3. Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    if value_tif is not None and value_nc_val is not None:
        print(f"GeoTIFF value:  {value:.2f} mm/day at ({actual_lat:.4f}, {actual_lon:.4f})")
        print(f"NetCDF value:   {value_nc_val:.2f} mm/day at ({actual_lat_nc:.4f}, {actual_lon_nc:.4f})")

        lon_diff = actual_lon_nc - actual_lon
        lat_diff = actual_lat_nc - actual_lat
        value_diff = value_nc_val - value

        print(f"\nCoordinate difference:")
        print(f"  Longitude: {lon_diff:.6f}° ({abs(lon_diff)/0.1:.2f} pixels)")
        print(f"  Latitude:  {lat_diff:.6f}° ({abs(lat_diff)/0.1:.2f} pixels)")
        print(f"  Value difference: {value_diff:.2f} mm/day")

        if abs(lon_diff) < 0.01 and abs(lat_diff) < 0.01:
            print("\n✓ Coordinates are aligned (within 0.01°)")
        else:
            print("\n⚠️  COORDINATE MISALIGNMENT DETECTED!")
            print(f"   NetCDF is offset by ~{abs(lon_diff)/0.1:.1f} pixels in longitude")
            print(f"   NetCDF is offset by ~{abs(lat_diff)/0.1:.1f} pixels in latitude")

        if abs(value_diff) < 0.01:
            print("✓ Values match (within 0.01 mm/day)")
        else:
            print(f"⚠️  Values differ by {abs(value_diff):.2f} mm/day")
            if abs(lon_diff) > 0.01 or abs(lat_diff) > 0.01:
                print("   This may be due to coordinate misalignment")

if __name__ == "__main__":
    test_point_alignment()
