"""Verify solar radiation data covers all regions of Brazil"""
import xarray as xr
from pathlib import Path

print("="*80)
print("Brazil Coverage Verification - Solar Radiation Data")
print("="*80)

# Brazil's approximate geographic bounds
brazil_bounds = {
    'north': 5.27,      # Roraima (northernmost point)
    'south': -33.75,    # Rio Grande do Sul (southernmost point)
    'east': -34.79,     # Ponta do Seixas, Paraíba (easternmost point)
    'west': -73.99      # Acre (westernmost point)
}

print(f"\n📍 Brazil Geographic Bounds:")
print(f"   North: {brazil_bounds['north']}°")
print(f"   South: {brazil_bounds['south']}°")
print(f"   East: {brazil_bounds['east']}°")
print(f"   West: {brazil_bounds['west']}°")
print(f"   Span: {brazil_bounds['north'] - brazil_bounds['south']:.2f}° lat × {brazil_bounds['east'] - brazil_bounds['west']:.2f}° lon")

# Check data coverage
hist_file = Path("/mnt/workwork/geoserver_data/solar_radiation_hist/solar_radiation_2024.nc")
ds = xr.open_dataset(hist_file)
da = ds['solar_radiation']

data_bounds = {
    'north': float(da.latitude.max().values),
    'south': float(da.latitude.min().values),
    'east': float(da.longitude.max().values),
    'west': float(da.longitude.min().values)
}

print(f"\n📊 Solar Radiation Data Coverage:")
print(f"   North: {data_bounds['north']}°")
print(f"   South: {data_bounds['south']}°")
print(f"   East: {data_bounds['east']}°")
print(f"   West: {data_bounds['west']}°")
print(f"   Span: {data_bounds['north'] - data_bounds['south']:.2f}° lat × {data_bounds['east'] - data_bounds['west']:.2f}° lon")

# Check if Brazil is fully covered
print(f"\n✓ Coverage Check:")
lat_covered = (data_bounds['south'] <= brazil_bounds['south'] and
               data_bounds['north'] >= brazil_bounds['north'])
lon_covered = (data_bounds['west'] <= brazil_bounds['west'] and
               data_bounds['east'] >= brazil_bounds['east'])

print(f"   Latitude coverage: {'✓ COMPLETE' if lat_covered else '✗ INCOMPLETE'}")
print(f"     Data: {data_bounds['south']}° to {data_bounds['north']}°")
print(f"     Brazil needs: {brazil_bounds['south']}° to {brazil_bounds['north']}°")
if lat_covered:
    print(f"     Extra margin: {brazil_bounds['south'] - data_bounds['south']:.2f}° south, {data_bounds['north'] - brazil_bounds['north']:.2f}° north")

print(f"\n   Longitude coverage: {'✓ COMPLETE' if lon_covered else '✗ INCOMPLETE'}")
print(f"     Data: {data_bounds['west']}° to {data_bounds['east']}°")
print(f"     Brazil needs: {brazil_bounds['west']}° to {brazil_bounds['east']}°")
if lon_covered:
    print(f"     Extra margin: {data_bounds['west'] - brazil_bounds['west']:.2f}° west, {brazil_bounds['east'] - data_bounds['east']:.2f}° east")

# Check major Brazilian cities
cities = {
    'São Paulo': (-23.55, -46.63),
    'Rio de Janeiro': (-22.91, -43.17),
    'Brasília': (-15.80, -47.93),
    'Salvador': (-12.97, -38.51),
    'Fortaleza': (-3.72, -38.54),
    'Belo Horizonte': (-19.92, -43.94),
    'Manaus': (-3.12, -60.02),
    'Curitiba': (-25.43, -49.27),
    'Recife': (-8.05, -34.88),
    'Porto Alegre': (-30.03, -51.23),
    'Belém': (-1.46, -48.50),
    'Goiânia': (-16.69, -49.26),
    'Guarulhos': (-23.46, -46.53),
    'Campinas': (-22.91, -47.06),
    'São Luís': (-2.54, -44.30)
}

print(f"\n🏙️ Major Brazilian Cities Coverage:")
all_covered = True
for city, (lat, lon) in cities.items():
    # Check if city is within data bounds
    in_bounds = (data_bounds['south'] <= lat <= data_bounds['north'] and
                 data_bounds['west'] <= lon <= data_bounds['east'])
    status = "✓" if in_bounds else "✗"
    print(f"   {status} {city:20s} ({lat:7.2f}°, {lon:7.2f}°)")
    if not in_bounds:
        all_covered = False

# Sample data at a few locations
print(f"\n☀️ Sample Solar Radiation Values (2024 annual average):")
for city, (lat, lon) in list(cities.items())[:5]:
    try:
        point = da.sel(latitude=lat, longitude=lon, method='nearest')
        value = float(point.mean().values)
        print(f"   {city:20s}: {value:.2f} kWh/m²/day")
    except Exception as e:
        print(f"   {city:20s}: Error - {e}")

ds.close()

print(f"\n" + "="*80)
if lat_covered and lon_covered and all_covered:
    print("✅ COMPLETE COVERAGE: All regions of Brazil are covered!")
else:
    print("⚠️  INCOMPLETE COVERAGE: Some regions may be missing")
print("="*80)
