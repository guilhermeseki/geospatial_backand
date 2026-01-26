#!/usr/bin/env python3
"""
Test script for batch point analysis endpoint.

Creates a small test CSV file and sends it to the batch analysis endpoint.
"""
import requests
import pandas as pd
from io import BytesIO

# API endpoint
BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/batch_analysis/points"

# Create test data
test_data = {
    "local": ["Brasília", "São Paulo", "Rio de Janeiro"],
    "latitude": [-15.8, -23.5, -22.9],
    "longitude": [-47.9, -46.6, -43.2]
}

df = pd.DataFrame(test_data)

# Save to CSV in memory
csv_buffer = BytesIO()
df.to_csv(csv_buffer, index=False, encoding='utf-8')
csv_buffer.seek(0)

# Prepare form data
files = {
    'file': ('test_locations.csv', csv_buffer, 'text/csv')
}

data = {
    'variable_type': 'precipitation',
    'source': 'chirps',
    'threshold': 50.0,
    'start_date': '2024-01-01',
    'end_date': '2024-12-31',
    'consecutive_days': 1
}

print("=" * 80)
print("Testing Batch Point Analysis Endpoint")
print("=" * 80)
print(f"\nEndpoint: {ENDPOINT}")
print(f"\nTest locations:")
print(df.to_string(index=False))
print(f"\nParameters:")
for key, value in data.items():
    print(f"  {key}: {value}")
print("\n" + "=" * 80)

# Send request
print("\nSending request...")
try:
    response = requests.post(ENDPOINT, files=files, data=data, timeout=60)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✅ Success!")

        # Save response to file
        output_file = "test_locations_analise.csv"
        with open(output_file, 'wb') as f:
            f.write(response.content)

        print(f"\nOutput saved to: {output_file}")

        # Display results
        df_result = pd.read_csv(BytesIO(response.content))
        print("\nResults:")
        print(df_result.to_string(index=False))

    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ Error: Could not connect to API. Is the server running?")
    print(f"   Start server with: uvicorn app.api.main:app --host 0.0.0.0 --port 8000")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
