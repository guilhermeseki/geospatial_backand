"""
Dataset Verification Script
Checks completeness of all datasets before going operational.
"""
from pathlib import Path
from datetime import date, timedelta
from app.config.settings import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()

def check_dataset(name, glob_pattern, expected_start, expected_end, date_extraction_fn):
    """Check a dataset for completeness"""
    logger.info(f"\n{'=' * 80}")
    logger.info(f"{name.upper()}")
    logger.info(f"{'=' * 80}")

    data_dir = Path(settings.DATA_DIR) / name
    if not data_dir.exists():
        logger.warning(f"❌ Directory does not exist: {data_dir}")
        return

    files = sorted(data_dir.glob(glob_pattern))
    logger.info(f"Files found: {len(files)}")

    if not files:
        logger.warning(f"❌ No files found")
        return

    # Extract dates
    dates = []
    for f in files:
        try:
            date_str = date_extraction_fn(f)
            dates.append(date_str)
        except:
            continue

    dates = sorted(dates)
    logger.info(f"Date range: {dates[0]} → {dates[-1]}")

    # Calculate expected
    start_date = expected_start
    end_date = expected_end
    expected_days = (end_date - start_date).days + 1

    logger.info(f"Expected range: {start_date} → {end_date}")
    logger.info(f"Expected files: ~{expected_days}")
    logger.info(f"Actual files: {len(files)}")

    coverage = (len(files) / expected_days) * 100
    logger.info(f"Coverage: {coverage:.1f}%")

    if coverage >= 95:
        logger.info(f"✓ Dataset is {coverage:.1f}% complete (GOOD)")
    elif coverage >= 80:
        logger.warning(f"⚠ Dataset is {coverage:.1f}% complete (ACCEPTABLE)")
    else:
        logger.warning(f"❌ Dataset is {coverage:.1f}% complete (NEEDS BACKFILL)")

    # Check for recent gaps
    recent_start = date.today() - timedelta(days=7)
    recent_dates = [d for d in dates if d >= recent_start.strftime('%Y%m%d')]
    logger.info(f"\nRecent files (last 7 days): {len(recent_dates)}")

    if len(recent_dates) >= 5:
        logger.info("✓ Recent data looks good")
    else:
        logger.warning("⚠ Missing recent data (check if update is running)")

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("DATASET VERIFICATION - PRE-OPERATIONAL CHECK")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Checking all datasets for completeness...")

    # CHIRPS (2015-01-01 to yesterday)
    check_dataset(
        name="chirps",
        glob_pattern="chirps_*.tif",
        expected_start=date(2015, 1, 1),
        expected_end=date.today() - timedelta(days=1),
        date_extraction_fn=lambda f: f.stem.split('_')[1]
    )

    # MERGE (2014-11-01 to yesterday)
    check_dataset(
        name="merge",
        glob_pattern="merge_*.tif",
        expected_start=date(2014, 11, 1),
        expected_end=date.today() - timedelta(days=1),
        date_extraction_fn=lambda f: f.stem.split('_')[1]
    )

    # ERA5 Temperature Max (2015-01-01 to 7 days ago)
    check_dataset(
        name="temp_max",
        glob_pattern="temp_max_*.tif",
        expected_start=date(2015, 1, 1),
        expected_end=date.today() - timedelta(days=7),
        date_extraction_fn=lambda f: f.stem.split('_')[2]
    )

    # ERA5 Temperature Min (2015-01-01 to 7 days ago)
    check_dataset(
        name="temp_min",
        glob_pattern="temp_min_*.tif",
        expected_start=date(2015, 1, 1),
        expected_end=date.today() - timedelta(days=7),
        date_extraction_fn=lambda f: f.stem.split('_')[2]
    )

    # ERA5 Temperature Mean (2015-01-01 to 7 days ago)
    check_dataset(
        name="temp_mean",
        glob_pattern="temp_mean_*.tif",
        expected_start=date(2015, 1, 1),
        expected_end=date.today() - timedelta(days=7),
        date_extraction_fn=lambda f: f.stem.split('_')[2]
    )

    # ERA5 Wind Speed (2015-01-01 to 7 days ago)
    check_dataset(
        name="wind_speed",
        glob_pattern="wind_speed_*.tif",
        expected_start=date(2015, 1, 1),
        expected_end=date.today() - timedelta(days=7),
        date_extraction_fn=lambda f: f.stem.split('_')[2]
    )

    # GLM (April 15, 2025 to 2 days ago)
    check_dataset(
        name="glm_fed",
        glob_pattern="glm_fed_*.tif",
        expected_start=date(2025, 4, 15),
        expected_end=date.today() - timedelta(days=2),
        date_extraction_fn=lambda f: f.stem.split('_')[2]
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("VERIFICATION COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Next Steps:")
    logger.info("  - If coverage < 95%, run backfill: ./run_full_backfill.sh")
    logger.info("  - If coverage >= 95%, ready for operational: ./install_cron_schedule.sh")
    logger.info("")
