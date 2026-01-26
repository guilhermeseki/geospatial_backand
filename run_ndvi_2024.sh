#!/bin/bash
# Run MODIS NDVI processing for 2024
# This script can be run directly in terminal to avoid Cursor crashes

cd /opt/geospatial_backend

echo "=========================================="
echo "Processing MODIS NDVI for 2024"
echo "=========================================="
echo "Date range: 2024-08-01 to 2024-12-31"
echo "This will take a while..."
echo ""

/home/guilherme/miniconda3/envs/horus/bin/python -c "
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date

result = ndvi_data_flow(
    start_date=date(2024, 8, 1),
    end_date=date(2024, 12, 31),
    sources=['modis'],
    batch_days=16
)

print(f'\n✓ COMPLETE: Processed {len(result)} files')
"

echo ""
echo "Processing finished!"


