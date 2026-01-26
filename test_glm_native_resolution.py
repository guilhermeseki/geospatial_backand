#!/usr/bin/env python3
"""
Download a single GLM FED file and check its native resolution
"""
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path
import xarray as xr
import numpy as np
from app.config.settings import get_settings

settings = get_settings()

# Check credentials
username = settings.EARTHDATA_USERNAME
password = settings.EARTHDATA_PASSWORD

if not username or not password:
    print("ERROR: Need EARTHDATA_USERNAME and EARTHDATA_PASSWORD")
    exit(1)

print(f"Using credentials: {username}")

# Download a single file from 2025-04-04
cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json"

params = {
    "short_name": "glmgoesL3",
    "provider": "GHRC_DAAC",
    "temporal": "2025-04-04T12:00:00Z,2025-04-04T12:01:00Z",
    "page_size": 10
}

print("\nSearching for GLM files...")
response = requests.get(cmr_url, params=params, timeout=60)
response.raise_for_status()

granules = response.json()['feed']['entry']
print(f"Found {len(granules)} granules")

if not granules:
    print("No granules found!")
    exit(1)

# Get first granule
granule = granules[0]
print(f"\nGranule: {granule['title']}")

# Find download link
download_url = None
for link in granule.get('links', []):
    if link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/data#':
        download_url = link.get('href')
        break

if not download_url:
    print("No download URL found!")
    exit(1)

print(f"Download URL: {download_url}")

# Download file
output_dir = Path("/tmp/glm_test")
output_dir.mkdir(exist_ok=True)

filename = download_url.split('/')[-1]
local_file = output_dir / filename

print(f"\nDownloading to: {local_file}")

session = requests.Session()
session.auth = HTTPBasicAuth(username, password)

file_response = session.get(download_url, timeout=120, stream=True)
file_response.raise_for_status()

with open(local_file, 'wb') as f:
    for chunk in file_response.iter_content(chunk_size=8192):
        f.write(chunk)

print(f"✓ Downloaded: {local_file.stat().st_size / 1024:.1f} KB")

# Open and check resolution
print("\n" + "="*80)
print("CHECKING NATIVE RESOLUTION")
print("="*80)

ds = xr.open_dataset(local_file)
print("\nDataset structure:")
print(ds)

print("\nCoordinate info:")
if 'lat' in ds.coords:
    lat = ds['lat']
    lon = ds['lon']
    print(f"Latitude: {len(lat)} points")
    print(f"Longitude: {len(lon)} points")

    lat_spacing = float(np.diff(lat.values).mean())
    lon_spacing = float(np.diff(lon.values).mean())

    print(f"\nSpacing:")
    print(f"  Latitude: {lat_spacing:.6f}° = {abs(lat_spacing * 111.32):.2f} km")
    print(f"  Longitude: {lon_spacing:.6f}° = {abs(lon_spacing * 111.32):.2f} km")

    print(f"\nCoverage:")
    print(f"  Lat range: {float(lat.min()):.2f} to {float(lat.max()):.2f}")
    print(f"  Lon range: {float(lon.min()):.2f} to {float(lon.max()):.2f}")

print("\nData variables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims} - {ds[var].shape}")

print("\nAttributes:")
for key, val in ds.attrs.items():
    print(f"  {key}: {val}")
