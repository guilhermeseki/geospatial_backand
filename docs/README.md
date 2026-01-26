# Geospatial Backend Documentation

Documentation for the locations validation feature.

## Quick Links

### API Documentation
- **[Locations API Documentation](LOCATIONS_API_DOCUMENTATION.md)** - Complete API reference for `/locations` endpoints
- **[Validation Rules Summary](VALIDATION_RULES_SUMMARY.md)** - Detailed validation rules and examples
- **[Quick Start Guide](QUICK_START_LOCATIONS.md)** - Get started quickly
- **[API Start Instructions](API_START_INSTRUCTIONS.md)** - How to properly start the API

### Testing
- **[Test Directory](../tests/locations/)** - All test files and test data
- **[Test README](../tests/locations/README.md)** - How to run tests

## Feature Overview

The Locations API provides file upload validation for geographic points within Brazil.

### Key Features
- ✅ XLSX and CSV file support
- ✅ Case-insensitive column matching
- ✅ Brazilian territory validation
- ✅ Detailed error reporting
- ✅ Empty row handling

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/locations/validate` | POST | Validate file without saving |
| `/locations/upload` | POST | Validate and save (DB pending) |

### Required File Format

Your file must have these columns (case-insensitive):
- `local` - Location name (string or number)
- `latitude` - Decimal degrees (must be number)
- `longitude` - Decimal degrees (must be number)

### Brazilian Boundaries

- **Latitude**: -33.7683° to 5.2711°
- **Longitude**: -73.9870° to -34.7937°

## Quick Start

### 1. Start the API

The API now works from any directory (imports fixed):

```bash
# From anywhere:
cd /opt/geospatial_backend/app/api
uvicorn main:app --host 0.0.0.0 --port 8000

# Or from project root:
cd /opt/geospatial_backend
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Test the Endpoint

```bash
# Simple test (waits for API)
python tests/locations/test_locations_simple.py

# Or use Swagger UI
open http://localhost:8000/docs
```

### 3. Upload a File

```bash
curl -X POST "http://localhost:8000/locations/validate" \
  -F "file=@tests/locations/test_valid_cities.xlsx" | jq .
```

## Implementation Files

### Core Files
- `app/utils/xlsx_validation.py` - Validation logic
- `app/api/routers/locations.py` - API endpoints
- `app/api/main.py` - Router registration (modified)

### Test Files
- `tests/locations/test_xlsx_validation.py` - Unit tests
- `tests/locations/test_empty_rows.py` - Empty row tests
- `tests/locations/test_locations_api.py` - API tests
- `tests/locations/test_locations_simple.py` - Simple API test

### Documentation Files
- `docs/LOCATIONS_API_DOCUMENTATION.md` - Full API docs
- `docs/VALIDATION_RULES_SUMMARY.md` - Validation rules
- `docs/QUICK_START_LOCATIONS.md` - Quick start
- `docs/API_START_INSTRUCTIONS.md` - API start guide

## Validation Examples

### Valid Entry
```csv
local,latitude,longitude
São Paulo,-23.5505,-46.6333
```
✅ All fields present, within Brazil

### Invalid - Outside Brazil
```csv
local,latitude,longitude
Caracas,10.4806,-66.9036
```
❌ Latitude too far north (outside Brazil)

### Invalid - Missing Data
```csv
local,latitude,longitude
Test City,,-46.6333
```
❌ Latitude missing

### Skipped - Empty Row
```csv
local,latitude,longitude
,,
```
⏭️ All fields empty, skipped silently

## Troubleshooting

### API won't start
- ✅ Fixed! API now works from any directory (sys.path auto-configured)
- Check logs: `tail -f /var/log/fastapi/geospatial_backend.log`

### Endpoint not found
- Verify locations router is registered
- Check logs show: "Routers registered: ...locations"

### Tests failing
- Make sure API is running
- Run from project root: `cd /opt/geospatial_backend`
- Check test README: `tests/locations/README.md`

## Next Steps

- [ ] Add database integration to `/locations/upload`
- [ ] Add authentication for upload endpoint
- [ ] Add batch operations support
- [ ] Add GET endpoints to retrieve saved locations

## Support

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Status**: http://localhost:8000/status
