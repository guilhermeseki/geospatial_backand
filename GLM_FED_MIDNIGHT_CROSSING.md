# GLM FED: Midnight-Crossing 30-Minute Windows

## 🌙 The Problem with Day Boundaries

**Naive Approach (wrong):**
- Reset windows at midnight (00:00)
- Windows: 00:00-00:30, 00:01-00:31, ..., 23:30-00:00
- **Problem**: Window from 23:40-00:10 is split across two days!

**Correct Approach (implemented):**
- Windows roll continuously across midnight
- Window assignment: belongs to the day when it **ENDS**
- Window 23:40 Oct 20 → 00:10 Oct 21 belongs to **Oct 21**

## 📊 How It Works

### Data Downloaded Per Day

For **target date D** (e.g., Oct 21):

**Download:**
- Previous day (D-1) from 23:31 to 23:59 → 29 minutes
- Target day (D) from 00:00 to 23:59 → 1,440 minutes
- **Total: 1,469 minutes**

### Window Calculation

**Time series:** D-1 23:31, 23:32, ..., 23:59, D 00:00, 00:01, ..., 23:59

**Rolling 30-min windows:**
```
Window ending at D-1 23:59: [D-1 23:30 to D-1 23:59]  ← Belongs to D-1
Window ending at D 00:00:   [D-1 23:31 to D 00:00]    ← Belongs to D ✓
Window ending at D 00:01:   [D-1 23:32 to D 00:01]    ← Belongs to D ✓
...
Window ending at D 23:59:   [D 23:30 to D 23:59]      ← Belongs to D ✓
```

**Keep only windows ending on day D** (00:00 to 23:59)
→ **1,440 windows per day**

### Maximum Selection

For each grid cell:
1. Calculate all 1,440 rolling windows ending on day D
2. Find the window with **maximum flash count**
3. Store:
   - `fed_30min_max`: Maximum flash count
   - `fed_30min_time`: Timestamp when max occurred

## 🕐 Example

**Date**: October 21, 2020
**Location**: São Paulo (-23.5°, -46.6°)

**Minute Data:**
```
Oct 20 23:40 → 23:59: Low activity (10-15 flashes/min)
Oct 21 00:00 → 00:10: Intense storm! (80-100 flashes/min)
Oct 21 00:11 → 23:59: Moderate activity (20-30 flashes/min)
```

**30-Min Windows:**
```
Oct 20 23:59 window: 300 flashes
Oct 21 00:00 window: 450 flashes  ← Storm starting!
Oct 21 00:01 window: 520 flashes
...
Oct 21 00:10 window: 1,247 flashes  ← MAXIMUM! Peak of storm
Oct 21 00:11 window: 1,180 flashes  ← Storm fading
...
Oct 21 14:30 window: 680 flashes
...
Oct 21 23:59 window: 250 flashes
```

**What We Store for Oct 21:**
```
fed_30min_max: 1,247 flashes
fed_30min_time: 2020-10-21T00:10:00
```

**Interpretation:**
- The most intense 30-minute storm on Oct 21 peaked at 00:10 AM
- This window included data from Oct 20 23:41 to Oct 21 00:10
- The storm ENDED on Oct 21, so it belongs to Oct 21 ✓

## 🎯 Why This Matters

### Case Study: Severe Thunderstorm

**Scenario:**
- Storm develops late Oct 20 evening
- Peak intensity: 23:45-00:15 (crosses midnight)
- Dissipates by 01:00 Oct 21

**Naive approach (wrong):**
- Oct 20: Window 23:30-23:59 shows partial storm
- Oct 21: Window 00:00-00:29 shows partial storm
- Neither day shows the **true peak intensity**!

**Correct approach (ours):**
- Oct 21: Window 00:00-00:29 includes data from 23:31-00:00
- Oct 21: Window 00:15-00:44 captures the FULL peak
- Shows the **complete storm intensity** ✓

## 📈 Storage & Performance

**Download Size:**
- Extra 29 minutes per day = 29/1440 = **+2% overhead**
- Negligible impact on total download size

**Processing Time:**
- Loading 1,469 instead of 1,440 files = **+2% time**
- Rolling window calculation unchanged
- Filtering step is fast

**Final Storage:**
- Still only 1 value per day per grid cell
- No increase in final storage size

## 🔍 Technical Details

### Window Assignment Logic

```python
# For target_date D:
target_start = pd.Timestamp(D)              # 00:00:00
target_end = target_start + pd.Timedelta(days=1)  # Next day 00:00:00

# Calculate all rolling windows across full time series
rolling_30min = time_series.rolling(time=30).sum()

# Keep only windows where END time is on day D
rolling_target_day = rolling_30min.sel(
    time=slice(target_start, target_end - pd.Timedelta(seconds=1))
)

# Find maximum among these 1,440 windows
max_30min = rolling_target_day.max(dim='time')
```

### Edge Cases

**First day of dataset (e.g., 2020-01-01):**
- No previous day data available
- First 29 windows (00:00-00:28) are incomplete
- Still usable, just slightly less data

**Missing previous day data:**
- If D-1 files unavailable, proceed with D only
- Log warning about incomplete windows
- Better to have 98% of data than fail completely

## ✅ Benefits

1. **Accurate storm characterization**: Captures storms that cross midnight
2. **No arbitrary splits**: Storm intensity not divided by day boundaries
3. **Continuous time series**: Windows roll naturally without resets
4. **Scientifically correct**: Matches how meteorologists analyze storms
5. **Minimal overhead**: Only 2% extra download/processing

## 🎉 Summary

✓ Windows cross midnight boundaries naturally
✓ Window belongs to day when it ENDS
✓ Captures full storm intensity regardless of timing
✓ Only 2% overhead in download/processing
✓ Same final storage size (1 value per day)
✓ Scientifically accurate and meteorologically meaningful

---

This approach ensures that a severe thunderstorm peaking at midnight is properly captured and attributed to the correct day, rather than being artificially split across two days.
