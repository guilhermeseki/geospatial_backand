#!/usr/bin/env python3
"""
Optimized GLM FED backfill script for historical data
Uses parallel downloads and checkpointing for efficient processing

USAGE:
    # Full backfill (2018-present)
    python app/run_glm_optimized_backfill.py

    # Specific date range
    python app/run_glm_optimized_backfill.py --start 2023-01-01 --end 2023-12-31

    # Resume from checkpoint
    python app/run_glm_optimized_backfill.py --resume

    # Adjust parallelism (default 8 workers)
    python app/run_glm_optimized_backfill.py --workers 16
"""
from datetime import date, timedelta
from app.workflows.data_processing.glm_fed_flow_optimized import glm_fed_flow_optimized
import logging
import argparse
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(f'logs/glm_optimized_backfill_{date.today().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Optimized GLM FED backfill with parallel downloads')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)', default=None)
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)', default=None)
    parser.add_argument('--workers', type=int, help='Number of parallel download workers', default=8)
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--no-checkpoint', action='store_true', help='Disable checkpointing')

    args = parser.parse_args()

    # Determine date range
    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    elif args.resume:
        # Resume will be handled by the flow itself
        # Default to full range, flow will skip already-processed dates
        start_date = date(2018, 1, 1)  # GLM available since 2018
        end_date = date.today() - timedelta(days=1)
        logger.info("RESUME MODE: Will skip already-processed dates from checkpoint")
    else:
        # Default: Full backfill from GLM start
        start_date = date(2018, 1, 1)
        end_date = date.today() - timedelta(days=1)

    total_days = (end_date - start_date).days + 1

    logger.info("="*80)
    logger.info("GLM FED OPTIMIZED BACKFILL")
    logger.info("="*80)
    logger.info(f"Date range: {start_date} to {end_date} ({total_days} days)")
    logger.info(f"Parallel workers: {args.workers}")
    logger.info(f"Checkpointing: {'Disabled' if args.no_checkpoint else 'Enabled'}")
    logger.info("="*80)
    logger.info("")
    logger.info("OPTIMIZATIONS ACTIVE:")
    logger.info(f"  ✓ Parallel downloads ({args.workers}x speedup)")
    logger.info(f"  ✓ Progress tracking with ETA")
    logger.info(f"  ✓ Checkpointing every 10 files" if not args.no_checkpoint else "  ✗ Checkpointing disabled")
    logger.info(f"  ✓ Memory-efficient batch processing")
    logger.info("="*80)
    logger.info("")

    # Estimate time
    # Original: ~1.5h per day = 90 min
    # Optimized: ~25 min per day (4x faster downloads + 20% faster processing)
    estimated_time_per_day_minutes = 25
    estimated_total_hours = (total_days * estimated_time_per_day_minutes) / 60
    estimated_days = estimated_total_hours / 24

    logger.info(f"ESTIMATED TIME:")
    logger.info(f"  Per day: ~{estimated_time_per_day_minutes} minutes")
    logger.info(f"  Total: ~{estimated_total_hours:.1f} hours ({estimated_days:.1f} days)")
    logger.info(f"  Note: This is {1.5 * 60 / estimated_time_per_day_minutes:.1f}x faster than original flow")
    logger.info("="*80)
    logger.info("")

    # Confirm with user
    try:
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return
    except KeyboardInterrupt:
        logger.info("\nCancelled by user")
        return

    logger.info("")
    logger.info("Starting backfill...")
    logger.info("")

    # Run the optimized flow
    try:
        result = glm_fed_flow_optimized(
            start_date=start_date,
            end_date=end_date,
            max_download_workers=args.workers,
            enable_checkpointing=not args.no_checkpoint
        )

        logger.info("")
        logger.info("="*80)
        logger.info("BACKFILL COMPLETE!")
        logger.info("="*80)
        logger.info(f"Successfully processed: {len(result)} files")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info("="*80)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("="*80)
        logger.info("INTERRUPTED BY USER")
        logger.info("="*80)
        if not args.no_checkpoint:
            logger.info("Progress has been saved to checkpoint.")
            logger.info("Resume with: python app/run_glm_optimized_backfill.py --resume")
        logger.info("="*80)
        sys.exit(1)

    except Exception as e:
        logger.error("="*80)
        logger.error("BACKFILL FAILED")
        logger.error("="*80)
        logger.error(f"Error: {e}")
        logger.exception(e)
        if not args.no_checkpoint:
            logger.info("Progress has been saved to checkpoint.")
            logger.info("Resume with: python app/run_glm_optimized_backfill.py --resume")
        logger.error("="*80)
        sys.exit(1)


if __name__ == "__main__":
    main()
