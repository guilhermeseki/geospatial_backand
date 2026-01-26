#!/usr/bin/env python3
"""Direct test of lightning area triggers and polygon - bypassing API to see actual errors"""
import sys
sys.path.insert(0, '/opt/geospatial_backend')

from app.services.climate_data import get_dataset
from app.api.routers.lightning import _calculate_lightning_area_exceedances_sync
from app.utils.polygon import PolygonProcessor
from app.api.schemas.lightning import LightningTriggerAreaRequest
from app.api.schemas.polygon import PolygonRequest
import traceback

# Test 1: Area triggers
print("="*70)
print("Test 1: Lightning Area Triggers (direct function call)")
print("="*70)

try:
    historical_ds = get_dataset('lightning', 'glm_fed')
    print(f"Dataset loaded: {historical_ds is not None}")

    if historical_ds:
        print(f"Dataset dims: {dict(historical_ds.dims)}")
        print(f"Dataset coords: {list(historical_ds.coords)}")
        print(f"Dataset vars: {list(historical_ds.data_vars)}")

        # Create request
        class MockRequest:
            lat = -15.8
            lon = -47.9
            radius = 50
            start_date = "2025-11-01"
            end_date = "2025-11-30"
            trigger = 3.0
            trigger_type = "above"

        request = MockRequest()

        print(f"\nCalling _calculate_lightning_area_exceedances_sync...")
        result = _calculate_lightning_area_exceedances_sync(historical_ds, request)
        print(f"✅ Success! Found {result[1]} trigger dates")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"\nFull traceback:")
    traceback.print_exc()

# Test 2: Polygon
print("\n" + "="*70)
print("Test 2: Lightning Polygon (direct function call)")
print("="*70)

try:
    historical_ds = get_dataset('lightning', 'glm_fed')
    print(f"Dataset loaded: {historical_ds is not None}")

    if historical_ds:
        print(f"Dataset dims: {dict(historical_ds.dims)}")

        # Create polygon request
        class MockPolygonRequest:
            coordinates = [
                (-48.0, -15.7),
                (-47.8, -15.7),
                (-47.8, -15.9),
                (-48.0, -15.9),
                (-48.0, -15.7)
            ]
            source = "glm_fed"
            start_date = "2025-11-01"
            end_date = "2025-11-30"
            statistic = "mean"
            trigger = None
            consecutive_days = 1

        request = MockPolygonRequest()

        processor = PolygonProcessor(historical_ds, 'fed_30min_max')
        print(f"\nPolygonProcessor created")
        print(f"Calling calculate_polygon_stats...")

        result = processor.calculate_polygon_stats(request)
        print(f"✅ Success! Got {len(result.get('results', []))} results")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"\nFull traceback:")
    traceback.print_exc()
