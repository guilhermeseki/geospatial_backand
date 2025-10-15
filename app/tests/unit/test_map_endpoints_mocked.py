from unittest.mock import patch
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

@patch("app.services.geoserver.GeoServerService.get_wms_url")
def test_mocked_map_endpoint(mock_wms):
    mock_wms.return_value = "http://mock-server/wms?test=1"
    
    response = client.post("/map/precipitation", json={
        "lat": 40.71,
        "lon": -74.01,
        "date": "2023-01-01",
        "source": "chirps_final",
        "width": 800,
        "height": 600
    })
    
    assert response.status_code == 200
    assert "http://mock-server" in response.json()["url"]