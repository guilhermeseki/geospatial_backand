"""
Create time-enabled ImageMosaic coverage stores and layers in GeoServer
"""
import requests
from requests.auth import HTTPBasicAuth
import json
from pathlib import Path


class GeoServerMosaicManager:
    def __init__(self, geoserver_url, username, password, workspace):
        self.base_url = geoserver_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.workspace = workspace
        self.headers = {'Content-Type': 'application/json'}
    
    def create_workspace(self):
        """Create workspace if it doesn't exist"""
        url = f"{self.base_url}/rest/workspaces"
        
        # Check if exists
        response = requests.get(f"{url}/{self.workspace}.json", auth=self.auth)
        if response.status_code == 200:
            print(f"✓ Workspace '{self.workspace}' already exists")
            return True
        
        # Create workspace
        data = {
            "workspace": {
                "name": self.workspace
            }
        }
        
        response = requests.post(url, json=data, auth=self.auth, headers=self.headers)
        
        if response.status_code in [200, 201]:
            print(f"✓ Created workspace: {self.workspace}")
            return True
        else:
            print(f"✗ Failed to create workspace: {response.status_code}")
            print(response.text)
            return False
    
    def create_coverage_store(self, store_name, data_dir):
        """Create ImageMosaic coverage store"""
        url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores"
        
        # Check if exists
        response = requests.get(f"{url}/{store_name}.json", auth=self.auth)
        if response.status_code == 200:
            print(f"⊙ Coverage store '{store_name}' already exists")
            return True
        
        # Create coverage store
        data = {
            "coverageStore": {
                "name": store_name,
                "type": "ImageMosaic",
                "enabled": True,
                "workspace": {
                    "name": self.workspace
                },
                "url": f"file://{data_dir}"
            }
        }
        
        response = requests.post(url, json=data, auth=self.auth, headers=self.headers)
        
        if response.status_code in [200, 201]:
            print(f"✓ Created coverage store: {store_name}")
            return True
        else:
            print(f"✗ Failed to create coverage store: {response.status_code}")
            print(response.text)
            return False
    
    def create_coverage_layer(self, store_name, layer_name, title=None, abstract=None):
        """Create coverage layer with proper initialization"""
        url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{store_name}/coverages"
        
        # Check if exists
        response = requests.get(f"{url}/{layer_name}.json", auth=self.auth)
        if response.status_code == 200:
            print(f"⊙ Layer '{layer_name}' already exists")
            return True
        
        # Create coverage layer with minimal configuration
        # Let GeoServer auto-configure from the mosaic
        data = {
            "coverage": {
                "name": layer_name,
                "title": title or layer_name,
                "abstract": abstract or f"Time-enabled mosaic layer for {layer_name}",
                "enabled": True
            }
        }
        
        response = requests.post(url, json=data, auth=self.auth, headers=self.headers)
        
        if response.status_code in [200, 201]:
            print(f"✓ Created layer: {layer_name}")
            return True
        else:
            print(f"✗ Failed to create layer: {response.status_code}")
            print(response.text)
            return False
    
    def enable_time_dimension(self, layer_name, presentation="LIST", default_value_strategy="MAXIMUM", nearest_match=False):
        """
        Enable and configure time dimension for a layer using the reliable method
        
        Args:
            layer_name: Name of the layer
            presentation: How to present time values - "LIST", "DISCRETE_INTERVAL", "CONTINUOUS_INTERVAL"
            default_value_strategy: Default time value strategy
                - "MINIMUM" = Use the smallest domain value
                - "MAXIMUM" = Use the biggest domain value
                - "NEAREST" = Use the domain value nearest to the reference value
                - "FIXED" = Use the reference value
            nearest_match: Enable nearest match for time queries (default: False for exact matching)
        """
        print(f"  Configuring time dimension...")
        
        # Get the layer configuration to find the resource URL
        layer_url = f"{self.base_url}/rest/layers/{self.workspace}:{layer_name}.json"
        response = requests.get(layer_url, auth=self.auth)
        
        if response.status_code != 200:
            print(f"✗ Failed to get layer config: {response.status_code}")
            return False
        
        layer_data = response.json()
        
        # Get the resource href
        resource_href = layer_data['layer']['resource']['href']
        
        # Get coverage configuration from the resource URL
        response = requests.get(resource_href, auth=self.auth)
        if response.status_code != 200:
            print(f"✗ Failed to get coverage config: {response.status_code}")
            return False
        
        coverage_data = response.json()
        
        # Ensure metadata structure exists
        if 'metadata' not in coverage_data['coverage']:
            coverage_data['coverage']['metadata'] = {'entry': []}
        
        metadata = coverage_data['coverage']['metadata']['entry']
        if not isinstance(metadata, list):
            metadata = []
        
        # Remove existing time entry if present
        metadata = [e for e in metadata if not (isinstance(e, dict) and e.get('@key') == 'time')]
        
        # Build time dimension configuration
        time_dimension_config = {
            "enabled": True,
            "attribute": "ingestion",  # Must match TimeAttribute in indexer.properties
            "presentation": presentation,
            "units": "ISO8601",
            "defaultValue": {
                "strategy": default_value_strategy
            },
            "nearestMatchEnabled": nearest_match
        }
        
        # Add time configuration
        time_config = {
            "@key": "time",
            "dimensionInfo": time_dimension_config
        }
        
        metadata.append(time_config)
        coverage_data['coverage']['metadata']['entry'] = metadata
        
        # Update the coverage
        response = requests.put(resource_href, json=coverage_data, auth=self.auth, headers=self.headers)
        
        if response.status_code in [200, 201]:
            print(f"✓ Enabled time dimension for: {layer_name}")
            print(f"  Presentation: {presentation}, Default: {default_value_strategy}")
            print(f"  Nearest match: {'enabled' if nearest_match else 'disabled (exact dates only)'}")
            print(f"  Attribute: ingestion")
            
            # Verify in GetCapabilities
            cap_url = f"{self.base_url}/{self.workspace}/wms?service=WMS&version=1.3.0&request=GetCapabilities"
            cap_response = requests.get(cap_url, auth=self.auth)
            
            if f'<Dimension name="time"' in cap_response.text:
                print(f"✓ Time dimension verified in GetCapabilities")
            else:
                print(f"⚠ Time dimension configuration saved but not yet visible in GetCapabilities")
                print(f"  This may require a GeoServer reload or a few moments to propagate")
            
            return True
        else:
            print(f"✗ Failed to enable time dimension: {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return False
    
    def setup_time_enabled_mosaic(self, store_name, layer_name, data_dir, title=None, abstract=None, workspace=None):
        """Complete setup: create store and layer with time enabled
        
        Args:
            workspace: Optional workspace override (uses self.workspace if not provided)
        """
        # Use provided workspace or fall back to instance workspace
        target_workspace = workspace or self.workspace
        original_workspace = self.workspace
        
        if workspace:
            self.workspace = workspace
        
        print(f"\n{'='*80}")
        print(f"Setting up time-enabled mosaic: {layer_name}")
        print(f"Workspace: {self.workspace}")
        print(f"Data directory: {data_dir}")
        print(f"{'='*80}\n")
        
        # Step 1: Create workspace
        if not self.create_workspace():
            self.workspace = original_workspace
            return False
        
        # Step 2: Create coverage store
        if not self.create_coverage_store(store_name, data_dir):
            self.workspace = original_workspace
            return False
        
        # Step 3: Create coverage layer
        if not self.create_coverage_layer(store_name, layer_name, title, abstract):
            self.workspace = original_workspace
            return False
        
        # Step 4: Enable time dimension
        if not self.enable_time_dimension(layer_name):
            self.workspace = original_workspace
            return False
        
        print(f"\n✓ Successfully set up time-enabled mosaic: {self.workspace}:{layer_name}")
        print(f"   Access at: {self.base_url}/wms?service=WMS&version=1.1.0&request=GetCapabilities")
        
        # Restore original workspace
        self.workspace = original_workspace
        return True


def main():
    """Example usage"""
    
    # Import settings
    import sys
    import os
    
    # Add the project root to path
    project_root = '/opt/geospatial_backend'
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from app.config.settings import get_settings
    
    settings = get_settings()
    
    # Configuration from settings
    GEOSERVER_URL = settings.geoserver_local_url
    USERNAME = settings.GEOSERVER_ADMIN_USER
    PASSWORD = settings.GEOSERVER_ADMIN_PASSWORD
    WORKSPACE = "era5_ws"  # New workspace for ERA5 data
    DATA_BASE_DIR = settings.DATA_DIR.rstrip('/')
    
    print(f"Using GeoServer: {GEOSERVER_URL}")
    print(f"Data directory: {DATA_BASE_DIR}")
    print(f"Workspace: {WORKSPACE}")
    
    # Initialize manager
    manager = GeoServerMosaicManager(GEOSERVER_URL, USERNAME, PASSWORD, WORKSPACE)
    
    # Define mosaics to create
    mosaics = [
        # ERA5 Temperature layers (era5_ws workspace)
        {
            "store_name": "temp_max",
            "layer_name": "temp_max",
            "data_dir": f"{DATA_BASE_DIR}/temp_max",
            "title": "Maximum Temperature (ERA5 Land)",
            "abstract": "Daily maximum 2m temperature from ERA5 Land (9km resolution)",
            "workspace": "era5_ws"
        },
        {
            "store_name": "temp_min",
            "layer_name": "temp_min",
            "data_dir": f"{DATA_BASE_DIR}/temp_min",
            "title": "Minimum Temperature (ERA5 Land)",
            "abstract": "Daily minimum 2m temperature from ERA5 Land (9km resolution)",
            "workspace": "era5_ws"
        },
        {
            "store_name": "temp_mean",
            "layer_name": "temp_mean",
            "data_dir": f"{DATA_BASE_DIR}/temp",
            "title": "Mean Temperature (ERA5 Land)",
            "abstract": "Daily mean 2m temperature from ERA5 Land (9km resolution)",
            "workspace": "era5_ws"
        },
        # CHIRPS Precipitation layer (precipitation_ws workspace)
        {
            "store_name": "chirps",
            "layer_name": "chirps",
            "data_dir": f"{DATA_BASE_DIR}/chirps",
            "title": "CHIRPS Precipitation",
            "abstract": "Daily precipitation from CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data)",
            "workspace": "precipitation_ws"
        },
        # MERGE Precipitation layer (precipitation_ws workspace)
        {
            "store_name": "merge",
            "layer_name": "merge",
            "data_dir": f"{DATA_BASE_DIR}/merge",
            "title": "MERGE Precipitation",
            "abstract": "Daily precipitation from MERGE (Merged Satellite and Gauge Precipitation)",
            "workspace": "precipitation_ws"
        }
    ]
    
    # Create all mosaics
    success_count = 0
    for mosaic in mosaics:
        # Check if directory exists and has files
        data_path = Path(mosaic["data_dir"])
        if not data_path.exists():
            print(f"⊘ Skipping {mosaic['layer_name']}: directory doesn't exist")
            continue
        
        tif_files = list(data_path.glob("*.tif"))
        if not tif_files:
            print(f"⊘ Skipping {mosaic['layer_name']}: no TIF files found")
            continue
        
        print(f"Found {len(tif_files)} TIF files in {mosaic['layer_name']}")
        
        # Set up the mosaic
        if manager.setup_time_enabled_mosaic(**mosaic):
            success_count += 1
    
    print(f"\n{'='*80}")
    print(f"Summary: Successfully created {success_count}/{len(mosaics)} mosaics")
    print(f"{'='*80}\n")
    
    # Print access URLs
    if success_count > 0:
        print("Access your layers:")
        print(f"  WMS Capabilities: {GEOSERVER_URL}/wms?service=WMS&version=1.3.0&request=GetCapabilities")
        print(f"  Layer preview: {GEOSERVER_URL}/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage")
        print(f"\nExample WMS request (temp_max for 2025-01-01):")
        bbox = f"{settings.min_lon},{settings.min_lat},{settings.max_lon},{settings.max_lat}"
        print(f"  {GEOSERVER_URL}/wms?service=WMS&version=1.3.0&request=GetMap&layers={WORKSPACE}:temp_max&time=2025-01-01&width=800&height=600&crs=EPSG:4326&bbox={bbox}&format=image/png")


if __name__ == "__main__":
    main()