from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date

result = ndvi_data_flow(
    start_date=date(2024, 9, 1),
    end_date=date(2024, 9, 30),
    sources=['modis'],  # Both sources, 'sentinel2','
    batch_days=10
)