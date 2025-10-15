#app/api/routers/health.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from app.services.geoserver import GeoServerService
from app.state import app_state
import logging
from typing import Dict, Any

router = APIRouter(tags=["Health Checks"])
logger = logging.getLogger(__name__)

def get_geoserver():
    return GeoServerService()

@router.get("/health/geoserver", 
           summary="GeoServer Health Check",
           response_description="GeoServer connection status")

async def geoserver_health(geoserver: GeoServerService = Depends(get_geoserver)) -> Dict[str, Any]:
    """
    Check GeoServer connection status with detailed diagnostics.
    
    Returns:
        dict: Health status with connection details and capabilities
    """
    try:
        is_alive = await geoserver.check_geoserver_alive()
        
        # Extended health information
        status_info = {
            "service": "geoserver",
            "status": "online" if is_alive else "offline",
            "url": geoserver.base_url,
            "workspace": geoserver.workspace,
            "ready": app_state.ready,  # From main app state
            "details": {
                "rest_api": f"{geoserver.base_url}/rest/about/version",
                "wms_capabilities": f"{geoserver.base_url}/wms?service=WMS&version=1.3.0&request=GetCapabilities"
            }
        }
        
        if not is_alive:
            logger.warning(f"GeoServer health check failed: {status_info}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=status_info
            )
            
        return status_info
        
    except Exception as e:
        logger.error(f"GeoServer health check error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "service": "geoserver",
                "error": str(e),
                "status": "error"
            }
        )

@router.get("/health/full", include_in_schema=False)
async def full_health_check(geoserver: GeoServerService = Depends(get_geoserver)):
    """
    Comprehensive health check for all subsystems (for internal use)
    """
    checks = {
        "geoserver": await geoserver_health(geoserver),
        "app_status": {
            "ready": app_state.ready,
            "initialization_error": app_state.failure_reason
        },
        "components": {
            "mosaic_config_initialized": app_state.ready
        }
    }
    
    if not all([
        checks["geoserver"]["status"] == "online",
        app_state.ready
    ]):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=checks
        )
    
    return checks

