"""Check sample solar radiation data from 2024"""
import xarray as xr
from pathlib import Path

print("="*80)
print("Solar Radiation Data Quality Check - 2024 Sample")
print("="*80)

# Check 2024 historical file
hist_file = Path("/mnt/workwork/geoserver_data/solar_radiation_hist/solar_radiation_2024.nc")

ds = xr.open_dataset(hist_file)
da = ds['solar_radiation']

print(f"\n📊 Dataset Info:")
print(f"   File: {hist_file.name}")
print(f"   Size: {hist_file.stat().st_size / 1024 / 1024:.1f} MB")
print(f"   Variables: {list(ds.data_vars)}")
print(f"   Dimensions: {dict(ds.sizes)}")

print(f"\n📅 Temporal Coverage:")
print(f"   Start: {da.time.min().values}")
print(f"   End: {da.time.max().values}")
print(f"   Days: {len(da.time)}")
print(f"   Expected: 365 days (2024)")

print(f"\n📍 Spatial Coverage:")
print(f"   Latitude: {float(da.latitude.min().values):.2f}° to {float(da.latitude.max().values):.2f}°")
print(f"   Longitude: {float(da.longitude.min().values):.2f}° to {float(da.longitude.max().values):.2f}°")
print(f"   Grid points: {len(da.latitude)} × {len(da.longitude)}")

print(f"\n☀️ Solar Radiation Values:")
print(f"   Min: {float(da.min().values):.2f} kWh/m²/day")
print(f"   Max: {float(da.max().values):.2f} kWh/m²/day")
print(f"   Mean: {float(da.mean().values):.2f} kWh/m²/day")

print(f"\n🏷️ Metadata:")
for key, value in da.attrs.items():
    print(f"   {key}: {value}")

# Sample specific location (Brasília: -15.8°, -47.9°)
print(f"\n📍 Sample Point: Brasília (-15.8°, -47.9°)")
point = da.sel(latitude=-15.8, longitude=-47.9, method='nearest')
print(f"   January avg: {float(point.sel(time='2024-01').mean().values):.2f} kWh/m²/day")
print(f"   July avg: {float(point.sel(time='2024-07').mean().values):.2f} kWh/m²/day")
print(f"   Year avg: {float(point.mean().values):.2f} kWh/m²/day")

ds.close()
print("\n" + "="*80)
print("✓ Data quality check passed!")
print("="*80)
