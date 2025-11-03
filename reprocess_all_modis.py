"""
Reprocess ALL MODIS NDVI data from 2015-2025 with the fix
"""
from datetime import date
import sys

sys.path.insert(0, '/opt/geospatial_backend')

from app.workflows.data_processing.ndvi_flow import ndvi_data_flow

print("=" * 80)
print("REPROCESSING ALL MODIS NDVI DATA (2015-2025)")
print("=" * 80)
print("\nThis will download and process ~11 years of MODIS data")
print("Expected: ~1150 composites (23 per year * 10 years)")
print("Estimated time: Several hours")
print("\n" + "=" * 80)

# Process year by year for better progress tracking
years = list(range(2015, 2026))  # 2015-2025

total_processed = 0

for year in years:
    print(f"\n{'=' * 80}")
    print(f"PROCESSING YEAR: {year}")
    print("=" * 80)

    if year == 2025:
        # Current year - process up to today
        start_date = date(year, 1, 1)
        end_date = date.today()
    else:
        # Full year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

    print(f"Date range: {start_date} to {end_date}")

    try:
        result = ndvi_data_flow(
            batch_days=365,  # Process full year at once (MODIS will still limit to 100 composites per batch)
            sources=['modis'],
            start_date=start_date,
            end_date=end_date
        )

        year_count = len(result) if result else 0
        total_processed += year_count

        print(f"\n✓ Year {year}: Processed {year_count} files")
        print(f"   Total so far: {total_processed} files")

    except Exception as e:
        print(f"\n✗ Year {year} failed: {e}")
        import traceback
        traceback.print_exc()
        continue

print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print(f"Total files processed: {total_processed}")
print(f"Years completed: 2015-2025")
print("=" * 80)
