#!/usr/bin/env python3
"""
Comprehensive test script for all Lightning API endpoints
Tests: /history, /triggers, /triggers/area, /wms, /polygon, /featureinfo
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/lightning"

def print_test_header(test_name):
    print("\n" + "="*70)
    print(f"Testing: {test_name}")
    print("="*70)

def print_response(response, show_full=False):
    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {response.elapsed.total_seconds():.2f}s")
    try:
        data = response.json()
        if show_full:
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            # Show truncated response for large data
            json_str = json.dumps(data, indent=2)
            if len(json_str) > 500:
                print(f"Response (truncated): {json_str[:500]}...")
            else:
                print(f"Response: {json_str}")
    except:
        print(f"Response Text: {response.text[:200]}")
    print()

# Test coordinates - Brasília area
TEST_LAT = -15.8
TEST_LON = -47.9

# Use dates within available range (2025-04-01 to 2025-11-30)
# Using recent dates from the available range
end_date = datetime(2025, 11, 30).date()
start_date = datetime(2025, 11, 1).date()  # 30 days of history

print(f"\nTest Configuration:")
print(f"  Base URL: {BASE_URL}")
print(f"  Test Location: ({TEST_LAT}, {TEST_LON}) - Brasília")
print(f"  Date Range: {start_date} to {end_date}")
print(f"  Current Time: {datetime.now()}")

# ============================================================================
# 1. TEST /history endpoint
# ============================================================================
print_test_header("POST /lightning/history")

history_payload = {
    "lat": TEST_LAT,
    "lon": TEST_LON,
    "start_date": str(start_date),
    "end_date": str(end_date)
}

print(f"Request: POST {BASE_URL}/history")
print(f"Payload: {json.dumps(history_payload, indent=2)}")

response = requests.post(f"{BASE_URL}/history", json=history_payload)
print_response(response)

if response.status_code == 200:
    data = response.json()
    print(f"✅ History endpoint working")
    print(f"   - Returned {len(data.get('history', {}))} dates")
    if data.get('history'):
        sample_dates = list(data['history'].items())[:3]
        print(f"   - Sample data: {sample_dates}")
else:
    print(f"❌ History endpoint failed")

# ============================================================================
# 2. TEST /triggers endpoint (point-based)
# ============================================================================
print_test_header("POST /lightning/triggers")

triggers_payload = {
    "lat": TEST_LAT,
    "lon": TEST_LON,
    "start_date": str(start_date),
    "end_date": str(end_date),
    "trigger": 5.0,  # FED threshold of 5
    "trigger_type": "above"
}

print(f"Request: POST {BASE_URL}/triggers")
print(f"Payload: {json.dumps(triggers_payload, indent=2)}")

response = requests.post(f"{BASE_URL}/triggers", json=triggers_payload)
print_response(response)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Triggers endpoint working")
    print(f"   - Found {data.get('n_exceedances', 0)} exceedances")
    if data.get('exceedances'):
        print(f"   - Sample: {data['exceedances'][:3]}")
else:
    print(f"❌ Triggers endpoint failed")

# ============================================================================
# 3. TEST /triggers/area endpoint (area-based)
# ============================================================================
print_test_header("POST /lightning/triggers/area")

area_triggers_payload = {
    "lat": TEST_LAT,
    "lon": TEST_LON,
    "radius": 50,  # 50 km radius
    "start_date": str(start_date),
    "end_date": str(end_date),
    "trigger": 3.0,  # Lower threshold for area
    "trigger_type": "above"
}

print(f"Request: POST {BASE_URL}/triggers/area")
print(f"Payload: {json.dumps(area_triggers_payload, indent=2)}")

response = requests.post(f"{BASE_URL}/triggers/area", json=area_triggers_payload)
print_response(response)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Area triggers endpoint working")
    print(f"   - Found {data.get('n_trigger_dates', 0)} dates with triggers")
    if data.get('exceedances_by_date'):
        sample_date = list(data['exceedances_by_date'].keys())[0] if data['exceedances_by_date'] else None
        if sample_date:
            n_points = len(data['exceedances_by_date'][sample_date])
            print(f"   - Sample date {sample_date}: {n_points} points exceeded threshold")
else:
    print(f"❌ Area triggers endpoint failed")

# ============================================================================
# 4. TEST /wms endpoint
# ============================================================================
print_test_header("GET /lightning/wms (GetCapabilities)")

wms_params = {
    "service": "WMS",
    "version": "1.1.1",
    "request": "GetCapabilities"
}

print(f"Request: GET {BASE_URL}/wms")
print(f"Params: {wms_params}")

response = requests.get(f"{BASE_URL}/wms", params=wms_params)
print(f"Status Code: {response.status_code}")
print(f"Response Time: {response.elapsed.total_seconds():.2f}s")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Response Length: {len(response.content)} bytes")

if response.status_code == 200 and 'xml' in response.headers.get('content-type', ''):
    print(f"✅ WMS GetCapabilities working")
    if b'glm_fed' in response.content or b'glm_ws' in response.content:
        print(f"   - GLM FED layer found in capabilities")
else:
    print(f"❌ WMS GetCapabilities failed")

# Test GetMap request
print_test_header("GET /lightning/wms (GetMap)")

wms_map_params = {
    "service": "WMS",
    "version": "1.1.1",
    "request": "GetMap",
    "layers": "glm_ws:glm_fed",
    "bbox": "-60,-30,-40,-10",  # Brazil area
    "width": 400,
    "height": 400,
    "srs": "EPSG:4326",
    "format": "image/png",
    "time": str(end_date)
}

print(f"Request: GET {BASE_URL}/wms")
print(f"Params: {json.dumps(wms_map_params, indent=2)}")

response = requests.get(f"{BASE_URL}/wms", params=wms_map_params)
print(f"Status Code: {response.status_code}")
print(f"Response Time: {response.elapsed.total_seconds():.2f}s")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Response Length: {len(response.content)} bytes")

if response.status_code == 200 and 'image/png' in response.headers.get('content-type', ''):
    print(f"✅ WMS GetMap working")
    print(f"   - Returned PNG image ({len(response.content)} bytes)")
else:
    print(f"❌ WMS GetMap failed")
    print(f"   Response text: {response.text[:200]}")

# ============================================================================
# 5. TEST /polygon endpoint
# ============================================================================
print_test_header("POST /lightning/polygon")

# Simple square polygon around Brasília
polygon_payload = {
    "coordinates": [
        [-48.0, -15.7],
        [-47.8, -15.7],
        [-47.8, -15.9],
        [-48.0, -15.9],
        [-48.0, -15.7]
    ],
    "source": "glm_fed",
    "start_date": str(start_date),
    "end_date": str(end_date),
    "statistic": "mean"
}

print(f"Request: POST {BASE_URL}/polygon")
print(f"Payload: {json.dumps(polygon_payload, indent=2)}")

response = requests.post(f"{BASE_URL}/polygon", json=polygon_payload)
print_response(response)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Polygon endpoint working")
    print(f"   - Calculated {data.get('statistic', '')} statistic")
    if data.get('results'):
        print(f"   - Returned {len(data['results'])} dates")
        print(f"   - Sample: {data['results'][:3]}")
else:
    print(f"❌ Polygon endpoint failed")

# ============================================================================
# 6. TEST /featureinfo endpoint
# ============================================================================
print_test_header("POST /lightning/featureinfo")

# Get available dates first
featureinfo_payload = {
    "source": "glm_fed",
    "lat": TEST_LAT,
    "lon": TEST_LON,
    "date": str(end_date)
}

print(f"Request: POST {BASE_URL}/featureinfo")
print(f"Payload: {json.dumps(featureinfo_payload, indent=2)}")

response = requests.post(f"{BASE_URL}/featureinfo", json=featureinfo_payload)
print_response(response)

if response.status_code == 200:
    data = response.json()
    print(f"✅ FeatureInfo endpoint working")
    print(f"   - FED value: {data.get('fed')}")
    if data.get('message'):
        print(f"   - Message: {data.get('message')}")
else:
    print(f"❌ FeatureInfo endpoint failed")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print("""
Endpoints tested:
  1. POST /lightning/history          - Point-based historical FED values
  2. POST /lightning/triggers         - Point-based threshold exceedances
  3. POST /lightning/triggers/area    - Area-based threshold exceedances
  4. GET  /lightning/wms              - GeoServer WMS proxy (GetCapabilities & GetMap)
  5. POST /lightning/polygon          - Polygon-based statistics
  6. POST /lightning/featureinfo      - Single point/date GeoTIFF query
""")

print("\nTest completed at:", datetime.now())
