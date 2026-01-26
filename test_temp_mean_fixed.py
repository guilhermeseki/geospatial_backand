#!/usr/bin/env python3
"""
Test temp_mean API endpoints after fixing the grid consistency issue.
Run this after restarting the FastAPI service.
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_endpoint(name, method, endpoint, data=None):
    """Test an API endpoint and print results."""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"{'='*80}")
    print(f"Endpoint: {method} {endpoint}")

    if data:
        print(f"Request body:")
        print(json.dumps(data, indent=2))

    try:
        if method == "GET":
            response = requests.get(f"{API_BASE}{endpoint}")
        elif method == "POST":
            response = requests.post(f"{API_BASE}{endpoint}", json=data)

        print(f"\nResponse status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✓ SUCCESS")
            print(f"\nResponse preview:")
            print(json.dumps(result, indent=2)[:500])

            # Specific checks for area_triggers
            if "area_triggers" in endpoint:
                total_exc = result.get('total_exceedances', 0)
                if total_exc > 0:
                    print(f"\n✓✓ AREA TRIGGERS WORKING! Found {total_exc} exceedances")
                else:
                    print(f"\n⚠️  No exceedances found (might be expected for this query)")

            return True
        else:
            print(f"✗ FAILED")
            print(f"Error: {response.text[:300]}")
            return False

    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        return False


if __name__ == "__main__":
    print("="*80)
    print("TESTING temp_mean API AFTER GRID FIX")
    print("="*80)

    results = {}

    # Test 1: Status check
    results['status'] = test_endpoint(
        "Status Check",
        "GET",
        "/status"
    )

    # Test 2: History endpoint
    results['history'] = test_endpoint(
        "Temperature History",
        "POST",
        "/temperature/history",
        {
            "source": "temp_mean",
            "lat": -15.8,
            "lon": -47.9,
            "start_date": "2025-01-25",
            "end_date": "2025-01-27"
        }
    )

    # Test 3: Triggers endpoint
    results['triggers'] = test_endpoint(
        "Temperature Triggers",
        "POST",
        "/temperature/triggers",
        {
            "source": "temp_mean",
            "lat": -15.8,
            "lon": -47.9,
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "trigger": 23.0,
            "trigger_type": "above"
        }
    )

    # Test 4: Area Triggers (THE CRITICAL TEST)
    results['area_triggers'] = test_endpoint(
        "Temperature Area Triggers (THE FIX)",
        "POST",
        "/temperature/area_triggers",
        {
            "source": "temp_mean",
            "lat": -15.8,
            "lon": -47.9,
            "radius": 10,
            "start_date": "2025-01-25",
            "end_date": "2025-01-25",
            "trigger": 20.0,
            "trigger_type": "above"
        }
    )

    # Test 5: WMS
    print(f"\n{'='*80}")
    print(f"Testing: WMS GetMap")
    print(f"{'='*80}")
    try:
        response = requests.get(
            f"{API_BASE}/temperature/wms",
            params={
                "service": "WMS",
                "version": "1.1.1",
                "request": "GetMap",
                "layers": "temperature_ws:temp_mean",
                "bbox": "-75,-35,-33.5,6.5",  # Brazil extent
                "width": "416",
                "height": "416",
                "srs": "EPSG:4326",
                "time": "2025-01-25",
                "format": "image/png"
            }
        )
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            print("✓ WMS working")
            results['wms'] = True
        else:
            print(f"✗ WMS failed: {response.status_code}")
            results['wms'] = False
    except Exception as e:
        print(f"✗ WMS exception: {e}")
        results['wms'] = False

    # Test 6: FeatureInfo
    results['featureinfo'] = test_endpoint(
        "Temperature FeatureInfo",
        "POST",
        "/temperature/featureinfo",
        {
            "source": "temp_mean",
            "lat": -15.8,
            "lon": -47.9,
            "date": "2025-01-25"
        }
    )

    # Summary
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test:20s} {status}")

    all_passed = all(results.values())

    print(f"\n{'='*80}")
    if all_passed:
        print("✓✓✓ ALL TESTS PASSED! temp_mean is fully working!")
    else:
        print("⚠️  Some tests failed. Check output above for details.")
    print(f"{'='*80}")
