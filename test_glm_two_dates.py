#!/usr/bin/env python3
"""
Test GLM FED optimized flow with exactly 2 dates
"""
from datetime import date
from app.workflows.data_processing.glm_fed_flow_optimized import glm_fed_flow_optimized
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

if __name__ == "__main__":
    # Test with two recent dates (allowing for data lag)
    test_date_1 = date(2025, 11, 20)
    test_date_2 = date(2025, 11, 21)

    print("="*80)
    print("TESTING OPTIMIZED GLM FLOW - TWO DATES")
    print("="*80)
    print(f"Date 1: {test_date_1}")
    print(f"Date 2: {test_date_2}")
    print(f"Optimizations enabled:")
    print(f"  - Parallel downloads (8 workers)")
    print(f"  - Progress tracking")
    print(f"  - Checkpointing")
    print("="*80)
    print()

    result = glm_fed_flow_optimized(
        start_date=test_date_1,
        end_date=test_date_2,
        max_download_workers=8,
        enable_checkpointing=True
    )

    print()
    print("="*80)
    print("TEST COMPLETE")
    print(f"Processed {len(result)} files")
    print("="*80)
