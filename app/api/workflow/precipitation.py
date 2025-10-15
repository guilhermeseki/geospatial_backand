from prefect import flow
from app.services.precipitation.local_data import get_precipitation_point
from app.services.fetch_precipitation import fetch_precipitation  # Your data-fetching function

@flow(name="api_precipitation_flow")
async def api_precipitation_flow(lat: float, lon: float, date: str, source: str):
    """Prefect flow to orchestrate precipitation data fetching."""
    return await fetch_precipitation(lat, lon, date, source)  # Delegate to service layer