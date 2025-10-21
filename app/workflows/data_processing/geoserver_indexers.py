"""
GeoServer Indexer Configuration Task
Creates timeregex.properties and indexer.properties for time-enabled mosaics
"""
from pathlib import Path
from typing import List, Optional, Union
from prefect import task, flow, get_run_logger
from app.config.settings import get_settings


@task
def create_geoserver_indexers(directory: Path) -> bool:
    """
    Create GeoServer indexer configuration files for time-enabled mosaics.
    Creates timeregex.properties and indexer.properties in the specified directory.
    
    Args:
        directory: Directory containing the GeoTIFF files
    
    Returns:
        True if successful
    """
    logger = get_run_logger()
    
    try:
        # Create timeregex.properties
        timeregex_path = directory / "timeregex.properties"
        timeregex_content = """# timeregex.properties
# Extract date from filename pattern: *_YYYYMMDD.tif
regex=.*([0-9]{8}).*
format=yyyyMMdd
"""
        with open(timeregex_path, 'w') as f:
            f.write(timeregex_content)
        logger.info(f"✓ Created: {timeregex_path}")
        
        # Create indexer.properties
        indexer_path = directory / "indexer.properties"
        indexer_content = """# indexer.properties
# Time-enabled mosaic configuration
TimeAttribute=ingestion
Schema=*the_geom:Polygon,location:String,ingestion:java.util.Date
PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion)
"""
        with open(indexer_path, 'w') as f:
            f.write(indexer_content)
        logger.info(f"✓ Created: {indexer_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create indexer files in {directory}: {e}")
        return False


@flow(name="setup-geoserver-indexers", validate_parameters=False)
def setup_geoserver_indexers_flow(
    data_dir: Union[str, None] = None,
    directories: Union[List[str], None] = None,
    force: bool = False
):
    """
    Standalone flow to create GeoServer indexer files for TIF directories.
    Run this once to set up time-enabled mosaics.
    
    Args:
        data_dir: Base data directory (default: from settings)
        directories: List of directory names to process (default: all known directories)
        force: If True, recreate indexers even if they exist
    """
    logger = get_run_logger()
    
    if data_dir is None:
        settings = get_settings()
        data_dir = settings.DATA_DIR
    
    base_path = Path(data_dir)
    
    # Default list of directories that contain TIF files
    if directories is None:
        directories = [
            'temp_max',
            'temp_min',
            'temp',
            'chirps',
            'chirps_historical',
            'merge',
            'merge_historical',
            'temp_hist',
            'temp_max_hist',
            'temp_min_hist'
        ]
    
    logger.info(f"Setting up GeoServer indexers in: {base_path}")
    logger.info(f"Force recreate: {force}")
    logger.info(f"{'='*80}")
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    for dir_name in directories:
        dir_path = base_path / dir_name
        
        if not dir_path.exists():
            logger.info(f"⊘ Directory doesn't exist, skipping: {dir_name}")
            continue
        
        # Check if indexers already exist
        indexer_exists = (dir_path / "indexer.properties").exists()
        
        if indexer_exists and not force:
            logger.info(f"⊙ Indexers already exist, skipping: {dir_name}")
            skipped_count += 1
            continue
        
        # Create indexers
        if indexer_exists and force:
            logger.info(f"♻ Recreating indexers for: {dir_name}")
        else:
            logger.info(f"➕ Creating indexers for: {dir_name}")
        
        success = create_geoserver_indexers(dir_path)
        
        if success:
            created_count += 1
        else:
            error_count += 1
    
    logger.info(f"{'='*80}")
    logger.info(f"✓ Created indexers in {created_count} directories")
    logger.info(f"⊙ Skipped {skipped_count} directories (already had indexers)")
    if error_count > 0:
        logger.info(f"✗ Failed for {error_count} directories")
    logger.info(f"Summary: {created_count} created, {skipped_count} skipped, {error_count} errors")
    
    return {
        'created': created_count,
        'skipped': skipped_count,
        'errors': error_count
    }


if __name__ == "__main__":
    # Example usage
    setup_geoserver_indexers_flow()