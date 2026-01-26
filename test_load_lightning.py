#!/usr/bin/env python3
"""Test loading lightning dataset manually"""
import sys
sys.path.insert(0, '/opt/geospatial_backend')

from app.services.climate_data import load_lightning_datasets, get_dataset, _climate_datasets
import traceback

print("="*70)
print("Manually loading lightning datasets...")
print("="*70)

try:
    # Check current state
    print(f"Current climate datasets keys: {list(_climate_datasets.keys())}")
    print(f"Lightning key exists: {'lightning' in _climate_datasets}")
    if 'lightning' in _climate_datasets:
        print(f"Lightning sources: {list(_climate_datasets['lightning'].keys())}")

    print("\nCalling load_lightning_datasets()...")
    load_lightning_datasets()

    print(f"\nAfter loading:")
    print(f"Climate datasets keys: {list(_climate_datasets.keys())}")
    if 'lightning' in _climate_datasets:
        print(f"Lightning sources: {list(_climate_datasets['lightning'].keys())}")

    # Try to get the dataset
    ds = get_dataset('lightning', 'glm_fed')
    print(f"\nget_dataset('lightning', 'glm_fed'): {ds is not None}")
    if ds:
        print(f"  Dims: {dict(ds.dims)}")
        print(f"  Coords: {list(ds.coords)}")
        print(f"  Vars: {list(ds.data_vars)}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
