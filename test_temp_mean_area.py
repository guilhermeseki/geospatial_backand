#!/usr/bin/env python3
"""Test temp_mean area triggers to debug the issue"""

import sys
import asyncio
from app.services.climate_data import get_dataset
from app.api.schemas.era5 import ERA5TriggerAreaRequest
from app.api.routers.temperature import _calculate_temperature_area_exceedances_sync

async def test_area_triggers():
    # Get dataset
    ds = get_dataset('temperature', 'temp_mean')

    if ds is None:
        print("ERROR: Dataset not loaded!")
        print("This means the app needs to be running for datasets to be loaded.")
        return

    print("✓ Dataset loaded successfully")
    print(f"  Variables: {list(ds.data_vars)}")
    print(f"  Dims: {dict(ds.dims)}")

    # Create request
    request = ERA5TriggerAreaRequest(
        source='temp_mean',
        lat=-15.8,
        lon=-47.9,
        radius=10.0,
        start_date='2025-01-25',
        end_date='2025-01-25',
        trigger=15.0,
        trigger_type='above'
    )

    print(f"\nTesting area query:")
    print(f"  Location: {request.lat}, {request.lon}")
    print(f"  Radius: {request.radius} km")
    print(f"  Date: {request.start_date}")
    print(f"  Trigger: {request.trigger_type} {request.trigger}°C")

    try:
        # Run the sync function in thread
        grouped_exceedances, num_trigger_dates = await asyncio.to_thread(
            _calculate_temperature_area_exceedances_sync,
            ds,
            request,
            'temp_mean'  # variable name
        )

        print(f"\n✓ Query completed successfully")
        print(f"  Total trigger dates: {num_trigger_dates}")
        print(f"  Total exceedances: {sum(len(points) for points in grouped_exceedances.values())}")

        if grouped_exceedances:
            print(f"\n  Exceedances by date:")
            for date, points in grouped_exceedances.items():
                print(f"    {date}: {len(points)} points")
                for p in points[:3]:  # Show first 3
                    print(f"      - {p}")
        else:
            print("\n  No exceedances found!")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Note: This will only work if run from within the FastAPI app context
    # where datasets are already loaded
    print("=" * 80)
    print("Testing temp_mean area_triggers")
    print("=" * 80)
    asyncio.run(test_area_triggers())
