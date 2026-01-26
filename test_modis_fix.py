"""
Test script to verify MODIS tile merging fix
Downloads one 16-day period and verifies coverage improvement
"""
from datetime import date
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
import logging

# Configure logging to see details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("TESTING MODIS TILE MERGING FIX")
print("=" * 80)
print("\nThis will download ONE 16-day composite and merge all tiles")
print("Expected result: ~50-80% coverage (vs 0.33% before fix)")
print()
print("Date range: 2024-02-09 to 2024-02-09 (one composite)")
print("=" * 80)
print()

# Set max_items to limit processing for testing
import app.workflows.data_processing.ndvi_flow as ndvi_module
ndvi_module._TEST_MAX_ITEMS = 15  # Limit to 15 tiles for faster testing

# Run flow for one composite period
result = ndvi_data_flow(
    batch_days=16,
    sources=['modis'],
    start_date=date(2024, 2, 9),
    end_date=date(2024, 2, 9)
)

print("\n" + "=" * 80)
print("TEST COMPLETE!")
print("=" * 80)
print(f"Processed {len(result)} files")
print("\nNext steps:")
print("1. Check the logs above for 'Merged mosaic: XX% valid pixels'")
print("2. If XX% > 10%, the fix is working!")
print("3. Restart FastAPI to load the new data")
print("=" * 80)
