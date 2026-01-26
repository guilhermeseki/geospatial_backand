"""
Simple test for the locations endpoint.
Waits for API to be ready before testing.
"""

import pandas as pd
import requests
import time
import sys


def wait_for_api(max_wait=60):
    """Wait for API to be ready."""
    print("Waiting for API to be ready...")
    start = time.time()

    while time.time() - start < max_wait:
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ API is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(".", end="", flush=True)
        time.sleep(2)

    print("\n❌ API did not respond within", max_wait, "seconds")
    return False


def test_locations_endpoint():
    """Test the /locations/validate endpoint."""
    print("\nTesting /locations/validate endpoint...")

    # Create a simple test file
    data = [
        {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
        {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729},
        {"local": "Caracas", "latitude": 10.4806, "longitude": -66.9036},  # Outside Brazil
    ]

    df = pd.DataFrame(data)

    # Save to Excel
    filename = "test_simple.xlsx"
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"Created {filename}")

    # Test the endpoint
    url = "http://localhost:8000/locations/validate"

    try:
        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(url, files=files, timeout=10)

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"Valid rows: {len(result['valid_rows'])}")
            print(f"Invalid rows: {len(result['invalid_rows'])}")

            print("\nValid locations:")
            for row in result['valid_rows']:
                print(f"  - {row['local']}: ({row['latitude']}, {row['longitude']})")

            print("\nInvalid locations:")
            for row in result['invalid_rows']:
                print(f"  - {row.get('local')}: {row['failure_reason']}")

            return True
        elif response.status_code == 404:
            print("\n❌ Endpoint not found!")
            print("The /locations endpoint may not be loaded yet.")
            print("Try restarting the API with: pkill -f 'uvicorn main:app' && python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000")
            return False
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return False

    except requests.exceptions.Timeout:
        print("\n❌ Request timed out")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    if wait_for_api():
        success = test_locations_endpoint()
        sys.exit(0 if success else 1)
    else:
        print("\nPlease start the API with:")
        print("  cd /opt/geospatial_backend")
        print("  python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)
