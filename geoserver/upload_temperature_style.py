"""
Upload and apply temperature style to GeoServer layers
"""
import requests
from requests.auth import HTTPBasicAuth
import sys
from pathlib import Path

sys.path.insert(0, '/opt/geospatial_backend')
from app.config.settings import get_settings

settings = get_settings()

GEOSERVER_URL = settings.geoserver_local_url
USERNAME = settings.GEOSERVER_ADMIN_USER
PASSWORD = settings.GEOSERVER_ADMIN_PASSWORD

auth = HTTPBasicAuth(USERNAME, PASSWORD)
headers_xml = {'Content-Type': 'application/vnd.ogc.sld+xml'}
headers_json = {'Content-Type': 'application/json'}


def list_all_styles():
    """List all styles in GeoServer for debugging"""
    print(f"\nListing all styles in GeoServer...")
    url = f"{GEOSERVER_URL}/rest/styles.json"
    response = requests.get(url, auth=auth)
    
    if response.status_code == 200:
        styles = response.json().get('styles', {}).get('style', [])
        print(f"Found {len(styles)} styles:")
        for style in styles:
            print(f"  - {style.get('name')}")
        return True
    else:
        print(f"✗ Failed to list styles: {response.status_code}")
        return False


def upload_style(style_name, sld_file):
    """Upload SLD style to GeoServer"""
    
    print(f"\nUploading style: {style_name}")
    print("="*80)
    
    # Read SLD file first to validate it exists and is readable
    try:
        with open(sld_file, 'r') as f:
            sld_content = f.read()
        print(f"✓ SLD file loaded ({len(sld_content)} bytes)")
    except Exception as e:
        print(f"✗ Failed to read SLD file: {e}")
        return False
    
    # Check if style exists
    check_url = f"{GEOSERVER_URL}/rest/styles/{style_name}.json"
    response = requests.get(check_url, auth=auth)
    
    if response.status_code == 200:
        print(f"⊙ Style '{style_name}' already exists, updating...")
        # Update existing style
        url = f"{GEOSERVER_URL}/rest/styles/{style_name}"
        response = requests.put(url, data=sld_content, auth=auth, headers=headers_xml)
    else:
        print(f"➕ Creating new style '{style_name}'...")
        # Create new style - POST requires name in URL parameter
        url = f"{GEOSERVER_URL}/rest/styles?name={style_name}"
        response = requests.post(url, data=sld_content, auth=auth, headers=headers_xml)
    
    if response.status_code in [200, 201]:
        print(f"✓ Style '{style_name}' uploaded successfully (status: {response.status_code})")
        
        # Verify the style was actually created
        verify_url = f"{GEOSERVER_URL}/rest/styles/{style_name}.json"
        verify_response = requests.get(verify_url, auth=auth)
        if verify_response.status_code == 200:
            print(f"✓ Verified: Style is now available in GeoServer")
            return True
        else:
            print(f"⚠ Warning: Upload succeeded but cannot verify style exists")
            return False
    else:
        print(f"✗ Failed to upload style: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def apply_style_to_layer(workspace, layer_name, style_name):
    """Apply a style to a layer"""
    
    print(f"\nApplying style '{style_name}' to layer '{workspace}:{layer_name}'")
    
    # Get current layer configuration
    layer_url = f"{GEOSERVER_URL}/rest/layers/{workspace}:{layer_name}.json"
    response = requests.get(layer_url, auth=auth)
    
    if response.status_code != 200:
        print(f"✗ Failed to get layer: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    layer_data = response.json()
    
    # Update default style
    layer_data['layer']['defaultStyle'] = {
        'name': style_name,
        'workspace': None  # Global style
    }
    
    # Update the layer
    response = requests.put(layer_url, json=layer_data, auth=auth, headers=headers_json)
    
    if response.status_code in [200, 201]:
        print(f"✓ Style applied to {workspace}:{layer_name}")
        return True
    else:
        print(f"✗ Failed to apply style: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def main():
    """Upload temperature style and apply to layers"""
    
    print(f"GeoServer URL: {GEOSERVER_URL}")
    print(f"Username: {USERNAME}")
    
    # Test connection first
    print("\nTesting GeoServer connection...")
    test_url = f"{GEOSERVER_URL}/rest/about/version.json"
    try:
        response = requests.get(test_url, auth=auth)
        if response.status_code == 200:
            print("✓ Connected to GeoServer successfully")
        else:
            print(f"✗ Connection failed: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Cannot connect to GeoServer: {e}")
        return
    
    # List existing styles before upload
    list_all_styles()
    
    # Path to SLD file
    sld_file = Path("/opt/geospatial_backend/geoserver/temperature_style.sld")
    
    if not sld_file.exists():
        print(f"\n✗ SLD file not found: {sld_file}")
        print(f"Please save the temperature_style.sld file to: {sld_file}")
        return
    
    # Upload the style
    style_name = "temperature_style"
    if not upload_style(style_name, sld_file):
        print("\n✗ Failed to upload style")
        return
    
    # List styles after upload to confirm it's there
    print(f"\n{'='*80}")
    print("Verifying style upload...")
    print(f"{'='*80}")
    list_all_styles()
    
    print(f"\n{'='*80}")
    print("Applying style to temperature layers...")
    print(f"{'='*80}")
    
    # Apply to temperature layers
    layers = [
        ("era5_ws", "temp_max"),
        ("era5_ws", "temp_min"),
        ("era5_ws", "temp_mean"),
    ]
    
    success_count = 0
    for workspace, layer_name in layers:
        if apply_style_to_layer(workspace, layer_name, style_name):
            success_count += 1
    
    print(f"\n{'='*80}")
    print(f"Summary: Applied style to {success_count}/{len(layers)} layers")
    print(f"{'='*80}")
    
    if success_count > 0:
        print("\nYou can now view your styled layers:")
        print(f"  Styles page: {GEOSERVER_URL}/web/?wicket:bookmarkablePage=:org.geoserver.web.data.style.StylePage")
        print(f"  Layer preview: {GEOSERVER_URL}/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage")
        print(f"\nExample WMS request:")
        print(f"  {GEOSERVER_URL}/wms?service=WMS&version=1.3.0&request=GetMap&layers=era5_ws:temp_max&time=2025-01-01&width=800&height=600&crs=EPSG:4326&bbox=-94,-53,-34.5,25.05&format=image/png&styles={style_name}")


if __name__ == "__main__":
    main()