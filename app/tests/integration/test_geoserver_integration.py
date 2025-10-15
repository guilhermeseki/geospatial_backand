import pytest
import os
from pathlib import Path
from app.services.geoserver import GeoServerService

@pytest.fixture
def test_nc_file():
    """Create a test NetCDF file"""
    test_dir = Path("data")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "test_latam_20250601.nc"
    return test_file

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_geoserver_connection():
    """Test actual connection to GeoServer"""
    service = GeoServerService()
    assert await service.check_geoserver_alive() is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_real_file(test_nc_file, mock_geoserver):
    """Test with real file but mocked GeoServer calls"""
    mock_geoserver.data_dir = str(test_nc_file.parent)
    #Path(os.getcwd()).write_text("test content")
    result = await mock_geoserver.ensure_layer_exists("test_data", "2025-06-01")
    assert result is not None