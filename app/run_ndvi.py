#!/usr/bin/env python3
"""
NDVI MODIS Data Download Script
Downloads MODIS NDVI data (250m, 16-day composites) for Latin America
Uses Microsoft Planetary Computer (100% FREE, no authentication!)
"""
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date

if __name__ == "__main__":
    # MODIS data from 2015 to present
    start_date = date(2015, 1, 1)
    end_date = date.today()

    print("="*80)
    print("MODIS NDVI DATA DOWNLOAD")
    print("="*80)
    print(f"Date range: {start_date} to {end_date}")
    print(f"Source: MODIS MOD13Q1.061 (250m resolution, 16-day composites)")
    print(f"Provider: Microsoft Planetary Computer (FREE!)")
    print(f"Region: Latin America")
    print("="*80)
    print()

    # Run the flow
    # MODIS has 16-day composites (~23 per year)
    # batch_days=32 means ~2 composites per download request
    result = ndvi_data_flow(
        start_date=start_date,
        end_date=end_date,
        sources=['modis'],  # Only MODIS for now
        batch_days=32  # ~2 composites per batch (16-day interval)
    )

    print(f"\n✓ Processed {len(result)} files")