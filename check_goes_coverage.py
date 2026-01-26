"""
Check the native GOES-19 coverage and understand the viewing geometry
"""
import xarray as xr
import numpy as np
from pyproj import CRS, Transformer
from pathlib import Path

# Check a raw daily NetCDF before GeoTIFF conversion
raw_nc = Path("/mnt/workwork/geoserver_data/raw/glm_fed/glm_fed_daily_20250504.nc")

if not raw_nc.exists():
    print(f"Raw NetCDF not found: {raw_nc}")
    print("\nLooking for any raw GLM files...")
    raw_dir = Path("/mnt/workwork/geoserver_data/raw/glm_fed")
    if raw_dir.exists():
        files = list(raw_dir.glob("*.nc"))
        if files:
            raw_nc = files[0]
            print(f"Found: {raw_nc}")
        else:
            print("No raw NetCDF files found")
            exit(1)
    else:
        print(f"Directory not found: {raw_dir}")
        exit(1)

print(f"Examining: {raw_nc.name}")
print("="*80)

ds = xr.open_dataset(raw_nc)
print("\nDataset info:")
print(f"  Dimensions: {dict(ds.dims)}")
print(f"  Coordinates: {list(ds.coords)}")
print(f"  Variables: {list(ds.data_vars)}")
print(f"\nAttributes:")
for key, val in ds.attrs.items():
    print(f"  {key}: {val}")

# Check if it has GOES projection
if 'x' in ds.dims and 'y' in ds.dims:
    print("\n" + "="*80)
    print("GOES NATIVE PROJECTION")
    print("="*80)
    print(f"X range (radians): {ds.x.min().values:.6f} to {ds.x.max().values:.6f}")
    print(f"Y range (radians): {ds.y.min().values:.6f} to {ds.y.max().values:.6f}")

    # Convert to degrees at satellite height
    sat_height = 35786023.0
    sat_lon = -75.2  # GOES-19

    # Create GOES CRS
    goes_crs = CRS.from_cf({
        'grid_mapping_name': 'geostationary',
        'perspective_point_height': sat_height,
        'longitude_of_projection_origin': sat_lon,
        'semi_major_axis': 6378137.0,
        'semi_minor_axis': 6356752.31414,
        'sweep_angle_axis': 'x'
    })

    # Create transformer to WGS84
    transformer = Transformer.from_crs(goes_crs, "EPSG:4326", always_xy=True)

    # Get corner coordinates in GOES projection (radians * sat_height)
    x_min, x_max = ds.x.min().values * sat_height, ds.x.max().values * sat_height
    y_min, y_max = ds.y.min().values * sat_height, ds.y.max().values * sat_height

    print(f"\nGOES projection extent (meters):")
    print(f"  X: {x_min:,.0f} to {x_max:,.0f}")
    print(f"  Y: {y_min:,.0f} to {y_max:,.0f}")

    # Transform corners to lat/lon
    corners = [
        (x_min, y_min),  # SW
        (x_max, y_min),  # SE
        (x_min, y_max),  # NW
        (x_max, y_max),  # NE
    ]

    print(f"\nGeographic extent (WGS84 lat/lon):")
    latlon_corners = []
    for i, (x, y) in enumerate(corners):
        lon, lat = transformer.transform(x, y)
        latlon_corners.append((lat, lon))
        corner_name = ['SW', 'SE', 'NW', 'NE'][i]
        print(f"  {corner_name}: {lat:.2f}°, {lon:.2f}°")

    lats = [c[0] for c in latlon_corners]
    lons = [c[1] for c in latlon_corners]
    print(f"\nBounding box:")
    print(f"  Latitude:  {min(lats):.2f}° to {max(lats):.2f}°")
    print(f"  Longitude: {min(lons):.2f}° to {max(lons):.2f}°")

    # Check Brazil coverage
    print(f"\n" + "="*80)
    print("BRAZIL COVERAGE ANALYSIS")
    print("="*80)
    print("Brazil extent: -34° to +5° lat, -74° to -34° lon")
    print(f"GOES-19 extent: {min(lats):.2f}° to {max(lats):.2f}° lat, {min(lons):.2f}° to {max(lons):.2f}° lon")
    print(f"\nMissing coverage:")
    if min(lats) > -34:
        print(f"  ⚠️  Southern Brazil: {min(lats):.2f}° to -34° (missing {abs(-34 - min(lats)):.2f}° of latitude)")
        print(f"      This includes: São Paulo, Paraná, Santa Catarina, Rio Grande do Sul")
    else:
        print(f"  ✓ Southern Brazil covered")

    if max(lons) < -34:
        print(f"  ⚠️  Eastern Brazil: {max(lons):.2f}° to -34° (missing {abs(-34 - max(lons)):.2f}° of longitude)")
        print(f"      This includes: parts of coastal areas")
    else:
        print(f"  ✓ Eastern Brazil covered")

ds.close()
print("\n" + "="*80)
