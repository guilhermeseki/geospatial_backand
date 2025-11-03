#!/usr/bin/env python3
"""
Setup GeoServer layer for GLM Flash Extent Density data
Creates workspace, ImageMosaic store, and time-enabled layer
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.geoserver import GeoServerService
from app.config.settings import get_settings

settings = get_settings()
geoserver = GeoServerService()


def create_indexer_properties():
    """Create indexer.properties for GLM FED ImageMosaic"""
    glm_fed_dir = Path(settings.DATA_DIR) / "glm_fed"
    glm_fed_dir.mkdir(parents=True, exist_ok=True)

    indexer_file = glm_fed_dir / "indexer.properties"

    content = """# GLM FED ImageMosaic Configuration
TimeAttribute=ingestion
Schema=*the_geom:Polygon,location:String,ingestion:java.util.Date
PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion)
"""

    with open(indexer_file, 'w') as f:
        f.write(content)

    print(f"✓ Created {indexer_file}")

    # Create timeregex.properties
    timeregex_file = glm_fed_dir / "timeregex.properties"

    timeregex_content = """# Extract date from filename: glm_fed_YYYYMMDD.tif
regex=.*([0-9]{8}).*
format=yyyyMMdd
"""

    with open(timeregex_file, 'w') as f:
        f.write(timeregex_content)

    print(f"✓ Created {timeregex_file}")

    return glm_fed_dir


def setup_glm_fed_layer():
    """Create and configure GLM FED layer in GeoServer"""

    workspace_name = "glm_ws"
    store_name = "glm_fed"
    layer_name = "glm_fed"

    print("=" * 80)
    print("Setting up GLM FED layer in GeoServer")
    print("=" * 80)

    # Step 1: Create indexer properties
    print("\n1. Creating ImageMosaic configuration...")
    glm_fed_dir = create_indexer_properties()

    # Step 2: Create workspace
    print(f"\n2. Creating workspace '{workspace_name}'...")
    workspace_result = geoserver.create_workspace(
        name=workspace_name,
        uri=f"http://geospatial.backend/{workspace_name}"
    )

    if workspace_result:
        print(f"✓ Workspace '{workspace_name}' created/verified")
    else:
        print(f"⚠ Failed to create workspace (may already exist)")

    # Step 3: Create ImageMosaic coverage store
    print(f"\n3. Creating ImageMosaic store '{store_name}'...")
    store_result = geoserver.create_imagemosaic_coveragestore(
        workspace=workspace_name,
        name=store_name,
        mosaic_path=str(glm_fed_dir)
    )

    if store_result:
        print(f"✓ ImageMosaic store '{store_name}' created")
    else:
        print(f"✗ Failed to create ImageMosaic store")
        return False

    # Step 4: Publish coverage
    print(f"\n4. Publishing coverage '{layer_name}'...")
    coverage_result = geoserver.publish_coverage(
        workspace=workspace_name,
        store=store_name,
        name=layer_name,
        native_name=store_name,
        title="GLM Flash Extent Density",
        abstract="GOES GLM Gridded Flash Extent Density - Daily aggregated lightning flash counts at 8km resolution"
    )

    if coverage_result:
        print(f"✓ Coverage '{layer_name}' published")
    else:
        print(f"✗ Failed to publish coverage")
        return False

    print("\n" + "=" * 80)
    print("✓ GLM FED layer setup complete!")
    print("=" * 80)
    print(f"\nWorkspace: {workspace_name}")
    print(f"Store: {store_name}")
    print(f"Layer: {layer_name}")
    print(f"Data directory: {glm_fed_dir}")
    print("\nNext steps:")
    print("1. Run the GLM FED flow to download and process data")
    print("2. Enable time dimension using enable_time_glm_fed.py")
    print("3. Apply custom SLD style")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = setup_glm_fed_layer()
    sys.exit(0 if success else 1)
