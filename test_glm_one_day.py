#!/usr/bin/env python3
"""Run GLM flow for a single day to test the fix."""

import sys
sys.path.insert(0, '/opt/geospatial_backend')

from datetime import date
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

if __name__ == "__main__":
    # Process just 2025-04-16
    test_date = date(2025, 4, 16)
    print(f"Processing GLM for {test_date}...")

    glm_fed_flow(
        start_date=test_date,
        end_date=test_date
    )
