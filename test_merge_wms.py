#!/usr/bin/env python3
"""
Test MERGE WMS layer to trigger shapefile regeneration and check alignment.
"""
import requests
from datetime import date, timedelta

# Test WMS GetMap request
def test_wms_getmap():
    """Test WMS GetMap to trigger shapefile creation"""
    print("=" * 80)
    print("TESTING MERGE WMS LAYER")
    print("=" * 80)

    test_date = "2015-11-01"
    url = (
        "http://localhost:8080/geoserver/wms"
        "?service=WMS"
        "&version=1.1.1"
        "&request=GetMap"
        "&layers=precipitation_ws:merge"
        "&bbox=-74,-34,-35,5"
        "&width=800"
        "&height=600"
        "&srs=EPSG:4326"
        f"&time={test_date}"
        "&format=image/png"
    )

    print(f"\nRequesting map for date: {test_date}")
    print(f"URL: {url[:100]}...")

    try:
        resp = requests.get(url, timeout=30)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")

        if resp.status_code == 200:
            if 'image' in resp.headers.get('Content-Type', ''):
                print("✓ WMS request successful - image returned")
                with open('/tmp/merge_test.png', 'wb') as f:
                    f.write(resp.content)
                print(f"  Saved test image to: /tmp/merge_test.png")
            else:
                print(f"✗ Unexpected content type")
                print(f"Response: {resp.text[:500]}")
        else:
            print(f"✗ WMS request failed")
            print(f"Response: {resp.text[:500]}")

    except Exception as e:
        print(f"✗ Error: {e}")

    # Check if shapefile was created
    print("\n" + "=" * 80)
    print("CHECKING SHAPEFILE CREATION")
    print("=" * 80)
    import os
    from pathlib import Path

    mosaic_dir = Path("/mnt/workwork/geoserver_data/merge")
    shapefiles = list(mosaic_dir.glob("*.shp"))

    if shapefiles:
        print(f"✓ Found {len(shapefiles)} shapefile(s):")
        for shp in shapefiles:
            stat = shp.stat()
            print(f"  {shp.name} ({stat.st_size} bytes)")
    else:
        print("✗ No shapefiles found yet")

if __name__ == "__main__":
    test_wms_getmap()
