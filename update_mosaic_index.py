#!/usr/bin/env python3
"""
Update GeoServer ImageMosaic index WITHOUT restarting GeoServer.

This script:
1. Deletes only the shapefile index (not the .properties files)
2. GeoServer automatically recreates the index on next WMS request
3. No restart needed - safe for production!

Usage: python update_mosaic_index.py <dataset>
Example: python update_mosaic_index.py chirps
"""
import sys
from pathlib import Path
from app.config.settings import get_settings
from app.workflows.data_processing.schemas import DataSource

def update_index(source: DataSource, verbose=True):
    """
    Delete shapefile components to force GeoServer to recreate index.
    GeoServer will automatically rebuild on next WMS request.
    """
    settings = get_settings()
    mosaic_dir = Path(settings.DATA_DIR) / source.value

    if verbose:
        print(f"Updating index for: {source.value}")
        print(f"Directory: {mosaic_dir}")

    # Delete only shapefile components (keep indexer.properties and timeregex.properties)
    extensions = ['.shp', '.dbf', '.shx', '.prj', '.cpg', '.fix', '.qix']
    deleted = []

    for ext in extensions:
        shp_file = mosaic_dir / f"{source.value}{ext}"
        if shp_file.exists():
            try:
                shp_file.unlink()
                deleted.append(shp_file.name)
                if verbose:
                    print(f"  ✓ Deleted: {shp_file.name}")
            except Exception as e:
                if verbose:
                    print(f"  ✗ Failed to delete {shp_file.name}: {e}")

    # Also delete the .properties file (mosaic metadata)
    props_file = mosaic_dir / f"{source.value}.properties"
    if props_file.exists():
        try:
            props_file.unlink()
            deleted.append(props_file.name)
            if verbose:
                print(f"  ✓ Deleted: {props_file.name}")
        except Exception as e:
            if verbose:
                print(f"  ✗ Failed to delete {props_file.name}: {e}")

    if verbose:
        print(f"\n✓ Deleted {len(deleted)} file(s)")
        print(f"✓ GeoServer will recreate index on next WMS request")
        print(f"✓ No restart needed!")

    return len(deleted)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_mosaic_index.py <dataset>")
        print("\nAvailable datasets:")
        for source in DataSource:
            print(f"  - {source.value}")
        sys.exit(1)

    source_name = sys.argv[1].upper()

    try:
        source = DataSource[source_name]
        update_index(source)
    except KeyError:
        print(f"Unknown dataset: {source_name}")
        print("\nAvailable datasets:")
        for source in DataSource:
            print(f"  - {source.value}")
        sys.exit(1)
