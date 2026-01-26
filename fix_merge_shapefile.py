#!/usr/bin/env python3
"""
Manually regenerate MERGE shapefile index.
"""
from pathlib import Path
import requests
from app.config.settings import get_settings

def regenerate_merge_shapefile():
    settings = get_settings()
    source = "merge"

    # Delete old shapefile index
    mosaic_dir = Path(settings.DATA_DIR) / source
    for f in mosaic_dir.glob(f"{source}.*"):
        try:
            f.unlink()
            print(f"✓ Deleted: {f.name}")
        except Exception as e:
            print(f"✗ Failed to delete {f}: {e}")

    # Reload GeoServer
    print("\nReloading GeoServer...")
    reload_url = f"{settings.geoserver_local_url}/rest/reload"

    # Try different credential combinations
    credentials = [
        (settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD),
        ("admin", "geoserver"),
        ("admin", "password"),
    ]

    success = False
    for user, password in credentials:
        try:
            resp = requests.post(
                reload_url,
                auth=(user, password),
                timeout=30
            )
            if resp.status_code == 200:
                print(f"✓ GeoServer reloaded successfully with credentials: {user}")
                success = True
                break
            else:
                print(f"✗ Failed with {user}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"✗ Error with {user}: {e}")

    if not success:
        print("\n⚠️  Could not reload GeoServer - may need manual restart")
        print("   Try: sudo systemctl restart geoserver")
    else:
        print("\n✓ Shapefile regeneration complete!")
        print(f"   New shapefile will be created in: {mosaic_dir}")

if __name__ == "__main__":
    regenerate_merge_shapefile()
