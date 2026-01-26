#!/usr/bin/env python3
"""
Backfill CHIRPS 2017 data (January 1 - May 3) and rebuild complete yearly NetCDF file.
"""
import sys
sys.path.insert(0, '/opt/geospatial_backend')

from prefect import flow
from datetime import datetime
from app.workflows.data_processing.precipitation_flow import process_chirps_daily_batch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@flow(name="backfill-chirps-2017")
def backfill_2017():
    """Download CHIRPS data for Jan 1 - May 3, 2017"""
    start_date = datetime(2017, 1, 1)
    end_date = datetime(2017, 5, 3)

    logger.info(f"Backfilling CHIRPS 2017: {start_date.date()} to {end_date.date()}")

    process_chirps_daily_batch(
        start_date=start_date,
        end_date=end_date
    )

    logger.info("Backfill complete!")

if __name__ == "__main__":
    backfill_2017()
