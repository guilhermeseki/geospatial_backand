# # run_era5.py
# import os

# # Read from your ~/.cdsapirc and set explicitly
# with open(os.path.expanduser("~/.cdsapirc"), 'r') as f:
#     for line in f:
#         if line.strip().startswith('url:'):
#             os.environ['CDSAPI_URL'] = line.split('url:')[1].strip()
#         elif line.strip().startswith('key:'):
#             os.environ['CDSAPI_KEY'] = line.split('key:')[1].strip()

from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date

# era5_land_daily_flow(
#     batch_days=7,
#     start_date=date(2025, 1, 1),
#     end_date=date(2025, 1, 7)
# )


# era5_land_daily_flow()

# Run for specific date range
from datetime import date
era5_land_daily_flow(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 31)
)
