import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.services.geoserver import GeoServerService
from app.config.settings import get_settings
import xarray as xr
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
import matplotlib
import geopandas as gpd
from io import BytesIO
import os

router = APIRouter(prefix="/georisk", tags=["georisk Maps"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()

@router.get("/cmaps")
async def generate_cmap(
    bounds: str = Query("1,10,20,30,40,60,80,100,150,200,300,400,600", description="Comma-separated colorbar bounds"),
    colors: str = Query(None, description="Comma-separated list of hex colors (e.g., FFFFFF,E8C2AA or #FFFFFF,#E8C2AA)"),
    format: str = Query("png", description="Output format (png)")
):
    try:
        # Parse comma-separated bounds
        try:
            bounds_list = [float(x) for x in bounds.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bounds format; use comma-separated numbers")

        # Default colors if none provided, parse comma-separated colors
        if colors:
            colors_list = [x.strip() for x in colors.split(",")]
            # Ensure each color starts with '#'
            colors_list = ['#' + c if not c.startswith('#') else c for c in colors_list]
        else:
            colors_list = [
                "#FFFFFF", "#E8C2AA", "#FF11FF", "#FF79FF", "#A37AFF",
                "#0036D0", "#114FFF", "#20E2FC", "#D5D5D5", "#8CE89B",
                "#BEFFBF", "#E1FFE1"
            ]
        
        # Reverse colors to invert colorbar
        #colors_list = colors_list[::-1]  # #E1FFE1 for 1-10, #BEFFBF for 10-20, etc.
        
        # Add transparent color for values below 1
        colors_list = ['#00000000'] + colors_list  # Prepend transparent color (8-digit hex for RGBA)
        bounds_list = [0] + bounds_list  # Prepend 0 to bounds for transparency
        
        # Validate colors and bounds
        if len(colors_list) < len(bounds_list) - 1:
            raise HTTPException(status_code=400, detail="Number of colors must be at least bounds-1")
        
        # Validate hex color format (skip transparent color)
        for c in colors_list[1:]:
            if not (len(c) == 7 and c.startswith('#') and all(ch in '0123456789ABCDEFabcdef' for ch in c[1:])):
                raise HTTPException(status_code=400, detail=f"Invalid hex color format: {c}")

        cmap = ListedColormap(colors_list)
        norm = matplotlib.colors.BoundaryNorm(bounds_list, cmap.N, clip=False)  # Allow values <1 to be transparent

        # Fixed file list with directory path
        data_dir = "/mnt/workwork/GeoRisk/data"
        file_list = [
            os.path.join(data_dir, 'MERGE_CPTEC_20240427.grib2'),
            os.path.join(data_dir, 'MERGE_CPTEC_20240428.grib2'),
            os.path.join(data_dir, 'MERGE_CPTEC_20240429.grib2'),
            os.path.join(data_dir, 'MERGE_CPTEC_20240501.grib2'),
            os.path.join(data_dir, 'MERGE_CPTEC_20240502.grib2'),
            os.path.join(data_dir, 'MERGE_CPTEC_20240503.grib2'),
            os.path.join(data_dir, 'MERGE_CPTEC_20240504.grib2'),
            os.path.join(data_dir, 'MERGE_CPTEC_20240505.grib2')
        ]

        # Check if files exist
        for file in file_list:
            if not os.path.exists(file):
                logger.error(f"File not found: {file}")
                raise HTTPException(status_code=400, detail=f"File not found: {file}")

        # Load Brazil borders from shapefile
        shapefile_path = "/opt/geospatial_backend/data/shapefiles/BR_Pais_2024/BR_Pais_2024.shp"
        if not os.path.exists(shapefile_path):
            logger.error(f"Shapefile not found: {shapefile_path}")
            raise HTTPException(status_code=400, detail=f"Shapefile not found: {shapefile_path}")
        brazil = gpd.read_file(shapefile_path)
        if brazil.empty:
            raise HTTPException(status_code=400, detail="Brazil shapefile is empty")

        # Open and sum precipitation data from local files
        ds = xr.open_mfdataset(file_list, combine='nested', concat_dim="time", engine="cfgrib")
        if 'rdp' not in ds:
            raise HTTPException(status_code=400, detail="Variable 'rdp' not found in dataset")
        
        # Normalize longitude to [-180, 180]
        ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180)).sortby('longitude')
        
        # Log coordinate ranges for debugging
        logger.info(f"Longitude range: {ds['longitude'].min().item()} to {ds['longitude'].max().item()}")
        logger.info(f"Latitude range: {ds['latitude'].min().item()} to {ds['latitude'].max().item()}")
        
        total_precip = ds['rdp'].sum(dim="time")
        lons = ds['longitude'].values
        lats = ds['latitude'].values
        lon_min, lon_max = float(lons.min()), float(lons.max())
        lat_min, lat_max = float(lats.min()), float(lats.max())

        # Plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot precipitation data first
        im = ax.pcolormesh(lons, lats, total_precip, cmap=cmap, norm=norm, zorder=1)
        
        # Plot Brazil borders on top
        brazil.plot(ax=ax, edgecolor='black', facecolor='none', linewidth=1, zorder=2)
        
        cbar = plt.colorbar(im, ax=ax, boundaries=bounds_list[1:], ticks=bounds_list[1:], shrink=0.7)  # Skip 0 for colorbar
        cbar.set_label('Precipitation (mm)')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)

        # Save to BytesIO for PNG response
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        img_buffer.seek(0)

        return StreamingResponse(img_buffer, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating map: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
