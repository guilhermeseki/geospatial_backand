#!/usr/bin/env python3
"""
Enable time dimension for wind_speed and ndvi_modis layers
"""
import sys
sys.path.insert(0, '/opt/geospatial_backend')

from create_time_enabled_mosaic import GeoServerMosaicManager
from app.config.settings import get_settings

def main():
    settings = get_settings()

    GEOSERVER_URL = settings.geoserver_local_url
    USERNAME = settings.GEOSERVER_ADMIN_USER
    PASSWORD = settings.GEOSERVER_ADMIN_PASSWORD

    print("=" * 80)
    print("ENABLING TIME DIMENSION FOR WIND_SPEED AND NDVI_MODIS")
    print("=" * 80)

    # Enable time for wind_speed
    print("\n1. Enabling time dimension for wind_speed...")
    wind_manager = GeoServerMosaicManager(GEOSERVER_URL, USERNAME, PASSWORD, "wind_ws")
    wind_success = wind_manager.enable_time_dimension(
        "wind_speed",
        presentation="LIST",
        default_value_strategy="MAXIMUM",
        nearest_match=False
    )

    # Enable time for ndvi_modis
    print("\n2. Enabling time dimension for ndvi_modis...")
    ndvi_manager = GeoServerMosaicManager(GEOSERVER_URL, USERNAME, PASSWORD, "ndvi_ws")
    ndvi_success = ndvi_manager.enable_time_dimension(
        "ndvi_modis",
        presentation="LIST",
        default_value_strategy="MAXIMUM",
        nearest_match=False
    )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if wind_success:
        print("✓ wind_speed: Time dimension enabled")
    else:
        print("✗ wind_speed: Failed to enable time dimension")

    if ndvi_success:
        print("✓ ndvi_modis: Time dimension enabled")
    else:
        print("✗ ndvi_modis: Failed to enable time dimension")

    print("\nTest with:")
    print(f"  Wind: {GEOSERVER_URL}/wind_ws/wms?service=WMS&version=1.1.1&request=GetMap&layers=wind_speed&time=2025-10-15&...")
    print(f"  NDVI: {GEOSERVER_URL}/ndvi_ws/wms?service=WMS&version=1.1.1&request=GetMap&layers=ndvi_modis&time=2025-10-08&...")
    print("=" * 80)

if __name__ == "__main__":
    main()
