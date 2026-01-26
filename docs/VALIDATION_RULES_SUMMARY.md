# Validation Rules Summary

## Complete Validation Logic

The `/locations/validate` endpoint processes each row with the following rules:

## Rule 1: Skip Completely Empty Rows ⏭️

**If ALL three fields are empty → Skip silently (no error reported)**

| local | latitude | longitude | Result |
|-------|----------|-----------|--------|
| (empty) | (empty) | (empty) | ⏭️ SKIPPED |
| "" | NULL | NULL | ⏭️ SKIPPED |
| "   " | NULL | NULL | ⏭️ SKIPPED |

These rows don't appear in `valid_rows` or `invalid_rows`.

---

## Rule 2: Reject Partially Empty Rows ❌

**If ANY field is empty (but not all) → Reject with error**

| local | latitude | longitude | Result | Error Message |
|-------|----------|-----------|--------|---------------|
| "São Paulo" | -23.5505 | (empty) | ❌ INVALID | "Field 'longitude' is missing or empty" |
| (empty) | -23.5505 | -46.6333 | ❌ INVALID | "Field 'local' is missing or empty" |
| "Rio" | (empty) | -46.6333 | ❌ INVALID | "Field 'latitude' is missing or empty" |
| (empty) | (empty) | -46.6333 | ❌ INVALID | "Field 'local' is missing or empty; Field 'latitude' is missing or empty" |

---

## Rule 3: Validate Data Types 🔢

**latitude and longitude must be convertible to float**

| local | latitude | longitude | Result | Error Message |
|-------|----------|-----------|--------|---------------|
| "São Paulo" | "not a number" | -46.6333 | ❌ INVALID | "Latitude is not a numeric value (received: 'not a number')" |
| "Rio" | -23.5505 | "abc" | ❌ INVALID | "Longitude is not a numeric value (received: 'abc')" |
| "123" | -23.5505 | -46.6333 | ✅ VALID | local can be number or string |
| 456 | -23.5505 | -46.6333 | ✅ VALID | local converted to string "456" |

**local can be string OR number (but not empty)**

---

## Rule 4: Check Brazilian Boundaries 🇧🇷

**Coordinates must fall within Brazil's geographic boundaries**

### Boundaries:
- **Latitude**: -33.7683° to 5.2711°
- **Longitude**: -73.9870° to -34.7937°

| Location | Latitude | Longitude | Result | Reason |
|----------|----------|-----------|--------|--------|
| São Paulo | -23.5505 | -46.6333 | ✅ VALID | Inside Brazil |
| Caracas (Venezuela) | 10.4806 | -66.9036 | ❌ INVALID | Latitude too far north |
| Lima (Peru) | -12.0464 | -77.0428 | ❌ INVALID | Longitude too far west |
| New York (USA) | 40.7128 | -74.0060 | ❌ INVALID | Latitude too far north |

---

## Complete Examples

### Example 1: Mixed Data File

**Input XLSX:**
```
local           | latitude  | longitude
São Paulo       | -23.5505  | -46.6333
                |           |              ← Completely empty (skipped)
Rio de Janeiro  | -22.9068  | -43.1729
Caracas         | 10.4806   | -66.9036     ← Outside Brazil (invalid)
Brasília        | -15.7942  |              ← Missing longitude (invalid)
                |           |              ← Completely empty (skipped)
Salvador        | -12.9714  | -38.5014
Test            | abc       | -46.6333     ← Bad latitude (invalid)
```

**Output:**
```json
{
  "valid_rows": [
    {"local": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
    {"local": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729},
    {"local": "Salvador", "latitude": -12.9714, "longitude": -38.5014}
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
      "local": "Brasília",
      "latitude": -15.7942,
      "longitude": null,
      "failure_reason": "Field 'longitude' is missing or empty"
    },
    {
      "_row_number": 8,
      "local": "Test",
      "latitude": "abc",
      "longitude": -46.6333,
      "failure_reason": "Latitude is not a numeric value (received: 'abc')"
    }
  ]
}
```

**Summary:**
- ✅ 3 valid rows
- ❌ 3 invalid rows (with reasons)
- ⏭️ 2 empty rows (skipped silently)

---

## Validation Flow Chart

```
For each row in file:
├─ Are ALL 3 fields empty?
│  ├─ YES → ⏭️ Skip row (don't report)
│  └─ NO → Continue validation
│
├─ Is ANY field empty?
│  ├─ YES → ❌ INVALID: "Field 'X' is missing or empty"
│  └─ NO → Continue validation
│
├─ Can latitude/longitude convert to float?
│  ├─ NO → ❌ INVALID: "X is not a numeric value"
│  └─ YES → Continue validation
│
└─ Are coordinates within Brazil's boundaries?
   ├─ NO → ❌ INVALID: "X is outside the Brazilian range"
   └─ YES → ✅ VALID: Add to valid_rows
```

---

## Field-Specific Rules

### `local` Field
- ✅ Can be: String, Number, or any non-empty value
- ❌ Cannot be: NULL, NaN, empty string, whitespace only
- 🔄 Processing: Converted to string in valid output
- Example: `123` → `"123"`, `"São Paulo"` → `"São Paulo"`

### `latitude` Field
- ✅ Must be: Valid decimal number between -33.7683 and 5.2711
- ❌ Cannot be: NULL, NaN, text, outside range
- 🔄 Processing: Converted to float
- Example: `-23.5505` → `-23.5505` (float)

### `longitude` Field
- ✅ Must be: Valid decimal number between -73.9870 and -34.7937
- ❌ Cannot be: NULL, NaN, text, outside range
- 🔄 Processing: Converted to float
- Example: `-46.6333` → `-46.6333` (float)

---

## What Counts as "Empty"?

| Value | Type | Considered Empty? |
|-------|------|-------------------|
| `NULL` / `NaN` / `None` | Null value | ✅ YES |
| `""` (empty string) | String | ✅ YES |
| `"   "` (whitespace only) | String | ✅ YES |
| `"0"` | String | ❌ NO (valid) |
| `0` | Number | ❌ NO (valid) |
| `"São Paulo"` | String | ❌ NO (valid) |
| `-23.5505` | Number | ❌ NO (valid) |

---

## API Response Structure

### Valid Row Structure
```json
{
  "local": "São Paulo",      // String (always)
  "latitude": -23.5505,      // Float
  "longitude": -46.6333      // Float
}
```

### Invalid Row Structure
```json
{
  "_row_number": 5,           // Row number in file (1-indexed after header)
  "local": "value or null",   // Original value from file
  "latitude": "value or null",// Original value from file
  "longitude": "value or null",// Original value from file
  "failure_reason": "Detailed explanation of what failed"
}
```

---

## Testing

Run tests to verify all validation rules:

```bash
# Test basic validation
python test_xlsx_validation.py

# Test empty row handling
python test_empty_rows.py

# Test API endpoints (requires running server)
python test_locations_api.py
```

---

## Summary

✅ **Completely empty rows** → Silently skipped
❌ **Partially empty rows** → Rejected with specific error message
🔢 **Data type validation** → latitude/longitude must be numeric
🇧🇷 **Geographic validation** → All coordinates must be within Brazil
📝 **local field** → Can be text or number, but not empty
