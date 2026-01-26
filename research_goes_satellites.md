# GOES Satellite Coverage for Brazil

## Current Active GOES Satellites:

### GOES-16 (GOES-East)
- **Position**: 75.2°W (operational location)
- **Coverage**: Eastern Americas, Atlantic
- **Status**: Operational since 2017
- **GLM Availability**: YES ✓

### GOES-18 (GOES-West)
- **Position**: 137.2°W
- **Coverage**: Western Americas, Pacific
- **Status**: Operational since 2023
- **GLM Availability**: YES ✓
- **Brazil Coverage**: Poor (too far west, oblique viewing angle)

### GOES-19
- **Position**: Currently at 75.2°W (replacing GOES-16)
- **Coverage**: Eastern Americas
- **Status**: Operational April 2025
- **GLM Availability**: YES ✓
- **Issue**: Same position as GOES-16, similar limitations

## Coverage Analysis:

All GOES satellites at 75.2°W have the **same geometric limitation** for southern Brazil:
- Geostationary satellites have reduced accuracy at high latitudes
- Viewing angle becomes too oblique beyond ~±60° from subsatellite point
- For 75.2°W position, southern Brazil is at extreme viewing angle

## Historical Data Options:

### GOES-16 Historical Data (2017-2025)
- Available from NASA GHRC DAAC
- **Same coverage as GOES-19** (both at 75.2°W)
- Will NOT solve southern Brazil coverage

### GOES-17 (Decommissioned 2024)
- Was at 137.2°W before GOES-18
- Poor Brazil coverage (too far west)

## Recommendation:

**Option 1: Accept Limitation**
- Document that lightning covers only northern/central Brazil (lat > -15°)
- Use current GOES-19 data
- Fast, no changes needed

**Option 2: Try GOES-16 Historical**
- Check if older GOES-16 position had better coverage
- Requires downloading historical data
- Likely same coverage (same orbit)

**Option 3: Use Ground-Based Lightning Networks**
- BrasilDAT (Brazilian lightning detection network)
- Better Brazil coverage
- Different data source/format
- May require commercial license

**Option 4: Combine with Other Datasets**
- Use GLM for northern Brazil
- Use ground-based for southern Brazil
- More complex integration

Which option would you prefer?
