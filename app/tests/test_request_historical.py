import requests
import json
import time

# --- API Request Details ---
URL = "https://api.seki-tech.com/map/precipitation/history"
HEADERS = {"Content-Type": "application/json"}
PAYLOAD = {
    "source": "merge",
    "start_date": "2015-01-01",
    "end_date": "2025-08-31",
    "lat": -4.5,
    "lon": -69.0
}

# --- Execution and Timing ---
print(f"Sending POST request to: {URL}")
print(f"Requesting data for: lat={PAYLOAD['lat']}, lon={PAYLOAD['lon']}")
print(f"Time Range: {PAYLOAD['start_date']} to {PAYLOAD['end_date']}")

try:
    # 1. Record the start time
    start_time = time.perf_counter()

    # 2. Execute the POST request
    response = requests.post(
        URL,
        headers=HEADERS,
        data=json.dumps(PAYLOAD),
        # You may want to set a timeout to prevent infinite waiting
        timeout=60  
    )
    
    # 3. Record the end time
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    # --- Print Results ---
    print("\n--- Response Metrics ---")
    print(f"Status Code: {response.status_code}")
    print(f"Total Response Time (Latency): {elapsed_time:.4f} seconds")
    
    # Check if the request was successful
    if response.status_code == 200:
        # You can inspect the first few characters of the response to verify the data
        try:
            data = response.json()
            # Assuming the response is a list of time-series points
            print(f"Data Points Received (Length): {len(data)}")
            #print(f"First 5 data points: {data[:5]}")
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response.")
            print(f"Response Text Snippet: {response.text[:200]}...")
    else:
        print(f"API Request Failed. Response body: {response.text}")

except requests.exceptions.Timeout:
    print(f"\n--- ERROR ---")
    print(f"The request timed out after 60 seconds.")
except requests.exceptions.RequestException as e:
    print(f"\n--- ERROR ---")
    print(f"An error occurred during the request: {e}")