"""
Test script for XLSX/CSV validation functionality.

Demonstrates validation of geographic points for Brazilian territory.
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


def create_test_data():
    """Create test data with both valid and invalid rows."""
    return pd.DataFrame([
        # Valid rows (within Brazil)
        {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
        {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729},
        {"local": "Brasília", "latitude": -15.7942, "longitude": -47.8822},

        # Invalid: Outside Brazil (latitude too far north)
        {"local": "Caracas", "latitude": 10.4806, "longitude": -66.9036},

        # Invalid: Outside Brazil (longitude too far west)
        {"local": "Lima", "latitude": -12.0464, "longitude": -77.0428},

        # Invalid: Missing local field
        {"local": None, "latitude": -23.5505, "longitude": -46.6333},

        # Invalid: Missing latitude
        {"local": "Test City", "latitude": None, "longitude": -46.6333},

        # Invalid: Non-numeric latitude
        {"local": "Bad Coords", "latitude": "not a number", "longitude": -46.6333},

        # Invalid: Non-numeric longitude
        {"local": "Bad Coords 2", "latitude": -23.5505, "longitude": "invalid"},

        # Valid: Edge case - near border
        {"local": "Porto Alegre", "latitude": -30.0346, "longitude": -51.2177},
    ])


def test_xlsx_validation():
    """Test XLSX validation."""
    print("=" * 80)
    print("Testing XLSX Validation")
    print("=" * 80)

    # Create test dataframe
    df = create_test_data()

    # Save to XLSX in memory
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    # Validate
    result = validate_geographic_points(buffer.read(), "test.xlsx")

    # Display results
    print(f"\n✓ Valid rows: {len(result['valid_rows'])}")
    for row in result['valid_rows']:
        print(f"  - {row['local']}: ({row['latitude']}, {row['longitude']})")

    print(f"\n✗ Invalid rows: {len(result['invalid_rows'])}")
    for row in result['invalid_rows']:
        print(f"  - Row {row.get('_row_number')}: {row.get('local', 'N/A')}")
        print(f"    Reason: {row['failure_reason']}")

    return result


def test_csv_validation():
    """Test CSV validation (fallback format)."""
    print("\n" + "=" * 80)
    print("Testing CSV Validation (Fallback)")
    print("=" * 80)

    # Create test dataframe
    df = create_test_data()

    # Save to CSV in memory
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    # Validate
    result = validate_geographic_points(buffer.read(), "test.csv")

    # Display results
    print(f"\n✓ Valid rows: {len(result['valid_rows'])}")
    print(f"✗ Invalid rows: {len(result['invalid_rows'])}")

    return result


def test_case_insensitive_columns():
    """Test case-insensitive column matching."""
    print("\n" + "=" * 80)
    print("Testing Case-Insensitive Column Names")
    print("=" * 80)

    # Create dataframe with mixed case columns
    df = pd.DataFrame([
        {"LOCAL": "São Paulo", "LATITUDE": -23.5505, "LONGITUDE": -46.6333},
        {"Local": "Rio", "Latitude": -22.9068, "Longitude": -43.1729},
    ])

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    result = validate_geographic_points(buffer.read(), "test_mixed_case.xlsx")

    print(f"✓ Valid rows: {len(result['valid_rows'])} (should be 2)")
    print(f"✗ Invalid rows: {len(result['invalid_rows'])} (should be 0)")

    return result


def test_missing_columns():
    """Test handling of missing required columns."""
    print("\n" + "=" * 80)
    print("Testing Missing Required Columns")
    print("=" * 80)

    # Create dataframe missing 'longitude' column
    df = pd.DataFrame([
        {"local": "São Paulo", "latitude": -23.5505},
    ])

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    result = validate_geographic_points(buffer.read(), "test_missing_column.xlsx")

    print(f"Expected error: {result['invalid_rows'][0]['failure_reason']}")

    return result


if __name__ == "__main__":
    try:
        # Run all tests
        test_xlsx_validation()
        test_csv_validation()
        test_case_insensitive_columns()
        test_missing_columns()

        print("\n" + "=" * 80)
        print("All tests completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
