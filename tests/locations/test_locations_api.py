"""
Test script for the /locations/validate API endpoint.

Creates sample XLSX files and tests the validation endpoint.
"""

import pandas as pd
import requests
import json


def create_sample_xlsx(filename, data):
    """Create a sample XLSX file for testing."""
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"✓ Created {filename}")


def test_validate_endpoint(filename):
    """Test the /locations/validate endpoint."""
    print(f"\n{'=' * 80}")
    print(f"Testing: {filename}")
    print('=' * 80)

    url = "http://localhost:8000/locations/validate"

    with open(filename, 'rb') as f:
        files = {'file': (filename, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = requests.post(url, files=files)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Valid rows: {len(result['valid_rows'])}")
        for row in result['valid_rows']:
            print(f"  - {row['local']}: ({row['latitude']}, {row['longitude']})")

        print(f"\n✗ Invalid rows: {len(result['invalid_rows'])}")
        for row in result['invalid_rows'][:5]:  # Show first 5 invalid rows
            print(f"  - Row {row.get('_row_number', 'N/A')}: {row.get('local', 'N/A')}")
            print(f"    Reason: {row['failure_reason']}")

        if len(result['invalid_rows']) > 5:
            print(f"  ... and {len(result['invalid_rows']) - 5} more invalid rows")
    else:
        print(f"\n❌ Error: {response.text}")


def main():
    """Run all tests."""
    print("Creating test XLSX files...")

    # Test 1: Valid Brazilian cities
    create_sample_xlsx("test_valid_cities.xlsx", [
        {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
        {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729},
        {"local": "Brasília", "latitude": -15.7942, "longitude": -47.8822},
        {"local": "Salvador", "latitude": -12.9714, "longitude": -38.5014},
        {"local": "Fortaleza", "latitude": -3.7172, "longitude": -38.5433},
    ])

    # Test 2: Mixed valid and invalid
    create_sample_xlsx("test_mixed.xlsx", [
        # Valid
        {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
        {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729},

        # Invalid: Outside Brazil
        {"local": "Caracas (Venezuela)", "latitude": 10.4806, "longitude": -66.9036},
        {"local": "Lima (Peru)", "latitude": -12.0464, "longitude": -77.0428},

        # Invalid: Missing data
        {"local": "Missing Coords", "latitude": None, "longitude": None},
        {"local": None, "latitude": -23.5505, "longitude": -46.6333},

        # Invalid: Bad data types
        {"local": "Bad Latitude", "latitude": "not a number", "longitude": -46.6333},
        {"local": "Bad Longitude", "latitude": -23.5505, "longitude": "invalid"},
    ])

    # Test 3: All invalid
    create_sample_xlsx("test_all_invalid.xlsx", [
        {"local": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"local": "London", "latitude": 51.5074, "longitude": -0.1278},
        {"local": "Tokyo", "latitude": 35.6762, "longitude": 139.6503},
    ])

    # Test 4: Case insensitive headers
    create_sample_xlsx("test_case_insensitive.xlsx", [
        {"LOCAL": "Porto Alegre", "LATITUDE": -30.0346, "LONGITUDE": -51.2177},
        {"Local": "Curitiba", "Latitude": -25.4290, "Longitude": -49.2671},
    ])

    print("\nStarting API tests...")
    print("Make sure the FastAPI server is running: uvicorn app.api.main:app --reload")
    print()

    try:
        # Test if API is running
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("❌ API is not responding. Please start the server.")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API at http://localhost:8000")
        print("Please start the server with: uvicorn app.api.main:app --reload")
        return

    # Run tests
    test_validate_endpoint("test_valid_cities.xlsx")
    test_validate_endpoint("test_mixed.xlsx")
    test_validate_endpoint("test_all_invalid.xlsx")
    test_validate_endpoint("test_case_insensitive.xlsx")

    print("\n" + "=" * 80)
    print("All API tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
