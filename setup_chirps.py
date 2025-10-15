#!/usr/bin/env python3
"""
GeoServer CHIRPS Mosaic Configuration Script
Automates the complete setup from coverage store to time-enabled layer
Includes deletion of existing store, layer, and data files first
"""

import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
import sys
import os
import glob
import shutil

# Configuration
GEOSERVER_URL = "https://gs.seki-tech.com/geoserver"
USERNAME = "admin"
PASSWORD = "geoserver"
WORKSPACE = "precipitation_ws"
STORE_NAME = "chirps"
COVERAGE_NAME = "chirps"
DATA_PATH = "/usr/share/geoserver-2.27.2/data_dir/data/chirps"

# Authentication
auth = HTTPBasicAuth(USERNAME, PASSWORD)
headers = {"Content-type": "text/xml"}

def check_response(response, operation):
    """Check HTTP response and print status"""
    if response.status_code in [200, 201]:
        print(f"✅ {operation} - Success")
        return True
    else:
        print(f"❌ {operation} - Failed (HTTP {response.status_code})")
        print(f"Response: {response.text}")
        return False

def delete_data_files():
    """Step 0: Delete existing data files and index files"""
    print("🗑️  Cleaning up data directory files...")
    
    try:
        if os.path.exists(DATA_PATH):
            # List of files to delete (mosaic index files)
            files_to_delete = [
                "chirps.dbf", "chirps.fix", "chirps.prj", "chirps.shp", "chirps.shx",
                "datastore.properties",
                #"*.xml", "*.properties", "*.shp", "*.dbf", "*.shx", "*.prj", "*.fix"
            ]
            
            deleted_count = 0
            # Delete specific mosaic index files
            for pattern in files_to_delete:
                for file_path in glob.glob(os.path.join(DATA_PATH, pattern)):
                    try:
                        os.remove(file_path)
                        print(f"   Deleted: {os.path.basename(file_path)}")
                        deleted_count += 1
                    except OSError as e:
                        print(f"   Warning: Could not delete {file_path}: {e}")
            
            # Also check for and delete any .sample files
            sample_files = glob.glob(os.path.join(DATA_PATH, "*.sample"))
            for file_path in sample_files:
                try:
                    os.remove(file_path)
                    print(f"   Deleted: {os.path.basename(file_path)}")
                    deleted_count += 1
                except OSError as e:
                    print(f"   Warning: Could not delete {file_path}: {e}")
            
            if deleted_count > 0:
                print(f"✅ Deleted {deleted_count} index files")
            else:
                print("✅ No index files found to delete")
            
            # Check if directory is empty (except GeoTIFF files)
            remaining_files = [f for f in os.listdir(DATA_PATH) 
                             if not f.endswith(('.tif', '.tiff', '.vrt', '.nc'))]
            if not remaining_files:
                print("✅ Data directory cleaned up successfully")
            else:
                print(f"⚠️  Data directory still contains: {remaining_files}")
            
            return True
        else:
            print("❌ Data directory does not exist: " + DATA_PATH)
            return False
            
    except Exception as e:
        print(f"❌ Error cleaning data directory: {e}")
        return False

def delete_existing_store():
    """Step 1: Delete existing coverage store if it exists"""
    print("🔍 Checking for existing coverage store...")
    
    # Check if store exists
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{STORE_NAME}.xml"
    response = requests.get(url, auth=auth)
    
    if response.status_code == 200:
        print("📦 Existing store found, deleting...")
        # Delete with recurse=true to remove associated layers
        delete_url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{STORE_NAME}?recurse=true"
        response = requests.delete(delete_url, auth=auth)
        
        if response.status_code == 200:
            print("✅ Existing store deleted successfully")
            return True
        else:
            print("❌ Failed to delete existing store")
            return False
    else:
        print("✅ No existing store found, proceeding...")
        return True

def delete_existing_layer():
    """Step 2: Delete existing layer if it exists"""
    print("🔍 Checking for existing layer...")
    
    # Check if layer exists
    url = f"{GEOSERVER_URL}/rest/layers/{WORKSPACE}:{COVERAGE_NAME}.xml"
    response = requests.get(url, auth=auth)
    
    if response.status_code == 200:
        print("📄 Existing layer found, deleting...")
        delete_url = f"{GEOSERVER_URL}/rest/layers/{WORKSPACE}:{COVERAGE_NAME}"
        response = requests.delete(delete_url, auth=auth)
        
        if response.status_code == 200:
            print("✅ Existing layer deleted successfully")
            return True
        else:
            print("❌ Failed to delete existing layer")
            return False
    else:
        print("✅ No existing layer found, proceeding...")
        return True

def create_coverage_store():
    """Step 3: Create the coverage store"""
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores"
    
    data = f"""<coverageStore>
        <name>{STORE_NAME}</name>
        <workspace>{WORKSPACE}</workspace>
        <type>ImageMosaic</type>
        <url>file:{DATA_PATH}</url>
    </coverageStore>"""
    
    response = requests.post(url, auth=auth, headers=headers, data=data)
    return check_response(response, "Create coverage store")

def create_coverage():
    """Step 4: Create the coverage"""
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{STORE_NAME}/coverages"
    
    data = f"""<coverage>
        <name>{COVERAGE_NAME}</name>
        <title>CHIRPS Precipitation</title>
        <description>Climate Hazards Group InfraRed Precipitation with Station data</description>
        <enabled>true</enabled>
    </coverage>"""
    
    response = requests.post(url, auth=auth, headers=headers, data=data)
    return check_response(response, "Create coverage")

def enable_time_dimension():
    """Step 5: Enable time dimension"""
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{STORE_NAME}/coverages/{COVERAGE_NAME}"
    
    data = """<coverage>
        <enabled>true</enabled>
        <metadata>
            <entry key="time">
                <dimensionInfo>
                    <enabled>true</enabled>
                    <presentation>LIST</presentation>
                    <resolution>1</resolution>
                    <units>days</units>
                    <defaultValue>
                        <strategy>MAXIMUM</strategy>
                    </defaultValue>
                </dimensionInfo>
            </entry>
        </metadata>
    </coverage>"""
    
    response = requests.put(url, auth=auth, headers=headers, data=data)
    return check_response(response, "Enable time dimension")

def publish_layer():
    """Step 6: Publish the layer"""
    url = f"{GEOSERVER_URL}/rest/layers/{WORKSPACE}:{COVERAGE_NAME}"
    
    data = f"""<layer>
        <name>{COVERAGE_NAME}</name>
        <path>/</path>
        <type>RASTER</type>
        <defaultStyle>
            <name>raster</name>
        </defaultStyle>
        <resource class="coverage">
            <name>{WORKSPACE}:{COVERAGE_NAME}</name>
        </resource>
        <enabled>true</enabled>
        <advertised>true</advertised>
    </layer>"""
    
    # First try PUT (update existing), if fails try POST (create new)
    response = requests.put(url, auth=auth, headers=headers, data=data)
    
    if response.status_code == 404:
        # Layer doesn't exist, try POST to create it
        url = f"{GEOSERVER_URL}/rest/layers"
        response = requests.post(url, auth=auth, headers=headers, data=data)
    
    return check_response(response, "Publish layer")

def reload_geoserver():
    """Step 7: Reload GeoServer configuration"""
    url = f"{GEOSERVER_URL}/rest/reload"
    response = requests.post(url, auth=auth)
    return check_response(response, "Reload GeoServer")

def verify_setup():
    """Step 8: Verify the setup"""
    print("\n🔍 Verifying setup...")
    
    # Check coverage store
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{STORE_NAME}.xml"
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        print("✅ Coverage store exists")
    else:
        print("❌ Coverage store not found")
        return False
    
    # Check coverage
    url = f"{GEOSERVER_URL}/rest/workspaces/{WORKSPACE}/coveragestores/{STORE_NAME}/coverages/{COVERAGE_NAME}.xml"
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        # Check if time dimension is enabled
        root = ET.fromstring(response.content)
        time_enabled = root.find('.//dimensionInfo/enabled')
        if time_enabled is not None and time_enabled.text == 'true':
            print("✅ Coverage exists with time dimension enabled")
        else:
            print("❌ Time dimension not properly configured")
            return False
    else:
        print("❌ Coverage not found")
        return False
    
    # Check layer
    url = f"{GEOSERVER_URL}/rest/layers/{WORKSPACE}:{COVERAGE_NAME}.xml"
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        print("✅ Layer is published")
    else:
        print("❌ Layer not found")
        return False
    
    # Check if mosaic index files were regenerated
    if os.path.exists(DATA_PATH):
        index_files = [f for f in os.listdir(DATA_PATH) 
                      if f.startswith('chirps.') or f == 'indexer.properties']
        if index_files:
            print("✅ Mosaic index files regenerated")
        else:
            print("⚠️  No mosaic index files found (may need manual configuration)")
    
    # Test WMS request
    wms_url = f"{GEOSERVER_URL}/wms?service=WMS&version=1.3.0&request=GetMap&layers={WORKSPACE}:{COVERAGE_NAME}&width=100&height=100&srs=EPSG:4326&bbox=-94.05,-53.0,-34.5,25.1&format=image/png"
    response = requests.get(wms_url)
    if response.status_code == 200:
        print("✅ WMS request successful")
    else:
        print("⚠️  WMS request failed (layer might need time parameter)")
    
    return True

def main():
    """Main execution function"""
    print("🚀 Starting GeoServer CHIRPS configuration...\n")
    
    # Execute steps in order
    steps = [
        ("Deleting data directory index files", delete_data_files),
        ("Deleting existing coverage store", delete_existing_store),
        ("Deleting existing layer", delete_existing_layer),
        ("Creating coverage store", create_coverage_store),
        ("Creating coverage", create_coverage),
        ("Enabling time dimension", enable_time_dimension),
        ("Publishing layer", publish_layer),
        ("Reloading GeoServer", reload_geoserver),
        ("Verifying setup", verify_setup)
    ]
    
    for step_name, step_function in steps:
        print(f"\n📋 {step_name}...")
        if not step_function():
            print(f"\n❌ Script failed at: {step_name}")
            # Ask user if they want to continue
            continue_anyway = input("Continue anyway? (y/n): ")
            if continue_anyway.lower() != 'y':
                sys.exit(1)
    
    print("\n🎉 All steps completed successfully!")
    print(f"\n🌐 Your layer is available at: {GEOSERVER_URL}/wms")
    print(f"📊 Layer name: {WORKSPACE}:{COVERAGE_NAME}")
    print(f"⏰ Time dimension: Enabled with LIST presentation")

if __name__ == "__main__":
    main()
