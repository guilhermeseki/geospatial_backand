import logging
from fastapi import APIRouter, HTTPException
from app.api.workflow.precipitation import api_precipitation_flow  # Correct import
from app.api.schemas.precipitation import PrecipitationRequest

router = APIRouter(prefix="/precipitation", tags=["Precipitation Data"])
logger = logging.getLogger(__name__)  # Regular Python logger

@router.post("/")
async def get_precipitation(request: PrecipitationRequest):
    try:
        logger.info(f"API Request Received: {request.dict()}")
        result = await api_precipitation_flow(
            request.lat,
            request.lon,
            request.date,
            request.source
        )
        logger.info("API Request Processed Successfully")
        return result
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))