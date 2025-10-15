import logging
from prefect import task
from app.services.precipitation.local_data import get_precipitation_point

@task(name="fetch_precipitation_data", retries=2)
async def fetch_precipitation(lat: float, lon: float, date: str, source: str):
    """Task to fetch precipitation data from an external API."""
    logger = logging.getLogger("precipitation")
    logger.info(f"Fetching data for {lat},{lon} on {date} from {source}")
    return await get_precipitation_point(lat, lon, date, source)
