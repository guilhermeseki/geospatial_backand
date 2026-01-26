#!/usr/bin/env python3
"""
Test script to download and process a single day of GLM FED data.
Tests the fixed coordinate handling code.
"""
from datetime import date
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

# Test with a recent date that hasn't been processed yet
# Let's try April 27, 2025 (next day after current processing)
test_date = date(2025, 4, 27)

print("=" * 80)
print("GLM FED SINGLE DAY TEST")
print("=" * 80)
print(f"Testing date: {test_date}")
print(f"This will test:")
print(f"  1. Download of minute-level data from NASA")
print(f"  2. Aggregation to 30-minute fixed bins")
print(f"  3. GeoTIFF creation for GeoServer")
print(f"  4. Historical NetCDF append (with fixed coordinate handling)")
print("=" * 80)
print()

# Run the flow for just this one day
result = glm_fed_flow(
    start_date=test_date,
    end_date=test_date
)

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
if result:
    print(f"✓ Successfully processed {len(result)} file(s)")
    for f in result:
        print(f"  - {f}")
else:
    print("⚠ No files were processed (may already exist)")
print("=" * 80)
