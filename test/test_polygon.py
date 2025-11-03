curl -X POST http://localhost:8000/api/precipitation/polygon \
  -H "Content-Type: application/json" \
  -d '{
    "coordinates": [[-47.9,-15.8],[-47.8,-15.8],[-47.8,-15.9],[-47.9,-15.9]],
    "source": "chirps",
    "start_date": "2023-01-01",
    "end_date": "2023-01-31",
    "statistic": "mean"
  }'