from fastapi import APIRouter, HTTPException
from core.services.geoserver import GeoServerService
from api.schemas.geospatial import MapRequest

router = APIRouter(prefix="/data", tags=["Geospatial Data"])

@router.post("/map")
async def get_map(request: MapRequest):
    try:
        map_url = await GeoServerService().generate_map_url(
            lat=request.lat,
            lon=request.lon,
            source=request.source,
            date=request.date,
            zoom=request.zoom,
            width=request.width,
            height=request.height
        )
        return {"url": map_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))