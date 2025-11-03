# GLM Flash Extent Density - 30-Minute Maximum Window

## 🌩️ What We Store

Instead of daily sums, we store the **maximum 30-minute lightning window** per day per grid cell.

### Why 30-Minute Windows?

1. **Storm Intensity**: Peak 30-min window better represents severe storm activity
2. **Actionable Alerts**: More useful for warnings than daily totals
3. **Temporal Context**: Also stores WHEN the peak occurred
4. **Compact Storage**: Still only 1 value per day (~2 GB total for 2020-2025)

## 📊 Data Variables

Each day contains TWO variables per grid cell:

1. **`fed_30min_max`**: Maximum flash extent density in any 30-minute window
   - Units: Total flashes in 30 minutes
   - Type: float32

2. **`fed_30min_time`**: Timestamp when the maximum occurred
   - Type: datetime64
   - Example: "2020-01-15 14:30:00" (peak was at 2:30 PM)

## 🔢 Example

**Location**: São Paulo (-23.5°, -46.6°)
**Date**: 2020-01-15

**Minute-level data** (1440 values):
```
00:00 - 00:01: 2 flashes
00:01 - 00:02: 1 flash
...
14:15 - 14:16: 45 flashes  ← Start of intense period
14:16 - 14:17: 52 flashes
14:17 - 14:18: 48 flashes
...
14:44 - 14:45: 43 flashes  ← End of 30-min peak
14:45 - 14:46: 8 flashes
...
23:59 - 00:00: 0 flashes
```

**30-minute rolling windows**:
```
00:00-00:30: 15 flashes total
00:01-00:31: 14 flashes total
...
14:15-14:45: 1,247 flashes total  ← MAXIMUM
14:16-14:46: 1,203 flashes total
...
23:30-00:00: 3 flashes total
```

**What we store**:
```
fed_30min_max: 1247.0 flashes
fed_30min_time: 2020-01-15T14:15:00
```

## 💾 Storage Comparison

**Daily Sum (old approach)**:
- Variable: `flash_extent_density`
- Value: Sum of all 1440 minutes
- Example: 8,432 flashes per day
- **Problem**: Doesn't show intensity, just volume

**30-Min Max (new approach)**:
- Variables: `fed_30min_max` + `fed_30min_time`
- Values: 1,247 flashes (peak) at 14:15
- Example: Peak intensity at specific time
- **Advantage**: Shows when and how intense

## 📈 Storage Requirements

**Per Day:**
- 583 × 569 grid cells
- 2 variables per cell (value + timestamp)
- ~1.3 MB uncompressed → **~400 KB compressed**

**Full Dataset (2020-2025):**
- 2,128 days × 0.4 MB = **~850 MB - 1 GB**
- Plus GeoTIFFs: ~1 GB
- **Total: ~2 GB** ✅

## 🔍 API Response Examples

### History Query
```python
response = requests.post("http://localhost:8000/lightning/history", json={
    "lat": -23.5,
    "lon": -46.6,
    "start_date": "2020-01-01",
    "end_date": "2020-01-15"
})

# Returns maximum 30-min window per day
{
  "lat": -23.5,
  "lon": -46.6,
  "history": {
    "2020-01-01": 342.5,  # Max 30-min window on Jan 1
    "2020-01-02": 128.3,  # Max 30-min window on Jan 2
    "2020-01-03": 892.1,  # Severe storm day!
    ...
  }
}
```

### Trigger Query
```python
response = requests.post("http://localhost:8000/lightning/triggers", json={
    "lat": -23.5,
    "lon": -46.6,
    "start_date": "2020-01-01",
    "end_date": "2020-12-31",
    "trigger": 500.0,  # Days with 500+ flashes in any 30-min window
    "trigger_type": "above"
})

# Returns days where peak 30-min window exceeded threshold
{
  "trigger": 500.0,
  "trigger_type": "above",
  "n_exceedances": 23,  # 23 days had severe lightning
  "exceedances": [
    {"date": "2020-01-03", "value": 892.1},
    {"date": "2020-01-15", "value": 1247.0},
    ...
  ]
}
```

## 🎯 Use Cases

### 1. Severe Storm Detection
Find days with intense lightning bursts:
```python
# Days with >1000 flashes in 30 minutes = severe thunderstorms
trigger: 1000.0
```

### 2. Lightning Risk Assessment
Identify moderate vs. severe activity:
```python
# 100-500: Moderate
# 500-1000: High
# >1000: Severe
```

### 3. Storm Timing Analysis
Query `fed_30min_time` to see when storms peaked:
```python
# Most storms peak between 14:00-18:00 local time
```

## 🚀 Processing Details

**Download & Process:**
1. Download 1,440 minute files (~2-4 GB)
2. Load into time series (1440 time steps)
3. Calculate rolling 30-minute sum
4. Find maximum per grid cell
5. Store max value + timestamp
6. **Delete raw files** (save disk space)

**Processing Time:**
- ~5-10 minutes per day
- ~150-350 hours total for 2020-2025

## 📝 Technical Notes

- **Rolling window**: Uses `xarray.rolling(time=30).sum()`
- **Maximum**: Uses `.max(dim='time')` and `.argmax(dim='time')`
- **Compression**: 5:1 ratio with zlib level 5
- **Chunking**: time=-1, lat=20, lon=20 for fast queries

## 🎉 Benefits

✅ **Better storm characterization**: Peak intensity > daily sum
✅ **Temporal information**: Know WHEN the storm peaked
✅ **Compact storage**: Still only ~2 GB total
✅ **Faster queries**: Same performance as daily sum
✅ **More actionable**: Better for alerts and warnings

## 🔄 Migration from Daily Sum

If you already have daily sum data:
1. The new approach is **incompatible** with old format
2. Variable names changed: `flash_extent_density` → `fed_30min_max`
3. Need to **re-download and reprocess** all data
4. Update any custom scripts to use new variable names

---

**Ready to download?** See the main `GLM_FED_README.md` for setup instructions!
