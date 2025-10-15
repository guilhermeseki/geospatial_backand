import requests
import json
import time

# --- API Request Details ---
BASE_URL = "https://api.seki-tech.com/map"  # Change to your server URL
ENDPOINT = "/precipitation/triggers"
URL = f"{BASE_URL}{ENDPOINT}"

HEADERS = {"Content-Type": "application/json"}

maiores_barragens_10 = {
    "Itaipu": {"lat": -25.40833, "lon": -54.58917},
    "Belo_Monte": {"lat": -3.12640, "lon": -51.77500},
    "Sao_Luiz_do_Tapajos_planejada": {"lat": -4.44789, "lon": -56.24401},
    "Tucurui": {"lat": -3.83167, "lon": -49.64667},
    "Santo_Antonio": {"lat": -8.76389, "lon": -63.90361},
    "Ilha_Solteira": {"lat": -20.38278, "lon": -51.36222},
    "Jirau": {"lat": -9.44611, "lon": -63.00472},
    "Xingo": {"lat": -9.00361, "lon": -37.57972},
    "Paulo_Afonso_IV": {"lat": -9.39910, "lon": -38.22671},
    "Jatoba_projeto": {"lat": -9.18306, "lon": -38.26889},
}

BASE_PAYLOAD = {
    "source": "chirps",
    "start_date": "2015-01-01",
    "end_date": "2025-07-31",
    "trigger": 60.0  # Precipitation threshold in mm/day
}

print(f"Sending POST request to: {URL}")
#print(f"Requesting triggers for: lat={PAYLOAD['lat']}, lon={PAYLOAD['lon']}")
#print(f"Time Range: {PAYLOAD['start_date']} to {PAYLOAD['end_date']}")
#print(f"Trigger threshold: {PAYLOAD['trigger']} mm/day")

for nome, coords in maiores_barragens_10.items():
    print(f"\n===== {nome} =====")

    payload = BASE_PAYLOAD.copy()
    payload.update({"lat": coords["lat"], "lon": coords["lon"]})

    try:
        start_time = time.perf_counter()
        response = requests.post(
            URL,
            headers=HEADERS,
            data=json.dumps(payload),
            timeout=60
        )
        elapsed_time = time.perf_counter() - start_time

        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed_time:.4f} s")

        if response.status_code == 200:
            try:
                data = response.json()

                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print("Error: Could not decode JSON response.")
                print(f"Response Snippet: {response.text[:200]}...")
        else:
            print(f"Request Failed. Response:\n{response.text}")

    except requests.exceptions.Timeout:
        print("--- ERROR --- Request timed out.")
    except requests.exceptions.RequestException as e:
        print(f"--- ERROR --- {e}")
