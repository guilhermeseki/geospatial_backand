#!/usr/bin/env python3
"""
Refresh CHIRPS mosaic index - operational approach
"""
from pathlib import Path
from app.workflows.data_processing.schemas import DataSource
from app.config.settings import get_settings
import requests
import time

def refresh_chirps():
    settings = get_settings()
    source = DataSource.CHIRPS
    mosaic_dir = Path(settings.DATA_DIR) / source.value

    print(f"Refreshing {source.value} mosaic index...")
    print(f"Directory: {mosaic_dir}")

    # Step 1: Delete shapefile components
    print("\n1. Deleting old shapefile index...")
    deleted = 0
    for f in mosaic_dir.glob(f"{source.value}.*"):
        try:
            f.unlink()
            print(f"   Deleted: {f.name}")
            deleted += 1
        except Exception as e:
            print(f"   Failed to delete {f}: {e}")

    print(f"   Total deleted: {deleted} files")

    # Step 2: Reload GeoServer
    print("\n2. Reloading GeoServer...")
    reload_url = f"{settings.geoserver_local_url}/rest/reload"
    resp = requests.post(
        reload_url,
        auth=(settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD)
    )
    if resp.status_code == 200:
        print("   ✓ GeoServer reload triggered")
    else:
        print(f"   ✗ Failed: {resp.status_code}")

    time.sleep(3)

    # Step 3: Trigger WMS GetCapabilities to rebuild index
    print("\n3. Triggering index rebuild via GetCapabilities...")
    cap_url = f"{settings.geoserver_local_url}/wms?service=WMS&version=1.3.0&request=GetCapabilities&layers={settings.GEOSERVER_WORKSPACE}:{source.value}"
    resp = requests.get(cap_url)
    if resp.status_code == 200:
        print("   ✓ GetCapabilities successful - index rebuilding...")
    else:
        print(f"   ✗ Failed: {resp.status_code}")

    print("\n4. Waiting for index to rebuild...")
    time.sleep(5)

    print("\n✓ Refresh complete! Shapefile will be regenerated on next WMS request.")

if __name__ == "__main__":
    refresh_chirps()
