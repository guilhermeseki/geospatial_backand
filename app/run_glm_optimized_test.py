#!/usr/bin/env python3
"""
Test script for optimized GLM FED flow
Processes a single day to verify optimizations work correctly
"""
from datetime import date, timedelta
from app.workflows.data_processing.glm_fed_flow_optimized import glm_fed_flow_optimized
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

if __name__ == "__main__":
    # Test with a recent date (yesterday or specific date)
    test_date = date(2025, 4, 15)  # Adjust as needed

    print("="*80)
    print("TESTING OPTIMIZED GLM FLOW")
    print("="*80)
    print(f"Test date: {test_date}")
    print(f"Optimizations enabled:")
    print(f"  - Parallel downloads (8 workers)")
    print(f"  - Progress tracking")
    print(f"  - Checkpointing")
    print("="*80)
    print()

    result = glm_fed_flow_optimized(
        start_date=test_date,
        end_date=test_date,
        max_download_workers=8,
        enable_checkpointing=True
    )

    print()
    print("="*80)
    print("TEST COMPLETE")
    print(f"Processed {len(result)} files")
    print("="*80)
