from fastapi import APIRouter
from prefect import flow, task
from api.schemas.precipitation import PrecipitationRequest

router = APIRouter(prefix="/precipitation", tags=["Precipitation Data"])

@router.post("/")
async def get_precipitation(request: PrecipitationRequest):
    logger = get_prefect_logger()
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
    except HTTPException:
        logger.error("API Error occurred", exc_info=True)
        raise
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")