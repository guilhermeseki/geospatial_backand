#!/usr/bin/env python3
"""
Harvest new granules into GeoServer ImageMosaic without rebuilding entire index.
This is for operational use when new files are added.
"""
import requests
import sys
from app.config.settings import get_settings
from app.workflows.data_processing.schemas import DataSource

def harvest_granules(source: DataSource):
    """
    Trigger GeoServer to scan for and add new granules to existing mosaic index.
    This preserves the existing shapefile and only adds new files.
    """
    settings = get_settings()

    print(f"Harvesting new granules for {source.value}...")

    # GeoServer REST API endpoint for harvesting
    harvest_url = (
        f"{settings.geoserver_local_url}/rest/workspaces/"
        f"{settings.GEOSERVER_WORKSPACE}/coveragestores/{source.value}/"
        f"external.imagemosaic/index/granules"
    )

    print(f"URL: {harvest_url}")

    # Make POST request to trigger harvest
    try:
        resp = requests.post(
            harvest_url,
            auth=(settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD),
            headers={"Content-Type": "text/plain"},
            timeout=120
        )

        print(f"Response status: {resp.status_code}")

        if resp.status_code in [200, 201, 202]:
            print(f"✓ Successfully triggered harvest for {source.value}")
            print(f"  GeoServer will scan for new files and update the index")
            return True
        else:
            print(f"✗ Failed to harvest: {resp.status_code}")
            print(f"  Response: {resp.text[:500]}")
            return False

    except Exception as e:
        print(f"✗ Error during harvest: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python harvest_new_granules.py <source>")
        print("Example: python harvest_new_granules.py chirps")
        print("Available sources: chirps, merge, temp_max, temp_mean, temp_min, wind_speed, glm_fed, ndvi_modis")
        sys.exit(1)

    source_name = sys.argv[1].upper()
    try:
        source = DataSource[source_name]
        harvest_granules(source)
    except KeyError:
        print(f"Unknown source: {source_name}")
        print("Available: chirps, merge, temp_max, temp_mean, temp_min, wind_speed, glm_fed, ndvi_modis")
        sys.exit(1)
