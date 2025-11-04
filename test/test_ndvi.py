import os
from pathlib import Path
import xarray as xr

os.chdir('/mnt/workwork/geoserver_data')
ndvi_dir = Path('ndvi_modis_hist')

ds = xr.open_dataset(ndvi_dir / 'ndvi_modis_2024.nc')
print(ds)
