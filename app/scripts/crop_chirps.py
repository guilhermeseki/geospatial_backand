import pandas as pd
import xarray as xr
from pathlib import Path
from dask.distributed import Client, LocalCluster
from dask.diagnostics import ProgressBar
import multiprocessing
import logging

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

# Define paths
data_dir = Path("/media/guilherme/Novo volume/CHIRPS")
output_dir = Path('/mnt/workwork/Howden/Usinas_hidreletricas')
output_dir.mkdir(exist_ok=True)

# Brazil bounding box (latitude: -35 to 5, longitude: -75 to -34)
BRAZIL_BBOX = {
    'latitude': slice(-35, 5),
    'longitude': slice(-75, -34)
}

# Time range
START_YEAR = 2025
END_YEAR = 2025
YEARS = range(START_YEAR, END_YEAR + 1)

# Preprocess CHIRPS files
def preprocess_chirps(ds):
    """Standardizes coordinates, ensures float32, and drops nulls."""
    if "lat" in ds.dims:
        ds = ds.rename({"lat": "latitude", "lon": "longitude"})
    
    # Ensure time is decoded to datetime64
    if not ds.time.dtype.kind.startswith("M"):
        ds = xr.decode_cf(ds)

    ds['precip'] = ds['precip'].astype('float32')  # Ensure float32
    return ds[['precip']].dropna(dim='time', how='all')

# Main processing function
import gc

def crop_chirps_to_brazil_by_year(data_dir, output_dir, years, bbox):
    for year in years:
        input_file = data_dir / f"chirps-v2.0.{year}.days_p05.nc"
        output_netcdf = output_dir / f"brazil_chirps_{year}.nc"
        print(f"Cropping: {output_netcdf}")

        if not input_file.exists():
            logging.warning(f"File {input_file} not found. Skipping year {year}.")
            continue

        try:
            ds = xr.open_dataset(input_file)

            ds = preprocess_chirps(ds)
            ds_cropped = ds.sel(**bbox)

            encoding = {
                'precip': {
                    'zlib': True,
                    'complevel': 4,
                    'shuffle': True,
                    'chunksizes': (ds_cropped.time.size, 100, 100)
                }
            }

            # Write directly without `.compute()`
            ds_cropped.to_netcdf(
                output_netcdf,
                encoding=encoding,
                engine="netcdf4",
                format="NETCDF4"
            )

            file_size_mb = output_netcdf.stat().st_size / 1024**2
            logging.info(f"Saved {output_netcdf}, size: {file_size_mb:.2f} MB")

        except Exception as e:
            logging.error(f"Error processing year {year}: {e}")

        finally:
            # Explicitly cleanup memory
            del ds, ds_cropped
            gc.collect()


# Run processing
try:
    crop_chirps_to_brazil_by_year(
        data_dir=data_dir,
        output_dir=output_dir,
        years=YEARS,
        bbox=BRAZIL_BBOX
    )
except Exception as e:
    logging.error(f"Processing failed: {e}")
finally:
    # Close Dask client
    client.close()
    cluster.close()