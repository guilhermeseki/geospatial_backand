#!/usr/bin/env python3
"""
Comprehensive test for batch point analysis endpoint.
Tests multiple variable types and parameters.
"""
import requests
import pandas as pd
from io import BytesIO

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/batch_analysis/points"

# Create test data
test_data = {
    "local": ["Brasília", "São Paulo"],
    "latitude": [-15.8, -23.5],
    "longitude": [-47.9, -46.6]
}

df = pd.DataFrame(test_data)

def test_analysis(variable_type, source, threshold, trigger_type=None, consecutive_days=1):
    """Run a batch analysis test."""
    print("\n" + "=" * 80)
    print(f"Testing: {variable_type.upper()} (source: {source}, threshold: {threshold})")
    if trigger_type:
        print(f"Trigger type: {trigger_type}")
    if consecutive_days > 1:
        print(f"Consecutive days: {consecutive_days}")
    print("=" * 80)

    # Prepare CSV
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_buffer.seek(0)

    files = {'file': ('test_locations.csv', csv_buffer, 'text/csv')}

    data = {
        'variable_type': variable_type,
        'source': source,
        'threshold': threshold,
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'consecutive_days': consecutive_days
    }

    if trigger_type:
        data['trigger_type'] = trigger_type

    try:
        response = requests.post(ENDPOINT, files=files, data=data, timeout=120)

        if response.status_code == 200:
            print("✅ Success!")
            df_result = pd.read_csv(BytesIO(response.content))
            print("\nResults:")
            print(df_result.to_string(index=False))
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

# Test 1: Precipitation with lower threshold
test_analysis('precipitation', 'chirps', 10.0)

# Test 2: Temperature max (heat events)
test_analysis('temp_max', 'temp_max', 35.0)

# Test 3: Temperature min (cold events)
test_analysis('temp_min', 'temp_min', 10.0)

# Test 4: Temperature mean with "above"
test_analysis('temp_mean', 'temp_mean', 25.0, trigger_type='above')

# Test 5: Precipitation with consecutive days
test_analysis('precipitation', 'chirps', 5.0, consecutive_days=3)

print("\n" + "=" * 80)
print("All tests completed!")
print("=" * 80)
