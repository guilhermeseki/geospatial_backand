from fastapi.testclient import TestClient
from app.api.main import app
import pytest

client = TestClient(app)

# Test data
TEST_DATA = {
    "lat": 40.71,
    "lon": -74.01,
    "date": "2023-01-01",
    "source": "chirps_final",
    "width": 800,
    "height": 600
}

def test_map_endpoint():
    response = client.post("/map", json={
        "lat": 40.71,
        "lon": -74.01,
        "date": "2023-01-01",
        "source": "chirps_final",
        "width": 800,
        "height": 600
    })
    assert response.status_code == 200

def test_precipitation_map_endpoint_success():
    """Test successful map generation"""
    response = client.post("/map/precipitation", json=TEST_DATA)
    
    # Basic response validation
    assert response.status_code == 200
    assert "url" in response.json()
    assert "metadata" in response.json()
    
    # Validate URL structure
    url = response.json()["url"]
    assert "http://localhost:8585/geoserver/wms?" in url
    assert "layers=precipitation_ws:chirps_final_mosaic" in url
    assert "time=2023-01-01" in url

def test_missing_required_field():
    """Test missing required field"""
    invalid_data = TEST_DATA.copy()
    del invalid_data["lat"]
    
    response = client.post("/map/precipitation", json=invalid_data)
    assert response.status_code == 422  # FastAPI validation error
    assert "detail" in response.json()

def test_invalid_date_format():
    """Test invalid date format"""
    invalid_data = TEST_DATA.copy()
    invalid_data["date"] = "2023/01/01"  # Wrong format
    
    response = client.post("/map/precipitation", json=invalid_data)
    assert response.status_code == 422

@pytest.mark.parametrize("source", ["invalid_source", "missing_source", ""])
def test_invalid_data_source(source):
    """Test invalid data sources"""
    invalid_data = TEST_DATA.copy()
    invalid_data["source"] = source
    
    response = client.post("/map/precipitation", json=invalid_data)
    assert response.status_code in [400, 422]  # 400 if your code checks sources