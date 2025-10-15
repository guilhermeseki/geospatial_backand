import pandas as pd
import xarray as xr
from pathlib import Path
from dask.distributed import Client, LocalCluster
from dask.diagnostics import ProgressBar
import multiprocessing
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename='/mnt/workwork/Howden/Usinas_hidreletricas/crop_log.txt',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Set up Dask client
n_cores = multiprocessing.cpu_count()
cluster = LocalCluster(n_workers=10, threads_per_worker=1, memory_limit='auto')
client = Client(cluster)
logging.info(f"Dask Client: {client}")
logging.info(f"Dashboard: {client.dashboard_link}")

# Enable progress bar
ProgressBar().register()

# Settings
base_dir = Path("/media/guilherme/Novo volume/MERGE/DAILY")
output_dir = Path("/media/guilherme/Novo volume/MERGE/DAILY")
output_dir.mkdir(parents=True, exist_ok=True)

years = sorted({p.name for p in base_dir.iterdir() if p.is_dir()})  # list of years

for year in years:
    print(f"Merging year {year}...")
    year_dir = base_dir / year
    files_to_merge = sorted(year_dir.glob("**/*.grib2"))

    if not files_to_merge:
        print(f"⚠️ No files found for year {year}")
        continue

    try:
        ds = xr.open_mfdataset(
            files_to_merge,
            engine="cfgrib",
            concat_dim="time",
            combine="nested",
            parallel=False
        )

        encoding = {
            'precip': {
                'zlib': True,
                'complevel': 4,
                'shuffle': True,
                'chunksizes': (ds.time.size, 100, 100)
            }
        }

        # Write directly without `.compute()`
        ds_cropped.to_netcdf(
            output_netcdf,
            encoding=encoding,
            engine="netcdf4",
            format="NETCDF4"
        )
        output_path = output_dir / f"MERGE_CPTEC_{year}.nc"
        print(f"Saving merged yearly file: {output_path}")
        ds.to_netcdf(output_path)
        ds.close()

    except Exception as e:
        print(f"❌ Failed to merge year {year}: {e}")
