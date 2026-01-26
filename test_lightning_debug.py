#!/usr/bin/env python3
"""Debug failing lightning endpoints"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/lightning"

# Test area triggers with detailed error
print("="*70)
print("Testing: POST /lightning/triggers/area (with debug)")
print("="*70)

area_triggers_payload = {
    "lat": -15.8,
    "lon": -47.9,
    "radius": 50,
    "start_date": "2025-11-01",
    "end_date": "2025-11-30",
    "trigger": 3.0,
    "trigger_type": "above"
}

print(f"Request: POST {BASE_URL}/triggers/area")
print(f"Payload: {json.dumps(area_triggers_payload, indent=2)}\n")

response = requests.post(f"{BASE_URL}/triggers/area", json=area_triggers_payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}\n")

# Test polygon with detailed error
print("="*70)
print("Testing: POST /lightning/polygon (with debug)")
print("="*70)

polygon_payload = {
    "coordinates": [
        [-48.0, -15.7],
        [-47.8, -15.7],
        [-47.8, -15.9],
        [-48.0, -15.9]
    ],
    "source": "glm_fed",
    "start_date": "2025-11-01",
    "end_date": "2025-11-30",
    "statistic": "mean"
}

print(f"Request: POST {BASE_URL}/polygon")
print(f"Payload: {json.dumps(polygon_payload, indent=2)}\n")

response = requests.post(f"{BASE_URL}/polygon", json=polygon_payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}\n")

# Also check what the actual dataset looks like
print("="*70)
print("Checking dataset availability via /status endpoint")
print("="*70)
response = requests.get("http://localhost:8000/status")
status = response.json()
print("Available datasets:")
for key in ['lightning_datasets', 'datasets']:
    if key in status:
        print(f"  {key}: {status[key]}")
