import requests
import json
import time

# --- API Request Details ---
BASE_URL = "https://api.seki-tech.com/map"  # Change to your server URL
ENDPOINT = "/precipitation/triggers"
URL = f"{BASE_URL}{ENDPOINT}"

HEADERS = {"Content-Type": "application/json"}


PAYLOAD = {
    "source": "chirps",
    "start_date": "2015-01-01",
    "end_date": "2025-07-31",
    "lat": 4.784,
    "lon": -62.402,
    "trigger": 70.0  # Precipitation threshold in mm/day
}

print(f"Sending POST request to: {URL}")
print(f"Requesting triggers for: lat={PAYLOAD['lat']}, lon={PAYLOAD['lon']}")
#rint(f"Time Range: {PAYLOAD['start_date']} to {PAYLOAD['end_date']}")
print(f"Trigger threshold: {PAYLOAD['trigger']} mm/day")

try:
    start_time = time.perf_counter()

    response = requests.post(
        URL,
        headers=HEADERS,
        data=json.dumps(PAYLOAD),
        timeout=60
    )

    elapsed_time = time.perf_counter() - start_time

    print("\n--- Response Metrics ---")
    print(f"Status Code: {response.status_code}")
    print(f"Total Response Time (Latency): {elapsed_time:.4f} seconds")

    if response.status_code == 200:
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response.")
            print(f"Response Text Snippet: {response.text[:200]}...")
    else:
        print(f"API Request Failed. Response body:\n{response.text}")

except requests.exceptions.Timeout:
    print("\n--- ERROR ---")
    print("The request timed out after 60 seconds.")
except requests.exceptions.RequestException as e:
    print("\n--- ERROR ---")
    print(f"An error occurred during the request: {e}")
