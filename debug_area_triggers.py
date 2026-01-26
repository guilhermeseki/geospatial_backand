#!/usr/bin/env python3
"""
Debug script to find the actual error in area triggers endpoint
Run this directly to bypass the FastAPI error handling
"""
import sys
sys.path.insert(0, '/opt/geospatial_backend')

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path

print("="*70)
print("Step 1: Load the GLM FED dataset directly")
print("="*70)

ds_path = Path('/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc')
print(f"Loading: {ds_path}")

ds = xr.open_dataset(ds_path)
print(f"✓ Dataset loaded")
print(f"  Dims: {dict(ds.dims)}")
print(f"  Coords: {list(ds.coords)}")
print(f"  Vars: {list(ds.data_vars)}")
print(f"  Latitude range: {float(ds.latitude.min()):.2f} to {float(ds.latitude.max()):.2f}")
print(f"  Longitude range: {float(ds.longitude.min()):.2f} to {float(ds.longitude.max()):.2f}")

# Check latitude ordering
print(f"  Latitude is decreasing: {ds.latitude[0] > ds.latitude[-1]}")

print("\n" + "="*70)
print("Step 2: Test spatial slicing for area query")
print("="*70)

# Test parameters (Brasília area)
lat = -15.8
lon = -47.9
radius_km = 50
DEGREES_TO_KM = 111.32

radius_deg = radius_km / DEGREES_TO_KM
lat_min = lat - radius_deg
lat_max = lat + radius_deg
lon_min = lon - radius_deg
lon_max = lon + radius_deg

print(f"Center: ({lat}, {lon})")
print(f"Radius: {radius_km} km = {radius_deg:.3f} degrees")
print(f"Bbox: lat=[{lat_min:.3f}, {lat_max:.3f}], lon=[{lon_min:.3f}, {lon_max:.3f}]")

try:
    # Try slicing with reversed order (for decreasing latitude)
    print("\nTrying spatial slice (latitude reversed)...")
    ds_slice = ds.sel(
        latitude=slice(lat_max, lat_min),  # Reversed for decreasing coords
        longitude=slice(lon_min, lon_max)
    )
    print(f"✓ Slice successful")
    print(f"  Slice dims: {dict(ds_slice.dims)}")

    if ds_slice.dims['latitude'] == 0 or ds_slice.dims['longitude'] == 0:
        print("  ⚠ WARNING: Empty slice! No data in this region")

except Exception as e:
    print(f"✗ Slice failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("Step 3: Test haversine distance calculation")
print("="*70)

try:
    from app.utils.geo import haversine_distance

    print(f"Calculating distances from center ({lat}, {lon})...")
    distances_km = haversine_distance(
        lon1=lon,
        lat1=lat,
        lon2=ds_slice.longitude,
        lat2=ds_slice.latitude
    )
    print(f"✓ Haversine calculation successful")
    print(f"  Distance array shape: {distances_km.shape}")
    print(f"  Min distance: {float(distances_km.min()):.2f} km")
    print(f"  Max distance: {float(distances_km.max()):.2f} km")

    # Create circular mask
    circular_mask = (distances_km <= radius_km)
    print(f"  Points within radius: {circular_mask.sum().values}")

except Exception as e:
    print(f"✗ Haversine calculation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("Step 4: Test time slicing and trigger calculation")
print("="*70)

try:
    start_date = pd.to_datetime("2025-11-01")
    end_date = pd.to_datetime("2025-11-30")

    print(f"Time range: {start_date.date()} to {end_date.date()}")

    # Add time slicing
    ds_full = ds_slice.sel(time=slice(start_date, end_date))
    print(f"✓ Time slice successful")
    print(f"  Time points: {len(ds_full.time)}")

    # Get FED data
    fed_data = ds_full['fed_30min_max']
    print(f"✓ Got fed_30min_max variable")
    print(f"  Shape: {fed_data.shape}")

    # Apply trigger
    trigger = 3.0
    trigger_mask_3D = (fed_data > trigger) & circular_mask
    print(f"✓ Created trigger mask")

    # Extract values
    print("\nComputing results (this may take a moment)...")
    exceeding_values = fed_data.where(trigger_mask_3D)
    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])
    computed = exceeding_flat.compute()
    exceeding_series = computed.to_series().dropna()

    print(f"✓ Computation successful!")
    print(f"  Total exceedances: {len(exceeding_series)}")

    # Group by date
    grouped = {}
    for index, value in exceeding_series.items():
        if not np.isfinite(value):
            continue
        time_val, lat_val, lon_val = index
        date_str = str(pd.Timestamp(time_val).date())
        if date_str not in grouped:
            grouped[date_str] = []
        grouped[date_str].append({
            "lat": round(float(lat_val), 4),
            "lon": round(float(lon_val), 4),
            "value": round(float(value), 2)
        })

    print(f"✓ Grouped by date: {len(grouped)} dates with exceedances")

    # Show sample
    if grouped:
        sample_date = list(grouped.keys())[0]
        print(f"\nSample date: {sample_date}")
        print(f"  Points: {len(grouped[sample_date])}")
        print(f"  First few: {grouped[sample_date][:3]}")

    print("\n✅ ALL TESTS PASSED - Area triggers should work!")

except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("Step 5: Test polygon calculation")
print("="*70)

try:
    from app.utils.polygon import PolygonProcessor

    # Create simple polygon around Brasília
    coords = [
        (-48.0, -15.7),
        (-47.8, -15.7),
        (-47.8, -15.9),
        (-48.0, -15.9),
        (-48.0, -15.7)
    ]

    print(f"Testing polygon with {len(coords)} vertices")

    class MockRequest:
        coordinates = coords
        source = "glm_fed"
        start_date = "2025-11-01"
        end_date = "2025-11-30"
        statistic = "mean"
        trigger = None
        consecutive_days = 1

    request = MockRequest()

    print("Creating PolygonProcessor...")
    processor = PolygonProcessor(ds, 'fed_30min_max')

    print("Calculating polygon stats...")
    result = processor.calculate_polygon_stats(request)

    print(f"✓ Polygon calculation successful!")
    print(f"  Results: {len(result.get('results', []))} dates")
    if result.get('results'):
        print(f"  Sample: {result['results'][:3]}")

    print("\n✅ POLYGON TEST PASSED!")

except Exception as e:
    print(f"\n✗ Polygon test failed: {e}")
    import traceback
    traceback.print_exc()

ds.close()
print("\nAll tests completed.")
