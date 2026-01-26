#!/usr/bin/env python3
"""
Daily Precipitation Update Script
Downloads yesterday's data and updates yearly historical files
Used by systemd timer for automated daily updates
"""
from app.workflows.data_processing.precipitation_flow import precipitation_batch_flow
from app.workflows.data_processing.schemas import DataSource
from datetime import date, timedelta

if __name__ == "__main__":
    yesterday = date.today() - timedelta(days=1)

    print("="*80)
    print("DAILY PRECIPITATION UPDATE")
    print("="*80)
    print(f"Date: {yesterday}")
    print("="*80)
    print()

    # Update CHIRPS
    print("[1/2] Processing CHIRPS...")
    chirps_result = precipitation_batch_flow(
        source=DataSource.CHIRPS,
        start_date=yesterday,
        end_date=yesterday,
        create_historical=True
    )

    # Update MERGE
    print("\n[2/2] Processing MERGE...")
    merge_result = precipitation_batch_flow(
        source=DataSource.MERGE,
        start_date=yesterday,
        end_date=yesterday,
        create_historical=True
    )

    print("\n" + "="*80)
    print("✅ DAILY UPDATE COMPLETE")
    print("="*80)
