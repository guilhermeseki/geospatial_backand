from prefect import flow, task
import logging

@task(name="fetch_precipitation_data")
async def fetch_precipitation(lat: float, lon: float, date: str, source: str):
    logger = logging.getLogger("precipitation")
    logger.info(f"Fetching data for {lat},{lon} on {date}")
    return await get_precipitation_point(lat, lon, date, source)

@flow(name="api_precipitation_flow")
async def api_precipitation_flow(lat: float, lon: float, date: str, source: str):
    logger = logging.getLogger("precipitation")
    logger.info("Starting precipitation flow", extra={"params": {"lat": lat, "lon": lon, "date": date}})
    result = await fetch_precipitation(lat, lon, date, source)
    logger.info("Flow completed successfully")
    return result