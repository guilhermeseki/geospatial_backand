# Quick Start: Locations API

## What Was Implemented

✅ **File Validation Function** (`app/utils/xlsx_validation.py`)
- Validates XLSX/CSV files with geographic coordinates
- Checks all points are within Brazil's boundaries
- Provides detailed error messages for invalid data

✅ **API Endpoints** (`app/api/routers/locations.py`)
- `POST /locations/validate` - Validate file without saving
- `POST /locations/upload` - Validate and save (DB integration pending)

✅ **Integration** (`app/api/main.py`)
- Registered locations router
- Added to API documentation

## How to Test

### Step 1: Restart the API

```bash
# Kill old process
pkill -f "uvicorn main:app"

# Start new process with updated code
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Run Unit Tests

```bash
# Test the validation function
python test_xlsx_validation.py
```

Expected output:
```
✓ Valid rows: 4
  - São Paulo: (-23.5505, -46.6333)
  - Rio de Janeiro: (-22.9068, -43.1729)
  - Brasília: (-15.7942, -47.8822)
  - Porto Alegre: (-30.0346, -51.2177)

✗ Invalid rows: 6
  - Row 5: Caracas (outside Brazil)
  - Row 6: Lima (outside Brazil)
  - Row 7: Missing local field
  ...
```

### Step 3: Run API Tests

```bash
# Test the API endpoints (requires API to be running)
python test_locations_api.py
```

This will create sample XLSX files and test the validation endpoint.

### Step 4: Test via Swagger UI

1. Open http://localhost:8000/docs
2. Navigate to "locations" section
3. Try `POST /locations/validate`
4. Upload a test file (created by `test_locations_api.py`)
5. See validation results

### Step 5: Test via cURL

```bash
# Create a simple test file first
cat > test.csv << 'EOF'
local,latitude,longitude
São Paulo,-23.5505,-46.6333
Rio de Janeiro,-22.9068,-43.1729
Caracas,10.4806,-66.9036
EOF

# Test the endpoint
curl -X POST "http://localhost:8000/locations/validate" \
  -F "file=@test.csv" \
  | jq .
```

Expected output:
```json
{
  "valid_rows": [
    {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
    {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729}
  ],
  "invalid_rows": [
    {
      "_row_number": 4,
      "local": "Caracas",
      "latitude": 10.4806,
      "longitude": -66.9036,
      "failure_reason": "Latitude 10.4806 is outside the Brazilian range (-33.7683 to 5.2711)"
    }
  ]
}
```

## File Structure

```
/opt/geospatial_backend/
├── app/
│   ├── api/
│   │   ├── main.py                    # ✏️ Modified: Added locations router
│   │   └── routers/
│   │       └── locations.py           # ✨ New: Locations API endpoints
│   └── utils/
│       └── xlsx_validation.py         # ✨ New: Validation logic
├── test_xlsx_validation.py            # ✨ New: Unit tests
├── test_locations_api.py              # ✨ New: API integration tests
├── LOCATIONS_API_DOCUMENTATION.md     # ✨ New: Full documentation
└── QUICK_START_LOCATIONS.md           # ✨ New: This file
```

## Validation Rules

### 1. File Format
- ✅ XLSX (primary format)
- ✅ CSV (fallback)
- ❌ Other formats rejected

### 2. Required Columns (case-insensitive)
- `local` - Location name
- `latitude` - Decimal degrees
- `longitude` - Decimal degrees

### 3. Data Validation
- **Presence**: All fields must be present and non-empty
- **Numeric**: Latitude and longitude must be valid numbers
- **Geographic**: Must be within Brazilian boundaries
  - Latitude: -33.7683° to 5.2711°
  - Longitude: -73.9870° to -34.7937°

## Example Valid File

**locations.xlsx**:
```
local           | latitude  | longitude
----------------|-----------|----------
São Paulo       | -23.5505  | -46.6333
Rio de Janeiro  | -22.9068  | -43.1729
Brasília        | -15.7942  | -47.8822
Salvador        | -12.9714  | -38.5014
Fortaleza       | -3.7172   | -38.5433
Belo Horizonte  | -19.9167  | -43.9345
Manaus          | -3.1190   | -60.0217
Curitiba        | -25.4290  | -49.2671
Recife          | -8.0476   | -34.8770
Porto Alegre    | -30.0346  | -51.2177
```

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Field 'local' is missing or empty` | Location name is blank | Fill in the location name |
| `Field 'latitude' is missing or empty` | Latitude is blank | Provide a latitude value |
| `Latitude is not a numeric value` | Latitude is text, not a number | Use decimal degrees (e.g., -23.5505) |
| `Latitude X is outside the Brazilian range` | Point is outside Brazil | Verify coordinates are correct |
| `Missing required columns: longitude` | Column header is wrong | Use headers: local, latitude, longitude |
| `Unsupported file format` | Wrong file type | Use .xlsx or .csv files only |

## API Endpoints Summary

### Validate (Recommended for preview)

```bash
POST /locations/validate
Content-Type: multipart/form-data
File: locations.xlsx or locations.csv

Returns:
- valid_rows: Array of valid locations
- invalid_rows: Array of invalid locations with reasons
```

### Upload (For saving to database)

```bash
POST /locations/upload
Content-Type: multipart/form-data
File: locations.xlsx or locations.csv

Returns:
- message: Success message
- summary: Counts of valid/invalid/total
- valid_rows: Valid locations that were saved
- invalid_rows: Invalid locations with reasons
```

## Next Steps After Restart

1. **Verify API is running**: http://localhost:8000/health
2. **Check API docs**: http://localhost:8000/docs
3. **Look for locations section** in Swagger UI
4. **Test with sample files** created by `test_locations_api.py`
5. **Integrate with your frontend** using the validation endpoint

## Need Help?

- Full documentation: `LOCATIONS_API_DOCUMENTATION.md`
- API docs: http://localhost:8000/docs
- Test the validation: `python test_xlsx_validation.py`
- Test the API: `python test_locations_api.py`
