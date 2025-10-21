# setup_indexers.py
import sys
sys.path.insert(0, '/opt/geospatial_backend')

from app.workflows.data_processing.geoserver_indexers import setup_geoserver_indexers_flow

# Create indexers for all directories
print("Setting up GeoServer indexers for all TIF directories...")
result = setup_geoserver_indexers_flow()

print(f"\nDone!")
print(f"Created: {result['created']}")
print(f"Skipped: {result['skipped']}")
print(f"Errors: {result['errors']}")