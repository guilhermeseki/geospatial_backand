"""
Run GLM FED processing in parallel - process multiple days simultaneously
"""
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/opt/geospatial_backend/logs/glm_parallel.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_missing_dates():
    """Find dates that don't have GeoTIFF files yet"""
    data_dir = Path("/mnt/workwork/geoserver_data/glm_fed")

    # Get existing files
    existing_files = list(data_dir.glob("glm_fed_*.tif"))
    existing_dates = set()

    for f in existing_files:
        date_str = f.stem.split('_')[-1]  # glm_fed_20250415 -> 20250415
        try:
            d = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
            existing_dates.add(d)
        except:
            continue

    # Target range: April 1 - November 30, 2025
    target_start = date(2025, 4, 1)
    target_end = date(2025, 11, 30)

    missing = []
    current = target_start
    while current <= target_end:
        if current not in existing_dates:
            missing.append(current)
        current += timedelta(days=1)

    return sorted(missing)

def run_date_range(start_date: date, end_date: date, process_id: int):
    """Run GLM processing for a specific date range"""
    logger.info(f"[Process {process_id}] Starting: {start_date} to {end_date}")

    cmd = [
        "python",
        "/opt/geospatial_backend/app/run_glm_fed_resume.py",
        "--start", start_date.strftime("%Y-%m-%d"),
        "--end", end_date.strftime("%Y-%m-%d")
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=None
        )

        if result.returncode == 0:
            logger.info(f"[Process {process_id}] Completed successfully")
        else:
            logger.error(f"[Process {process_id}] Failed with code {result.returncode}")
            logger.error(f"[Process {process_id}] Error: {result.stderr[:500]}")

        return result.returncode

    except Exception as e:
        logger.error(f"[Process {process_id}] Exception: {e}")
        return 1

def main():
    NUM_PARALLEL = 3  # Process 3 days at once

    logger.info("="*80)
    logger.info("GLM FED Parallel Processing")
    logger.info("="*80)

    missing = get_missing_dates()

    if not missing:
        logger.info("✓ No missing dates - all done!")
        return

    logger.info(f"Missing dates: {len(missing)}")
    logger.info(f"Range: {missing[0]} to {missing[-1]}")
    logger.info(f"Parallel processes: {NUM_PARALLEL}")
    logger.info("")

    # Split into chunks for parallel processing
    chunk_size = max(1, len(missing) // NUM_PARALLEL)

    processes = []
    for i in range(NUM_PARALLEL):
        start_idx = i * chunk_size
        if i == NUM_PARALLEL - 1:
            # Last process gets remaining dates
            chunk = missing[start_idx:]
        else:
            chunk = missing[start_idx:start_idx + chunk_size]

        if not chunk:
            continue

        logger.info(f"Process {i+1}: {len(chunk)} dates ({chunk[0]} to {chunk[-1]})")

        # Launch subprocess
        cmd = [
            "python",
            __file__.replace("run_glm_parallel.py", "run_glm_single_date.py"),
            str(chunk[0]),
            str(chunk[-1]),
            str(i+1)
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append((i+1, proc, chunk))

    logger.info("")
    logger.info(f"Launched {len(processes)} parallel processes")
    logger.info("Waiting for completion...")

    # Wait for all to complete
    for proc_id, proc, chunk in processes:
        proc.wait()
        if proc.returncode == 0:
            logger.info(f"✓ Process {proc_id} completed successfully")
        else:
            logger.error(f"✗ Process {proc_id} failed with code {proc.returncode}")

    logger.info("="*80)
    logger.info("All processes completed")
    logger.info("="*80)

if __name__ == "__main__":
    main()
