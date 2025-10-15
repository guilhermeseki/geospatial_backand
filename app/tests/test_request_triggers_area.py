import requests
import json
import time

# --- API Request Details ---
BASE_URL = "https://api.seki-tech.com/map"  # Change to your server URL
ENDPOINT = "/precipitation/area_triggers"
URL = f"{BASE_URL}{ENDPOINT}"

HEADERS = {"Content-Type": "application/json"}

# --- BODY PAYLOAD (UPDATED) ---
RADIUS_KM = 150.0  # Radius in kilometers

PAYLOAD = {
    "source": "chirps",
    "start_date": "2015-01-01",
    "end_date": "2025-07-31",
    "lat": -2.5,
    "lon": -69.0,
    "trigger": 60.0,  # Precipitation threshold in mm/day
    "radius": RADIUS_KM # <-- RADIUS IS NOW PART OF THE JSON BODY
}

# --- Build the final URL (no query parameters needed) ---
FINAL_URL = URL

print(f"Sending POST request to: {FINAL_URL}")
print(f"Requesting triggers for area around: lat={PAYLOAD['lat']}, lon={PAYLOAD['lon']}")
print(f"Radius: {PAYLOAD['radius']} km")
print(f"Time Range: {PAYLOAD['start_date']} to {PAYLOAD['end_date']}")
print(f"Trigger threshold: {PAYLOAD['trigger']} mm/day")
print("-" * 30)

try:
    start_time = time.perf_counter()

    response = requests.post(
        FINAL_URL,
        headers=HEADERS,
        data=json.dumps(PAYLOAD),
        timeout=120  # Increased timeout for complex area calculations
    )

    elapsed_time = time.perf_counter() - start_time

    print("\n--- Response Metrics ---")
    print(f"Status Code: {response.status_code}")
    print(f"Total Response Time (Latency): {elapsed_time:.4f} seconds")

    if response.status_code == 200:
        try:
            data = response.json()

            # Print high-level summary
            total_exceedances = data.get('total_exceedances', 'N/A')
            print(f"Total Exceedances Found: {total_exceedances}")

            # Print only the first 5 events for brevity
            exceedances_list = data.get('exceedances_list', [])
            if exceedances_list:
                print(f"First 5 Exceedances (out of {len(exceedances_list)} total):")
                # Using max_items=5 for printing large lists
                print(json.dumps(exceedances_list[:5], indent=2))
            elif total_exceedances == 0:
                print("No exceedances found in the specified area and time range.")
            
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response.")
            print(f"Response Text Snippet: {response.text[:200]}...")
    else:
        print(f"API Request Failed. Response body:\n{response.text}")

except requests.exceptions.Timeout:
    print("\n--- ERROR ---")
    print(f"The request timed out after 120 seconds. Area queries can be slow.")
except requests.exceptions.RequestException as e:
    print("\n--- ERROR ---")
    print(f"An error occurred during the request: {e}")