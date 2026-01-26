#!/usr/bin/env python3
"""
Regenerate MERGE shapefile index for GeoServer.
"""
from pathlib import Path
from app.workflows.data_processing.tasks import refresh_mosaic_shapefile
from app.workflows.data_processing.schemas import DataSource

if __name__ == "__main__":
    print("Regenerating MERGE shapefile index...")
    try:
        result = refresh_mosaic_shapefile.fn(DataSource.MERGE)
        print("✓ Successfully regenerated MERGE shapefile index")
    except Exception as e:
        print(f"✗ Failed to regenerate shapefile: {e}")
        import traceback
        traceback.print_exc()
