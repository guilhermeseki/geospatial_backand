# app/utils/polygon.py
"""
Polygon utilities for processing climate data with polygon boundaries.
Variable is determined by the route/endpoint, not the request.
"""
import logging
import numpy as np
import xarray as xr
from shapely.geometry import Polygon
import geopandas as gpd
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class PolygonProcessor:
    """Process climate data within polygon boundaries."""
    
    @staticmethod
    def create_polygon_from_coords(coordinates) -> Polygon:
        """Create Shapely Polygon from coordinate list."""
        polygon = Polygon(coordinates)
        
        if not polygon.is_valid:
            raise ValueError("Invalid polygon: may be self-intersecting or malformed")
        
        return polygon
    
    @staticmethod
    def calculate_polygon_area_km2(polygon: Polygon) -> float:
        """Calculate polygon area in km² using geodesic projection."""
        gdf = gpd.GeoDataFrame([1], geometry=[polygon], crs="EPSG:4326")
        gdf_projected = gdf.to_crs("EPSG:6933")  # Cylindrical Equal Area
        area_m2 = gdf_projected.geometry.area.iloc[0]
        return area_m2 / 1_000_000
    
    @staticmethod
    def get_polygon_bounds(polygon: Polygon) -> Tuple[float, float, float, float]:
        """Get bounding box (min_lon, min_lat, max_lon, max_lat)."""
        return polygon.bounds
    
    @staticmethod
    def create_polygon_mask(ds_slice: xr.Dataset, 
                           polygon: Polygon,
                           lat_dim: str = "latitude",
                           lon_dim: str = "longitude") -> xr.DataArray:
        """Create boolean mask for points within polygon."""
        lons = ds_slice[lon_dim].values
        lats = ds_slice[lat_dim].values
        
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        lon_flat = lon_grid.flatten()
        lat_flat = lat_grid.flatten()
        
        # Vectorized point-in-polygon
        from shapely.vectorized import contains
        points = np.column_stack([lon_flat, lat_flat])
        mask_flat = contains(polygon, points[:, 0], points[:, 1])
        mask_grid = mask_flat.reshape(lon_grid.shape)
        
        mask_da = xr.DataArray(
            mask_grid,
            coords={lat_dim: ds_slice[lat_dim], lon_dim: ds_slice[lon_dim]},
            dims=[lat_dim, lon_dim]
        )
        
        return mask_da
    
    @staticmethod
    def crop_dataset_by_polygon(ds: xr.Dataset,
                                polygon: Polygon,
                                lat_dim: str = "latitude",
                                lon_dim: str = "longitude",
                                time_dim: str = "time",
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> xr.Dataset:
        """Crop dataset to polygon bounds and apply mask."""
        # Get bounds and slice
        lon_min, lat_min, lon_max, lat_max = polygon.bounds

        # FIX: Handle both ascending and descending latitude coordinates
        # xarray slice requires bounds to match coordinate order
        lat_coords = ds[lat_dim].values
        lat_ascending = lat_coords[0] < lat_coords[-1]

        if lat_ascending:
            lat_slice = slice(lat_min, lat_max)
        else:
            # Descending order (e.g., CHIRPS): swap min/max
            lat_slice = slice(lat_max, lat_min)

        ds_slice = ds.sel(
            **{lat_dim: lat_slice,
               lon_dim: slice(lon_min, lon_max)}
        )
        
        # Add time slicing
        if start_date and end_date:
            ds_slice = ds_slice.sel(**{time_dim: slice(start_date, end_date)})
        
        # Apply polygon mask
        polygon_mask = PolygonProcessor.create_polygon_mask(
            ds_slice, polygon, lat_dim, lon_dim
        )
        
        ds_masked = ds_slice.where(polygon_mask)
        
        return ds_masked
    
    @staticmethod
    def calculate_polygon_statistics(data: xr.DataArray,
                                    statistic: str = "mean",
                                    spatial_dims: Tuple[str, str] = ("latitude", "longitude")) -> xr.DataArray:
        """
        Calculate spatial statistics over polygon area.
        Supports: mean, sum, max, min, std, median, and percentiles (pctl_XX).
        """
        # Handle percentiles
        if statistic.startswith('pctl_'):
            try:
                percentile = int(statistic.split('_')[1])
                return data.quantile(percentile / 100.0, dim=spatial_dims)
            except (IndexError, ValueError):
                raise ValueError(f"Invalid percentile format: {statistic}. Use 'pctl_XX' (e.g., pctl_50)")
        
        # Standard statistics
        stat_funcs = {
            'mean': lambda x: x.mean(dim=spatial_dims),
            'sum': lambda x: x.sum(dim=spatial_dims),
            'max': lambda x: x.max(dim=spatial_dims),
            'min': lambda x: x.min(dim=spatial_dims),
            'std': lambda x: x.std(dim=spatial_dims),
            'median': lambda x: x.median(dim=spatial_dims)
        }
        
        if statistic not in stat_funcs:
            raise ValueError(f"Unsupported statistic: {statistic}")
        
        return stat_funcs[statistic](data)
    
    @staticmethod
    def process_polygon_request(ds: xr.Dataset,
                               polygon: Polygon,
                               variable_name: str,
                               start_date: str,
                               end_date: str,
                               statistic: Optional[str] = None,
                               trigger: Optional[float] = None,
                               consecutive_days: Optional[int] = 1,
                               lat_dim: str = "latitude",
                               lon_dim: str = "longitude",
                               time_dim: str = "time") -> dict:
        """
        Process a complete polygon request.

        Args:
            ds: xarray Dataset
            polygon: Shapely Polygon
            variable_name: Variable to process (e.g., "precip", "t2m_max")
            start_date: Start date string
            end_date: End date string
            statistic: Optional statistic to calculate
            trigger: Optional trigger threshold
            consecutive_days: Minimum consecutive days for trigger (default=1)

        Returns:
            dict with results
        """
        import pandas as pd
        
        # Crop dataset
        ds_cropped = PolygonProcessor.crop_dataset_by_polygon(
            ds, polygon, lat_dim, lon_dim, time_dim, start_date, end_date
        )
        
        data = ds_cropped[variable_name]
        
        # Calculate metadata
        area_km2 = PolygonProcessor.calculate_polygon_area_km2(polygon)
        bounds = PolygonProcessor.get_polygon_bounds(polygon)
        
        result = {
            "metadata": {
                "polygon_area_km2": round(area_km2, 2),
                "bounds": {
                    "min_lon": bounds[0],
                    "min_lat": bounds[1],
                    "max_lon": bounds[2],
                    "max_lat": bounds[3]
                },
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
        # If trigger is provided, find exceedances
        if trigger is not None:
            trigger_mask = data > trigger
            exceeding_values = data.where(trigger_mask)
            exceeding_flat = exceeding_values.stack(
                point=[time_dim, lat_dim, lon_dim]
            )
            exceeding_computed = exceeding_flat.compute().to_series().dropna()

            # Apply consecutive days filter if requested
            if consecutive_days and consecutive_days > 1:
                from collections import defaultdict

                # Reorganize by (lat, lon) to check consecutive dates
                points_by_location = defaultdict(list)
                for index, value in exceeding_computed.items():
                    time_val, lat_val, lon_val = index
                    date_val = pd.to_datetime(time_val).date()
                    points_by_location[(lat_val, lon_val)].append((date_val, value))

                # Filter points that meet consecutive day requirement
                valid_points = {}
                for (lat_val, lon_val), date_values in points_by_location.items():
                    # Sort by date
                    date_values.sort(key=lambda x: x[0])
                    dates = [dv[0] for dv in date_values]

                    # Find consecutive sequences
                    consecutive_count = 1
                    for i in range(1, len(dates)):
                        if (dates[i] - dates[i-1]).days == 1:
                            consecutive_count += 1
                            if consecutive_count >= consecutive_days:
                                # This location meets the requirement
                                # Include all dates in the consecutive sequence
                                for j in range(i - consecutive_count + 1, i + 1):
                                    key = (dates[j], lat_val, lon_val)
                                    valid_points[key] = date_values[j][1]
                        else:
                            consecutive_count = 1

                # Rebuild exceeding_computed with only valid points
                exceeding_computed_filtered = pd.Series(valid_points)
            else:
                exceeding_computed_filtered = exceeding_computed

            grouped_exceedances = {}
            for index, value in exceeding_computed_filtered.items():
                if consecutive_days and consecutive_days > 1:
                    date_val, lat_val, lon_val = index
                    date_str = str(date_val)
                else:
                    time_val, lat_val, lon_val = index
                    date_str = str(pd.to_datetime(time_val).date())

                point_data = {
                    "latitude": round(float(lat_val), 5),
                    "longitude": round(float(lon_val), 5),
                    f"{variable_name}_value": round(float(value), 2)
                }

                if date_str not in grouped_exceedances:
                    grouped_exceedances[date_str] = []
                grouped_exceedances[date_str].append(point_data)

            result["trigger_dates"] = grouped_exceedances
            result["num_trigger_dates"] = len(grouped_exceedances)
            result["metadata"]["trigger"] = trigger

            if consecutive_days and consecutive_days > 1:
                result["metadata"]["consecutive_days"] = consecutive_days
        
        # If statistic is provided, calculate it
        if statistic is not None:
            stat_result = PolygonProcessor.calculate_polygon_statistics(
                data, statistic=statistic
            )
            stat_computed = stat_result.compute()
            
            time_series = []
            for time_val, value in stat_computed.to_series().items():
                if pd.notna(value):
                    time_series.append({
                        "date": str(pd.to_datetime(time_val).date()),
                        "value": round(float(value), 2)
                    })
            
            result["time_series"] = time_series
            result["num_records"] = len(time_series)
            result["metadata"]["statistic"] = statistic
        
        return result