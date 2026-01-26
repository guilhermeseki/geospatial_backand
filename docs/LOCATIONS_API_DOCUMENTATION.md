# Locations API Documentation

## Overview

The Locations API provides endpoints for validating and uploading geographic point data via XLSX or CSV files. All coordinates are validated against Brazilian geographic boundaries.

## Features

- ✅ **File Format Support**: XLSX (primary) and CSV (fallback)
- ✅ **Case-Insensitive Headers**: Column names can be in any case (LOCAL, local, Local, etc.)
- ✅ **Brazilian Territory Validation**: Automatically validates coordinates are within Brazil
- ✅ **Detailed Error Reporting**: Each invalid row includes specific failure reasons
- ✅ **Robust Data Validation**: Checks for presence, numeric types, and geographic boundaries

## Brazilian Geographic Boundaries

All coordinates must fall within these boundaries:

- **Latitude**: -33.7683° to 5.2711°
- **Longitude**: -73.9870° to -34.7937°

## File Format Requirements

### Required Columns

Your XLSX or CSV file must contain these three columns (case-insensitive):

1. `local` - Location name (text)
2. `latitude` - Latitude in decimal degrees (number)
3. `longitude` - Longitude in decimal degrees (number)

### Example XLSX/CSV Structure

```
local           | latitude  | longitude
----------------|-----------|----------
São Paulo       | -23.5505  | -46.6333
Rio de Janeiro  | -22.9068  | -43.1729
Brasília        | -15.7942  | -47.8822
Salvador        | -12.9714  | -38.5014
```

## API Endpoints

### 1. Validate Location File

**Endpoint**: `POST /locations/validate`

**Description**: Validates geographic points without saving them to the database.

**Request**:
```bash
curl -X POST "http://localhost:8000/locations/validate" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@locations.xlsx"
```

**Response** (200 OK):
```json
{
  "valid_rows": [
    {
      "local": "São Paulo",
      "latitude": -23.5505,
      "longitude": -46.6333
    },
    {
      "local": "Rio de Janeiro",
      "latitude": -22.9068,
      "longitude": -43.1729
    }
  ],
  "invalid_rows": [
    {
      "_row_number": 5,
      "local": "Caracas",
      "latitude": 10.4806,
      "longitude": -66.9036,
      "failure_reason": "Latitude 10.4806 is outside the Brazilian range (-33.7683 to 5.2711)"
    },
    {
      "_row_number": 6,
      "local": "Test City",
      "latitude": null,
      "longitude": -46.6333,
      "failure_reason": "Field 'latitude' is missing or empty"
    }
  ]
}
```

### 2. Upload and Save Locations

**Endpoint**: `POST /locations/upload`

**Description**: Validates and saves valid geographic points to the database.

**Note**: Currently returns validation results. Database integration is pending.

**Request**:
```bash
curl -X POST "http://localhost:8000/locations/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@locations.xlsx"
```

**Response** (200 OK):
```json
{
  "message": "Successfully validated 3 locations",
  "summary": {
    "valid_count": 3,
    "invalid_count": 2,
    "total_processed": 5
  },
  "valid_rows": [...],
  "invalid_rows": [...]
}
```

**Response** (400 Bad Request - No valid locations):
```json
{
  "detail": {
    "message": "No valid locations found in file",
    "invalid_rows": [...]
  }
}
```

## Validation Rules

The API performs three levels of validation for each row:

### 1. Presence Check
- All three fields (`local`, `latitude`, `longitude`) must be present
- Fields cannot be null or empty
- Example failure: `"Field 'latitude' is missing or empty"`

### 2. Numeric Check
- `latitude` and `longitude` must be valid decimal numbers
- Strings or non-numeric values are rejected
- Example failure: `"Latitude is not a numeric value (received: 'not a number')"`

### 3. Geographic Boundary Check
- Latitude must be between -33.7683 and 5.2711
- Longitude must be between -73.9870 and -34.7937
- Example failure: `"Latitude 10.4806 is outside the Brazilian range (-33.7683 to 5.2711)"`

## Error Responses

### 400 Bad Request - Unsupported File Format
```json
{
  "detail": "Unsupported file format: document.pdf. Only XLSX and CSV files are accepted."
}
```

### 400 Bad Request - Empty File
```json
{
  "detail": "Uploaded file is empty"
}
```

### 400 Bad Request - Missing Columns
```json
{
  "valid_rows": [],
  "invalid_rows": [
    {
      "failure_reason": "Missing required columns: longitude. Expected columns: local, latitude, longitude (case-insensitive)"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error processing file: <error message>"
}
```

## Usage Examples

### Python Example

```python
import requests

# Validate a file
with open('locations.xlsx', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/locations/validate',
        files={'file': ('locations.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    )

result = response.json()
print(f"Valid: {len(result['valid_rows'])}")
print(f"Invalid: {len(result['invalid_rows'])}")

# Print invalid rows with reasons
for row in result['invalid_rows']:
    print(f"Row {row['_row_number']}: {row['failure_reason']}")
```

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/locations/validate', {
  method: 'POST',
  body: formData
})
  .then(response => response.json())
  .then(data => {
    console.log(`Valid rows: ${data.valid_rows.length}`);
    console.log(`Invalid rows: ${data.invalid_rows.length}`);

    // Display errors
    data.invalid_rows.forEach(row => {
      console.error(`Row ${row._row_number}: ${row.failure_reason}`);
    });
  });
```

### cURL Example

```bash
# Validate XLSX file
curl -X POST "http://localhost:8000/locations/validate" \
  -F "file=@locations.xlsx" \
  | jq .

# Validate CSV file
curl -X POST "http://localhost:8000/locations/validate" \
  -F "file=@locations.csv" \
  | jq .
```

## Testing

### Run Unit Tests

```bash
# Test the validation function directly
python test_xlsx_validation.py
```

### Test API Endpoints

```bash
# Make sure API is running first
# uvicorn app.api.main:app --reload

# Run API tests
python test_locations_api.py
```

This will:
1. Create sample XLSX files with various test cases
2. Test the `/locations/validate` endpoint
3. Display validation results for each test case

## Common Test Cases

### Valid Brazilian Cities
```csv
local,latitude,longitude
São Paulo,-23.5505,-46.6333
Rio de Janeiro,-22.9068,-43.1729
Brasília,-15.7942,-47.8822
```

### Invalid - Outside Brazil
```csv
local,latitude,longitude
Caracas,10.4806,-66.9036
Lima,-12.0464,-77.0428
```

### Invalid - Missing Data
```csv
local,latitude,longitude
Missing Coords,,
,,-46.6333
```

### Invalid - Bad Data Types
```csv
local,latitude,longitude
Bad Coords,not a number,-46.6333
Bad Coords 2,-23.5505,invalid
```

## Integration with Frontend

### Recommended Workflow

1. **User uploads file** → Call `/locations/validate`
2. **Display validation results** → Show valid/invalid counts
3. **User reviews errors** → Display `invalid_rows` with failure reasons
4. **User confirms** → Call `/locations/upload` to save valid rows
5. **Show success** → Display summary of saved locations

### Response Structure

Each valid row contains:
- `local`: String (location name)
- `latitude`: Float (decimal degrees)
- `longitude`: Float (decimal degrees)

Each invalid row contains:
- `_row_number`: Integer (row number in file, 1-indexed after header)
- `local`: Original value (may be null)
- `latitude`: Original value (may be null or non-numeric)
- `longitude`: Original value (may be null or non-numeric)
- `failure_reason`: String (detailed explanation of what failed)

## Files Created

1. **Validation Logic**: `app/utils/xlsx_validation.py`
   - Core validation function
   - Brazilian boundary checking
   - File parsing for XLSX/CSV

2. **API Router**: `app/api/routers/locations.py`
   - `/locations/validate` endpoint
   - `/locations/upload` endpoint
   - File upload handling

3. **Tests**:
   - `test_xlsx_validation.py` - Unit tests for validation function
   - `test_locations_api.py` - Integration tests for API endpoints

4. **Documentation**: `LOCATIONS_API_DOCUMENTATION.md` (this file)

## Next Steps

- [ ] Add database integration to `/locations/upload`
- [ ] Add authentication/authorization for upload endpoint
- [ ] Add rate limiting for file uploads
- [ ] Add support for batch operations
- [ ] Add endpoint to retrieve saved locations
- [ ] Add endpoint to update/delete locations

## Support

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
