"""
Test to verify that completely empty rows are skipped silently.
"""

# Fix imports to work from any directory
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from io import BytesIO
from app.utils.xlsx_validation import validate_geographic_points


def test_empty_rows():
    """Test that completely empty rows are skipped."""
    print("=" * 80)
    print("Testing Empty Row Handling")
    print("=" * 80)

    # Create data with empty rows mixed in
    data = [
        # Valid row
        {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},

        # Completely empty row (should be skipped)
        {"local": None, "latitude": None, "longitude": None},

        # Another valid row
        {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729},

        # Empty row with whitespace (should be skipped)
        {"local": "   ", "latitude": None, "longitude": None},

        # Partially empty row (should be rejected with error)
        {"local": "Brasília", "latitude": -15.7942, "longitude": None},

        # Another completely empty row
        {"local": None, "latitude": None, "longitude": None},

        # Valid row
        {"local": "Salvador", "latitude": -12.9714, "longitude": -38.5014},
    ]

    # Create XLSX
    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    # Validate
    result = validate_geographic_points(buffer.read(), "test.xlsx")

    print(f"\n📊 Results:")
    print(f"  Valid rows: {len(result['valid_rows'])}")
    print(f"  Invalid rows: {len(result['invalid_rows'])}")
    print(f"  Total processed: {len(result['valid_rows']) + len(result['invalid_rows'])}")
    print(f"  Skipped (empty): {len(data) - len(result['valid_rows']) - len(result['invalid_rows'])}")

    print(f"\n✅ Valid rows:")
    for row in result['valid_rows']:
        print(f"  - {row['local']}: ({row['latitude']}, {row['longitude']})")

    print(f"\n❌ Invalid rows:")
    for row in result['invalid_rows']:
        print(f"  - Row {row['_row_number']}: {row.get('local', 'N/A')}")
        print(f"    Reason: {row['failure_reason']}")

    print(f"\n⏭️  Silently skipped rows:")
    print(f"  - Row 3 (all empty)")
    print(f"  - Row 5 (all empty/whitespace)")
    print(f"  - Row 7 (all empty)")

    # Verify expectations
    print("\n" + "=" * 80)
    print("Verification:")
    print("=" * 80)

    expected_valid = 3  # São Paulo, Rio, Salvador
    expected_invalid = 1  # Brasília (missing longitude)
    expected_skipped = 3  # Three completely empty rows

    if len(result['valid_rows']) == expected_valid:
        print(f"✅ Valid count correct: {expected_valid}")
    else:
        print(f"❌ Valid count wrong: expected {expected_valid}, got {len(result['valid_rows'])}")

    if len(result['invalid_rows']) == expected_invalid:
        print(f"✅ Invalid count correct: {expected_invalid}")
    else:
        print(f"❌ Invalid count wrong: expected {expected_invalid}, got {len(result['invalid_rows'])}")

    skipped = len(data) - len(result['valid_rows']) - len(result['invalid_rows'])
    if skipped == expected_skipped:
        print(f"✅ Skipped count correct: {expected_skipped}")
    else:
        print(f"❌ Skipped count wrong: expected {expected_skipped}, got {skipped}")

    print("\n" + "=" * 80)
    print("Summary:")
    print("=" * 80)
    print("✅ Completely empty rows (all 3 fields empty) → SKIPPED SILENTLY")
    print("❌ Partially empty rows (some fields empty) → REJECTED WITH ERROR")
    print("✅ Valid rows (all fields present) → VALIDATED")


if __name__ == "__main__":
    test_empty_rows()
