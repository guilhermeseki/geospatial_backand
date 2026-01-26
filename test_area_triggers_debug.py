#!/usr/bin/env python3
"""
Debug area_triggers for CHIRPS to understand why it returns 0 results
"""
import sys
sys.path.insert(0, '/opt/geospatial_backend')

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
from app.config.settings import get_settings
from app.utils.geo import haversine_distance, DEGREES_TO_KM

settings = get_settings()

# Load CHIRPS historical dataset
hist_dir = Path(settings.DATA_DIR) / "chirps_hist"
nc_files = sorted(hist_dir.glob("chirps_*.nc"))
print(f"Loading {len(nc_files)} CHIRPS NetCDF files...")
ds = xr.open_mfdataset(
    nc_files,
    combine="nested",
    concat_dim="time",
    engine="netcdf4",
    chunks={"time": 365, "latitude": 20, "longitude": 20},
    join='override',
    combine_attrs='override'
)

print(f"\nDataset loaded:")
print(f"  Time range: {pd.to_datetime(ds.time.min().values).date()} to {pd.to_datetime(ds.time.max().values).date()}")
print(f"  Dimensions: {dict(ds.dims)}")
print(f"  Variables: {list(ds.data_vars)}")

# Test parameters (near Brasília)
lat = -15.8
lon = -47.9
radius_km = 25
trigger_mm = 50.0
start_date = pd.to_datetime("2024-01-01").date()
end_date = pd.to_datetime("2024-01-31").date()

print(f"\n{'='*80}")
print(f"Testing area_triggers logic")
print(f"{'='*80}")
print(f"Location: ({lat}, {lon})")
print(f"Radius: {radius_km} km")
print(f"Trigger: {trigger_mm} mm")
print(f"Date range: {start_date} to {end_date}")

# Calculate bounding box
radius_deg = radius_km / DEGREES_TO_KM
lat_min = lat - radius_deg
lat_max = lat + radius_deg
lon_min = lon - radius_deg
lon_max = lon + radius_deg

print(f"\nBounding box:")
print(f"  Latitude: {lat_min:.4f} to {lat_max:.4f}")
print(f"  Longitude: {lon_min:.4f} to {lon_max:.4f}")
print(f"  Radius in degrees: {radius_deg:.4f}°")

# Slice the dataset
print(f"\nSlicing dataset...")
ds_slice = ds.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max),
    time=slice(start_date, end_date)
)

print(f"Sliced dimensions: {dict(ds_slice.dims)}")
print(f"  Latitude range: {float(ds_slice.latitude.min())} to {float(ds_slice.latitude.max())}")
print(f"  Longitude range: {float(ds_slice.longitude.min())} to {float(ds_slice.longitude.max())}")
print(f"  Time range: {pd.to_datetime(ds_slice.time.min().values).date()} to {pd.to_datetime(ds_slice.time.max().values).date()}")

# Get precipitation data
var_name = "precipitation" if "precipitation" in ds_slice.data_vars else "precip"
print(f"\nVariable name: {var_name}")
precip_data = ds_slice[var_name]

# Calculate circular mask
print(f"\nCalculating haversine distances...")
distances_km = haversine_distance(
    lon1=lon,
    lat1=lat,
    lon2=ds_slice.longitude,
    lat2=ds_slice.latitude
)
print(f"Distance array shape: {distances_km.shape}")
print(f"Distance min: {float(distances_km.min()):.2f} km")
print(f"Distance max: {float(distances_km.max()):.2f} km")

circular_mask = (distances_km <= radius_km).compute()
print(f"\nCircular mask:")
print(f"  Shape: {circular_mask.shape}")
print(f"  Points within radius: {circular_mask.sum().values}")

# Check precipitation values
print(f"\nPrecipitation data:")
print(f"  Shape: {precip_data.shape}")
precip_computed = precip_data.compute()
print(f"  Min: {float(precip_computed.min()):.2f} mm")
print(f"  Max: {float(precip_computed.max()):.2f} mm")
print(f"  Mean: {float(precip_computed.mean()):.2f} mm")

# Check trigger mask
trigger_mask_2D = (precip_computed > trigger_mm)
print(f"\nPrecipitation > {trigger_mm} mm:")
print(f"  Total cells exceeding: {trigger_mask_2D.sum().values}")

# Combine masks
trigger_mask_3D = (precip_computed > trigger_mm) & circular_mask
print(f"\nCombined mask (precipitation > {trigger_mm} AND within {radius_km} km):")
exceeding_count = trigger_mask_3D.sum()
print(f"  Total exceedances: {exceeding_count.values}")

if exceeding_count.values > 0:
    # Extract exceedances
    exceeding_values = precip_computed.where(trigger_mask_3D)
    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])
    exceeding_flat_computed = exceeding_flat.to_series().dropna()

    print(f"\nExceedances found: {len(exceeding_flat_computed)}")
    print(f"\nFirst 10 exceedances:")
    for i, (index, value) in enumerate(exceeding_flat_computed.head(10).items()):
        time_val, lat_val, lon_val = index
        date_str = pd.to_datetime(time_val).date()
        dist_km = haversine_distance(lon, lat, lon_val, lat_val)
        print(f"  {i+1}. Date: {date_str}, Lat: {lat_val:.4f}, Lon: {lon_val:.4f}, Value: {value:.2f} mm, Distance: {dist_km:.2f} km")

    # Group by date
    from collections import defaultdict
    grouped = defaultdict(list)
    for index, value in exceeding_flat_computed.items():
        time_val, lat_val, lon_val = index
        date_str = str(pd.to_datetime(time_val).date())
        grouped[date_str].append({
            "latitude": round(float(lat_val), 5),
            "longitude": round(float(lon_val), 5),
            "precipitation_mm": round(float(value), 2)
        })

    print(f"\nExceedances by date:")
    for date_str in sorted(grouped.keys()):
        print(f"  {date_str}: {len(grouped[date_str])} locations")
else:
    print("\n❌ No exceedances found!")

    # Debug: let's check some sample values
    print("\nSample precipitation values at center point:")
    center_ts = precip_computed.sel(latitude=lat, longitude=lon, method="nearest")

    print(f"\nValues for nearest point to ({lat}, {lon}):")
    print(f"  Actual coords: ({float(center_ts.latitude)}, {float(center_ts.longitude)})")

    for time_val in center_ts.time[:10].values:
        date_str = pd.to_datetime(time_val).date()
        val = float(center_ts.sel(time=time_val).values)
        print(f"  {date_str}: {val:.2f} mm")

print(f"\n{'='*80}")
print(f"Debug complete")
print(f"{'='*80}")
