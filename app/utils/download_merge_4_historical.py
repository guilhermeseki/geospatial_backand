import os
import xarray as xr
from dask.distributed import Client, LocalCluster
import fsspec
from datetime import datetime, timedelta
from tqdm import tqdm

# -------------------------
# USER CONFIGURATION
# -------------------------
OUTPUT_DIR = "/mnt/workwork/geoserver_data/merge_historical"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = "https://ftp.cptec.inpe.br/modelos/tempo/MERGE/GPM/DAILY"
START_YEAR = 2015
END_YEAR = datetime.now().year

bbox = (-74.97500610351562, -34.974998474121094, -34.02500915527344, 4.974998474121094)
lon_min, lat_min, lon_max, lat_max = bbox

MAX_CORES = 4

# -------------------------
# DASK SETUP
# -------------------------
cluster = LocalCluster(
    n_workers=MAX_CORES,
    threads_per_worker=1,
    processes=True,
    memory_limit="8GB"
)
client = Client(cluster)
print("✅ Dask client running:", client)

# -------------------------
# FUNCTION TO PROCESS A YEAR
# -------------------------
def convert_longitudes(ds):
    ds = ds.assign_coords(
        longitude=(((ds.longitude + 180) % 360) - 180)
    )
    ds = ds.sortby("longitude")
    return ds

def process_year(year: int):
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    delta = timedelta(days=1)

    temp_dir = os.path.join(OUTPUT_DIR, f"temp_{year}")
    os.makedirs(temp_dir, exist_ok=True)

    datasets = []

    for i in tqdm(range((end_date - start_date).days + 1), desc=f"📦 Processing {year}"):
        date = start_date + i * delta
        ymd = date.strftime("%Y%m%d")
        month = date.month
        url = f"{BASE_URL}/{year}/{month:02d}/MERGE_CPTEC_{ymd}.grib2"

        local_path = os.path.join(temp_dir, f"MERGE_CPTEC_{ymd}.grib2")

        # Download file if it doesn't exist
        if not os.path.exists(local_path):
            try:
                fs = fsspec.open(url).fs
                fs.get(url, local_path)
            except Exception:
                continue  # Skip missing files

        # Open and crop
        try:
            ds = xr.open_dataset(
                local_path,
                engine="cfgrib",
                backend_kwargs={"filter_by_keys": {"typeOfLevel": "surface"}},
                decode_times=True,
                chunks={"latitude": 100, "longitude": 100},
                decode_timedelta=True
            )
            ds = convert_longitudes(ds)

            # --- MODIFICATION START ---
            # Rename 'rdp' to 'precip'
            if 'rdp' in ds.data_vars:
                ds = ds.rename({'rdp': 'precip'})
            
            # Delete 'prmsl' if it exists
            if 'prmsl' in ds.data_vars:
                ds = ds.drop_vars('prmsl')
            # --- MODIFICATION END ---
            
            ds = ds.sel(
                longitude=slice(lon_min, lon_max),
                latitude=slice(lat_min, lat_max)
            )
            ds = ds.expand_dims(time=[date])
            datasets.append(ds)
        except Exception:
            continue

    if not datasets:
        print(f"⚠️ No data found for {year}")
        return

    try:
        ds_year = xr.concat(datasets, dim="time")
        out_path = os.path.join(OUTPUT_DIR, f"brazil_merge_{year}.nc")
        print(f"💾 Saving {out_path} ...")
        # Ensure to compute the data before saving if it's large and you want to trigger Dask
        # If it's small, to_netcdf with dask chunks will work, but for large data, 
        # it might be better to use compute() or a specific Dask function.
        # For simplicity, keeping the original to_netcdf call:
        ds_year.to_netcdf(out_path, engine="netcdf4")
        ds_year.close()
    except Exception as e:
        print(f"❌ Failed to merge year {year}: {e}")

    # Cleanup temp files
    # for f in os.listdir(temp_dir):
    #     os.remove(os.path.join(temp_dir, f))
    # os.rmdir(temp_dir)
    # print(f"🗑 Deleted temp files for {year}")


# -------------------------
# MAIN LOOP
# -------------------------
if __name__ == "__main__":
    for year in range(START_YEAR, END_YEAR + 1):
        process_year(year)

    print("🎉 All done!")