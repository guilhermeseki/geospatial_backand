# run_era5_debug.py
from datetime import date
from app.workflows.data_processing.era5_flow import download_era5_batch, split_era5_batch
from app.config.settings import get_settings
import json

settings = get_settings()

print("=" * 80)
print("SETTINGS CHECK")
print("=" * 80)
print(f"DATA_DIR: {settings.DATA_DIR}")
print(f"latam_bbox_raster: {settings.latam_bbox_raster}")
print(f"Bbox type: {type(settings.latam_bbox_raster)}")
print(f"Bbox length: {len(settings.latam_bbox_raster) if hasattr(settings.latam_bbox_raster, '__len__') else 'N/A'}")
print()

# Check what the request will look like before sending
start_date = date(2025, 1, 1)
end_date = date(2025, 1, 31)
variables = ["maximum_2m_temperature_since_previous_post_processing"]

print("=" * 80)
print("REQUEST PARAMETERS")
print("=" * 80)
print(f"Start date: {start_date}")
print(f"End date: {end_date}")
print(f"Variables: {variables}")
print(f"Area: {settings.latam_bbox_raster}")
print()

# Generate dates to see what will be requested
from datetime import timedelta
dates = []
current = start_date
while current <= end_date:
    dates.append(current)
    current += timedelta(days=1)

years = sorted(list(set([d.strftime("%Y") for d in dates])))
months = sorted(list(set([d.strftime("%m") for d in dates])))
days = sorted(list(set([d.strftime("%d") for d in dates])))

print("=" * 80)
print("PARSED DATE COMPONENTS")
print("=" * 80)
print(f"Years: {years}")
print(f"Months: {months}")
print(f"Days: {days}")
print(f"Total days: {len(dates)}")
print()

# Show the exact request that will be built
request = {
    "product_type": "reanalysis",
    "variable": variables,
    "year": years[0] if len(years) == 1 else years,
    "month": months[0] if len(months) == 1 else months,
    "day": days,
    "time": [f"{h:02d}:00" for h in range(24)],
    "area": settings.latam_bbox_raster,
    "format": "netcdf"
}

print("=" * 80)
print("EXACT CDS API REQUEST")
print("=" * 80)
print(json.dumps(request, indent=2, default=str))
print()

print("=" * 80)
print("STARTING DOWNLOAD...")
print("=" * 80)

try:
    # Now actually run the download
    batch_path = download_era5_batch(
        start_date=start_date,
        end_date=end_date,
        variables=variables,
        area=settings.latam_bbox_raster
    )
    print(f"\n✓ SUCCESS: Downloaded to {batch_path}")
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()