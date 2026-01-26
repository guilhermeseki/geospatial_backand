# API Start Instructions - IMPORTANT

## Current Issue

The API process is running but **from the wrong directory**:
- ❌ Currently running from: `/opt/geospatial_backend/app/api/`
- ✅ Should run from: `/opt/geospatial_backend/` (project root)

This causes the imports to fail and the API doesn't initialize properly.

## How to Properly Start the API

### Option 1: Use the Start Script (Recommended)

```bash
cd /opt/geospatial_backend
./START_API.sh
```

### Option 2: Manual Start

```bash
# 1. Kill any existing instances
pkill -f "uvicorn main:app"
pkill -f "uvicorn app.api.main:app"

# 2. Change to project root
cd /opt/geospatial_backend

# 3. Start with correct module path
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## What to Look For

When the API starts correctly, you should see:

```
🚀 Starting Geospatial Backend - Climate Data API
================================================================================
📊 Initializing shared climate data service...
...
📋 Climate Data Service Status
================================================================================
Precipitation sources: 2 - ['chirps', 'merge']
Temperature sources: 3 - ['temp_max', 'temp_min', 'temp']
...
🔌 Routers registered: precipitation, temperature, ndvi, wind, lightning, solar, georisk, locations
                                                                                          ^^^^^^^^^
✅ Application initialized successfully
```

**Key indicator**: The line showing routers should include **"locations"** at the end!

## Testing the Locations Endpoint

Once the API is running properly:

### Quick Test with curl

```bash
# Create test file
cat > test.csv << 'EOF'
local,latitude,longitude
São Paulo,-23.5505,-46.6333
Caracas,10.4806,-66.9036
EOF

# Test endpoint
curl -X POST "http://localhost:8000/locations/validate" \
  -F "file=@test.csv" | jq .
```

### Run Python Tests

```bash
# Simple test (waits for API to be ready)
python test_locations_simple.py

# Full test suite
python test_locations_api.py

# Empty row handling test
python test_empty_rows.py
```

### Use Swagger UI

1. Open http://localhost:8000/docs
2. Find the **"locations"** section
3. Try `POST /locations/validate`
4. Upload a test file

## Files You Can Use for Testing

After running `python test_locations_api.py`, these files will be created:
- `test_valid_cities.xlsx` - All valid Brazilian cities
- `test_mixed.xlsx` - Mix of valid and invalid
- `test_all_invalid.xlsx` - All outside Brazil
- `test_case_insensitive.xlsx` - Tests case-insensitive headers

## Implementation Summary

### What Was Created

1. **`app/utils/xlsx_validation.py`**
   - Core validation function
   - Handles XLSX and CSV files
   - Validates Brazilian boundaries
   - Skips empty rows silently

2. **`app/api/routers/locations.py`**
   - `POST /locations/validate` - Validation endpoint
   - `POST /locations/upload` - Upload endpoint (DB pending)

3. **`app/api/main.py`** (Modified)
   - Added `locations` router import
   - Registered locations router
   - Added to endpoint list

### Validation Rules

- ✅ **Empty rows** (all 3 fields empty) → Skipped silently
- ❌ **Partial data** (some fields empty) → Rejected with error
- 🔢 **latitude/longitude** → Must be valid floats
- 🇧🇷 **Boundaries** → Must be within Brazil
  - Latitude: -33.7683° to 5.2711°
  - Longitude: -73.9870° to -34.7937°
- 📝 **local field** → Can be string or number, not empty

### Documentation Files

- `LOCATIONS_API_DOCUMENTATION.md` - Complete API documentation
- `VALIDATION_RULES_SUMMARY.md` - Detailed validation rules
- `QUICK_START_LOCATIONS.md` - Quick start guide
- `API_START_INSTRUCTIONS.md` - This file

## Troubleshooting

### API not responding
- Check it's running from `/opt/geospatial_backend/` (use `pwdx <PID>`)
- Check logs: `tail -f /var/log/fastapi/geospatial_backend.log`
- Make sure no other process is using port 8000

### "locations" endpoint not found
- API must be started from project root
- Check logs show "locations" in registered routers
- Restart using `./START_API.sh`

### Validation not working as expected
- Run unit tests: `python test_xlsx_validation.py`
- Run empty row tests: `python test_empty_rows.py`
- Check VALIDATION_RULES_SUMMARY.md for expected behavior

## Ready to Go!

Everything is implemented and ready. Just start the API properly and test! 🚀
