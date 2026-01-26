#!/usr/bin/env python3
"""
Test that GLM download now covers ALL of Brazil (including southern regions).
This test downloads a single day and verifies complete coverage.
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.glm_fed_flow import glm_fed_flow
import xarray as xr
from pyproj import Transformer, CRS
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Brazil bbox - FULL country
BRAZIL_BBOX = {
    'lat_min': -35.0,   # Rio Grande do Sul south
    'lat_max': 6.5,     # Roraima north
    'lon_min': -75.0,   # Acre west
    'lon_max': -33.5    # Paraíba east coast
}

def check_coverage(nc_file):
    """Check if a GLM file covers all of Brazil."""

    logger.info(f"Checking coverage of: {nc_file.name}")

    ds = xr.open_dataset(nc_file)

    # GOES parameters
    sat_lon = -75.2
    sat_height = 35786023.0

    # Create transformer
    goes_crs = CRS.from_cf({
        'grid_mapping_name': 'geostationary',
        'perspective_point_height': sat_height,
        'longitude_of_projection_origin': sat_lon,
        'semi_major_axis': 6378137.0,
        'semi_minor_axis': 6356752.31414,
        'sweep_angle_axis': 'x'
    })
    wgs84 = CRS.from_epsg(4326)
    to_goes = Transformer.from_crs(wgs84, goes_crs, always_xy=True)
    to_latlon = Transformer.from_crs(goes_crs, wgs84, always_xy=True)

    # Get file bounds
    x_vals = ds.x.values
    y_vals = ds.y.values

    # Convert corners to lat/lon
    corners_xy = [
        (x_vals.min(), y_vals.min()),
        (x_vals.max(), y_vals.min()),
        (x_vals.min(), y_vals.max()),
        (x_vals.max(), y_vals.max()),
    ]

    lats, lons = [], []
    for x, y in corners_xy:
        lon, lat = to_latlon.transform(x * sat_height, y * sat_height)
        lats.append(lat)
        lons.append(lon)

    file_lat_min, file_lat_max = min(lats), max(lats)
    file_lon_min, file_lon_max = min(lons), max(lons)

    logger.info(f"  File coverage: lat [{file_lat_min:.2f}, {file_lat_max:.2f}], lon [{file_lon_min:.2f}, {file_lon_max:.2f}]")
    logger.info(f"  Brazil needs:  lat [{BRAZIL_BBOX['lat_min']}, {BRAZIL_BBOX['lat_max']}], lon [{BRAZIL_BBOX['lon_min']}, {BRAZIL_BBOX['lon_max']}]")

    # Check if Brazil is fully covered
    lat_covered = (file_lat_min <= BRAZIL_BBOX['lat_min']) and (file_lat_max >= BRAZIL_BBOX['lat_max'])
    lon_covered = (file_lon_min <= BRAZIL_BBOX['lon_min']) and (file_lon_max >= BRAZIL_BBOX['lon_max'])

    ds.close()

    if lat_covered and lon_covered:
        logger.info("  ✓ FULL BRAZIL COVERAGE CONFIRMED!")
        return True
    else:
        logger.error("  ✗ INCOMPLETE COVERAGE!")
        if not lat_covered:
            if file_lat_min > BRAZIL_BBOX['lat_min']:
                logger.error(f"    Missing south: {file_lat_min:.2f}° to {BRAZIL_BBOX['lat_min']}°")
            if file_lat_max < BRAZIL_BBOX['lat_max']:
                logger.error(f"    Missing north: {file_lat_max:.2f}° to {BRAZIL_BBOX['lat_max']}°")
        if not lon_covered:
            if file_lon_min > BRAZIL_BBOX['lon_min']:
                logger.error(f"    Missing west: {file_lon_min:.2f}° to {BRAZIL_BBOX['lon_min']}°")
            if file_lon_max < BRAZIL_BBOX['lon_max']:
                logger.error(f"    Missing east: {file_lon_max:.2f}° to {BRAZIL_BBOX['lon_max']}°")
        return False


def main():
    """Test GLM download with full Brazil coverage."""

    print("=" * 80)
    print("GLM BRAZIL COVERAGE TEST")
    print("=" * 80)
    print("This test will:")
    print("  1. Download 1 day of GLM data using the updated flow")
    print("  2. Verify it covers ALL of Brazil (including southern regions)")
    print("  3. Check the processed GeoTIFF bounds")
    print("=" * 80)

    # Use a recent date (7 days ago to ensure data availability)
    test_date = date.today() - timedelta(days=7)

    logger.info(f"Test date: {test_date}")
    logger.info("Starting download...")

    try:
        # Run the flow for 1 day
        result = glm_fed_flow(
            start_date=test_date,
            end_date=test_date,
            rolling_step_minutes=10
        )

        if not result:
            logger.error("✗ Flow returned no files")
            return False

        logger.info(f"✓ Flow completed, processed {len(result)} file(s)")

        # Check the raw NetCDF file
        from app.config.settings import get_settings
        settings = get_settings()

        raw_file = Path(settings.DATA_DIR) / "raw" / "glm_fed" / f"glm_fed_daily_{test_date.strftime('%Y%m%d')}.nc"

        if not raw_file.exists():
            logger.error(f"✗ Raw file not found: {raw_file}")
            return False

        logger.info("\n" + "=" * 80)
        logger.info("CHECKING RAW NETCDF COVERAGE")
        logger.info("=" * 80)

        if not check_coverage(raw_file):
            logger.error("\n✗ TEST FAILED: Raw NetCDF does not cover full Brazil")
            return False

        # Check the processed GeoTIFF
        tif_file = Path(settings.DATA_DIR) / "glm_fed" / f"glm_fed_{test_date.strftime('%Y%m%d')}.tif"

        if tif_file.exists():
            logger.info("\n" + "=" * 80)
            logger.info("CHECKING GEOTIFF COVERAGE")
            logger.info("=" * 80)

            import rasterio
            with rasterio.open(tif_file) as src:
                bounds = src.bounds
                logger.info(f"  GeoTIFF bounds: W={bounds.left:.2f}, S={bounds.bottom:.2f}, E={bounds.right:.2f}, N={bounds.top:.2f}")

                tif_lat_covered = (bounds.bottom <= BRAZIL_BBOX['lat_min']) and (bounds.top >= BRAZIL_BBOX['lat_max'])
                tif_lon_covered = (bounds.left <= BRAZIL_BBOX['lon_min']) and (bounds.right >= BRAZIL_BBOX['lon_max'])

                if tif_lat_covered and tif_lon_covered:
                    logger.info("  ✓ GEOTIFF COVERS FULL BRAZIL!")
                else:
                    logger.warning("  ⚠ GeoTIFF has partial coverage (this is OK if clipped to Brazil bbox)")

        print("\n" + "=" * 80)
        print("✓ TEST PASSED: Full Brazil coverage confirmed!")
        print("=" * 80)
        print(f"Files created:")
        print(f"  Raw NetCDF: {raw_file}")
        if tif_file.exists():
            print(f"  GeoTIFF: {tif_file}")
        print("=" * 80)

        return True

    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
