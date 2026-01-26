# Locations Validation Tests

This directory contains tests for the locations validation feature.

## Test Files

### Unit Tests

**`test_xlsx_validation.py`**
- Tests the core validation function directly
- Validates XLSX and CSV file reading
- Tests case-insensitive column matching
- Tests boundary checks and data type validation
- Run: `python tests/locations/test_xlsx_validation.py`

**`test_empty_rows.py`**
- Tests that completely empty rows are skipped silently
- Tests that partially empty rows are rejected with errors
- Run: `python tests/locations/test_empty_rows.py`

### API Integration Tests

**`test_locations_simple.py`**
- Simple API test that waits for API to be ready
- Creates a small test file and validates it
- Good for quick verification
- Run: `python tests/locations/test_locations_simple.py`

**`test_locations_api.py`**
- Comprehensive API endpoint testing
- Creates multiple test scenarios
- Tests all validation edge cases via API
- Run: `python tests/locations/test_locations_api.py`

## Test Data Files

Pre-generated test files for manual testing:

- **`test_valid_cities.xlsx`** - All valid Brazilian cities
- **`test_mixed.xlsx`** - Mix of valid and invalid entries
- **`test_all_invalid.xlsx`** - All locations outside Brazil
- **`test_case_insensitive.xlsx`** - Tests mixed case column names

## Running Tests

### Quick Test
```bash
cd /opt/geospatial_backend
python tests/locations/test_xlsx_validation.py
```

### Full Test Suite
```bash
cd /opt/geospatial_backend
python tests/locations/test_xlsx_validation.py
python tests/locations/test_empty_rows.py
```

### API Tests (requires running API)
```bash
# Make sure API is running first
python tests/locations/test_locations_simple.py
python tests/locations/test_locations_api.py
```

## Expected Test Results

### test_xlsx_validation.py
- ✅ Valid rows: 4 (São Paulo, Rio, Brasília, Porto Alegre)
- ❌ Invalid rows: 6 (various validation failures)

### test_empty_rows.py
- ✅ Valid rows: 3
- ❌ Invalid rows: 1
- ⏭️ Skipped rows: 3 (silently)

### test_locations_simple.py
- ✅ Valid rows: 2 (São Paulo, Rio)
- ❌ Invalid rows: 1 (Caracas - outside Brazil)

## Manual Testing via API

### Using cURL
```bash
cd /opt/geospatial_backend/tests/locations
curl -X POST "http://localhost:8000/locations/validate" \
  -F "file=@test_valid_cities.xlsx" | jq .
```

### Using Swagger UI
1. Open http://localhost:8000/docs
2. Find "locations" section
3. Try POST /locations/validate
4. Upload one of the test XLSX files

## Validation Rules

See `../../docs/VALIDATION_RULES_SUMMARY.md` for complete validation rules.

Quick summary:
- ✅ Empty rows (all fields) → Skipped silently
- ❌ Partial data (some fields) → Rejected with error
- 🔢 lat/lon must be numbers within Brazil
- 📝 local can be text or number, not empty
- 🇧🇷 Brazil bounds: lat [-33.77, 5.27], lon [-73.99, -34.79]
