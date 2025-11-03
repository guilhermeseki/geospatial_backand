#!/usr/bin/env python3
"""
Enable time dimension for GLM FED layer in GeoServer
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.geoserver import GeoServerMosaicManager
from app.config.settings import get_settings

settings = get_settings()


def enable_glm_fed_time_dimension():
    """Enable time dimension for GLM FED layer"""

    workspace = "glm_ws"
    layer = "glm_fed"

    print("=" * 80)
    print("Enabling Time Dimension for GLM FED Layer")
    print("=" * 80)
    print(f"Workspace: {workspace}")
    print(f"Layer: {layer}")
    print()

    # Initialize GeoServer mosaic manager
    manager = GeoServerMosaicManager()

    # Enable time dimension
    print("Configuring time dimension...")
    result = manager.enable_time_dimension(
        layer_name=layer,
        presentation="LIST",
        default_value_strategy="MAXIMUM",
        nearest_match=False
    )

    if result:
        print("✓ Time dimension enabled successfully!")
        print()
        print("Configuration:")
        print("  - Presentation: LIST (shows all available dates)")
        print("  - Default value: MAXIMUM (most recent date)")
        print("  - Nearest match: False (exact dates only)")
        print()
        print("=" * 80)
        print("Next steps:")
        print("1. Test WMS GetCapabilities to verify time dimension")
        print("2. Apply custom lightning style (glm_fed_style.sld)")
        print("3. Test WMS GetMap with time parameter")
        print("=" * 80)
        return True
    else:
        print("✗ Failed to enable time dimension")
        print()
        print("Troubleshooting:")
        print("1. Verify the layer exists in GeoServer")
        print("2. Check GeoServer logs for errors")
        print("3. Verify ImageMosaic configuration (indexer.properties)")
        return False


if __name__ == "__main__":
    success = enable_glm_fed_time_dimension()
    sys.exit(0 if success else 1)
