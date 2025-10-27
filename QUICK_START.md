# Quick Start Guide - Yearly Historical Architecture

## TL;DR

Your geospatial backend now uses **yearly historical files** (easier to manage!) and all **NetCDF writes are FUSE-safe** (no more corruption!).

## Run This Now

```bash
cd /opt/geospatial_backend

# 1. Clean up any FUSE issues
./cleanup_fuse_issues.sh

# 2. Test ERA5 with small batch
python test_era5_fix.py

# 3. If test passes, run full ERA5 flow
python app/run_era5.py

# 4. Verify yearly files were created
python test_yearly_loading.py

# 5. Restart your API
pkill -f "uvicorn main:app"
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## What Changed?

### Before
```
temp_max_hist/
  └── historical.nc  # ❌ One huge file, gets corrupted on FUSE
```

### After
```
temp_max_hist/
  ├── temp_max_2024.nc  # ✅ One file per year, FUSE-safe writes
  └── temp_max_2025.nc  # ✅ Easy to manage
```

## Key Benefits

✅ No more file corruption (FUSE-safe writes)
✅ Smaller, manageable files (~150MB/year vs 10+GB total)
✅ Faster updates (only modify current year)
✅ **API code unchanged** - works exactly the same!

## Migration Checklist

- [ ] **Step 1**: Run cleanup script
  ```bash
  ./cleanup_fuse_issues.sh
  ```

- [ ] **Step 2**: Test ERA5 (creates yearly files automatically)
  ```bash
  python app/run_era5.py
  ```

- [ ] **Step 3**: Verify files load
  ```bash
  python test_yearly_loading.py
  ```

- [ ] **Step 4**: (Optional) Migrate existing ERA5 data
  ```bash
  python migrate_era5_to_yearly.py
  rm /mnt/workwork/geoserver_data/temp_*_hist/historical.nc
  ```

- [ ] **Step 5**: (Later) Migrate precipitation
  ```bash
  # Rename directories
  mv /mnt/workwork/geoserver_data/chirps_historical /mnt/workwork/geoserver_data/chirps_hist
  mv /mnt/workwork/geoserver_data/merge_historical /mnt/workwork/geoserver_data/merge_hist

  # Rename files
  cd /mnt/workwork/geoserver_data/chirps_hist
  for f in brazil_chirps_*.nc; do mv "$f" "${f/brazil_chirps_/chirps_}"; done

  cd /mnt/workwork/geoserver_data/merge_hist
  for f in brazil_merge_*.nc; do mv "$f" "${f/brazil_merge_/merge_}"; done
  ```

## Expected Directory Structure

After migration, you should have:

```
/mnt/workwork/geoserver_data/
├── chirps/                    # Daily GeoTIFFs for GeoServer
│   └── chirps_20241024.tif
├── chirps_hist/               # Yearly historical for API
│   ├── chirps_2024.nc
│   └── chirps_2025.nc
├── temp_max/                  # Daily GeoTIFFs
│   └── temp_max_20241024.tif
├── temp_max_hist/             # Yearly historical
│   ├── temp_max_2024.nc
│   └── temp_max_2025.nc
└── ... (same for merge, temp_min, temp, ndvi)
```

## Testing

### Test API Endpoint

```bash
# Temperature history query
curl -X POST http://localhost:8000/temperature/history \
  -H "Content-Type: application/json" \
  -d '{
    "source": "temp_max",
    "start_date": "2024-10-01",
    "end_date": "2024-10-24",
    "lat": -15.8,
    "lon": -47.9
  }'
```

Should return data seamlessly from yearly files!

### Check Logs

Look for these messages in flow logs:
```
📦 Appending data from ... to yearly historical files
  📅 Processing year 2024 (10 dates)
    Writing to temp file...  # FUSE-safe write
    Copying to: temp_max_2024.nc
    ✓ Updated temp_max_2024.nc
```

## Troubleshooting

### No files found
**Run:** `python app/run_era5.py` to create them

### Files don't load
**Run:** `python test_yearly_loading.py` to diagnose

### API doesn't see data
**Restart:** `pkill -f uvicorn && python -m uvicorn app.api.main:app --reload`

### Still getting FUSE errors
**Check:** All `.py` files were updated (see FUSE_FIX_SUMMARY.md)

## Documentation

- **`IMPLEMENTATION_SUMMARY.md`** - What changed and why
- **`YEARLY_HISTORICAL_MIGRATION.md`** - Detailed migration steps
- **`UNIFIED_DATA_ARCHITECTURE.md`** - Complete architecture design
- **`FUSE_FIX_SUMMARY.md`** - FUSE filesystem fixes
- **`CLAUDE.md`** - Operational guide (updated)

## Need Help?

1. Check the logs for FUSE-safe write messages
2. Run `test_yearly_loading.py` to verify files
3. Review `IMPLEMENTATION_SUMMARY.md` for details
4. Check `CLAUDE.md` for operational guidance

## Summary

✅ **Run cleanup script**
✅ **Test ERA5 flow**
✅ **Verify loading works**
✅ **Restart API**
✅ **You're done!**

Everything else is automatic - the flows create yearly files, the API loads them seamlessly, and you have no more FUSE corruption issues! 🎉

---

**Quick Commands:**
```bash
# Cleanup
./cleanup_fuse_issues.sh

# Test
python test_era5_fix.py

# Run full flow
python app/run_era5.py

# Verify
python test_yearly_loading.py

# API
python -m uvicorn app.api.main:app --reload
```

Done! 🚀
