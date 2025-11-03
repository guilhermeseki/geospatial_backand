"""
Test MODIS fix with samples from DIFFERENT YEARS
Before doing full reprocessing, verify the fix works across years
"""
from datetime import date
import sys
import rasterio
import numpy as np

sys.path.insert(0, '/opt/geospatial_backend')

from app.workflows.data_processing.ndvi_flow import ndvi_data_flow

print("=" * 80)
print("TESTING MODIS FIX ACROSS MULTIPLE YEARS")
print("=" * 80)

# Test dates from different years
test_dates = [
    ("2015", date(2015, 6, 15), date(2015, 6, 20)),  # Start of dataset
    ("2018", date(2018, 3, 10), date(2018, 3, 15)),  # Middle year
    ("2021", date(2021, 9, 5), date(2021, 9, 10)),   # Recent year
    ("2024", date(2024, 8, 1), date(2024, 8, 5)),    # Very recent
]

results = []

for year_label, start, end in test_dates:
    print(f"\n{'=' * 80}")
    print(f"TESTING YEAR {year_label}: {start} to {end}")
    print("=" * 80)

    try:
        result = ndvi_data_flow(
            batch_days=16,
            sources=['modis'],
            start_date=start,
            end_date=end
        )

        if result and len(result) > 0:
            # Check the first file
            test_file = result[0]
            print(f"\n✓ Created {len(result)} file(s)")
            print(f"  Checking: {test_file.name}")

            with rasterio.open(test_file) as src:
                data = src.read(1)
                valid = data[~np.isnan(data)]

                # Check for the bug
                neg_03 = np.sum(np.abs(data + 0.3) < 0.001)
                unique_count = len(np.unique(valid))

                stats = {
                    'year': year_label,
                    'file': test_file.name,
                    'shape': data.shape,
                    'valid_pixels': len(valid),
                    'unique_values': unique_count,
                    'min': float(np.nanmin(data)) if len(valid) > 0 else None,
                    'max': float(np.nanmax(data)) if len(valid) > 0 else None,
                    'mean': float(np.nanmean(data)) if len(valid) > 0 else None,
                    'bug_count': int(neg_03),
                    'status': 'PASS' if neg_03 == 0 and unique_count > 100 else 'FAIL'
                }

                results.append(stats)

                print(f"  Shape: {stats['shape']}")
                print(f"  Valid pixels: {stats['valid_pixels']:,}")
                print(f"  Unique values: {stats['unique_values']:,}")
                if stats['min'] is not None:
                    print(f"  Range: {stats['min']:.4f} to {stats['max']:.4f}")
                    print(f"  Mean: {stats['mean']:.4f}")
                print(f"  -0.3 count (bug): {stats['bug_count']}")

                if stats['status'] == 'PASS':
                    print(f"  ✅ PASS: Good data!")
                else:
                    print(f"  ❌ FAIL: Bad data detected!")

        else:
            print(f"  ⚠️  No files created (no data available for this period?)")
            results.append({
                'year': year_label,
                'status': 'NO_DATA'
            })

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'year': year_label,
            'status': 'ERROR',
            'error': str(e)
        })

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

pass_count = sum(1 for r in results if r.get('status') == 'PASS')
fail_count = sum(1 for r in results if r.get('status') == 'FAIL')
no_data_count = sum(1 for r in results if r.get('status') == 'NO_DATA')
error_count = sum(1 for r in results if r.get('status') == 'ERROR')

print(f"\nResults:")
for r in results:
    status_icon = {
        'PASS': '✅',
        'FAIL': '❌',
        'NO_DATA': '⚠️',
        'ERROR': '✗'
    }.get(r['status'], '?')

    if r.get('unique_values'):
        print(f"  {status_icon} {r['year']}: {r['unique_values']:,} unique values, {r['bug_count']} bugs")
    else:
        print(f"  {status_icon} {r['year']}: {r['status']}")

print(f"\n{'=' * 40}")
print(f"PASSED:   {pass_count}/{len(test_dates)}")
print(f"FAILED:   {fail_count}/{len(test_dates)}")
print(f"NO DATA:  {no_data_count}/{len(test_dates)}")
print(f"ERRORS:   {error_count}/{len(test_dates)}")
print("=" * 40)

if pass_count == len(test_dates) or (pass_count > 0 and fail_count == 0):
    print("\n🎉 FIX IS WORKING! Safe to proceed with full reprocessing.")
elif fail_count > 0:
    print("\n⚠️  SOME TESTS FAILED! Do NOT proceed with full reprocessing yet.")
else:
    print("\n⚠️  Mixed results. Review before proceeding.")

print("\n" + "=" * 80)
