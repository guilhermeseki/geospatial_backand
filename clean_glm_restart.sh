#!/bin/bash
# Clean up old GLM data to start fresh with fixed bins

echo "================================================================================"
echo "GLM FED DATA CLEANUP - Starting Fresh with Fixed Bins"
echo "================================================================================"
echo ""
echo "This will remove:"
echo "  - Old historical NetCDF files (rolling window data)"
echo "  - Old GeoTIFF files (rolling window data)"
echo "  - Raw temporary files"
echo ""
echo "GeoTIFFs will be regenerated with fixed bins method."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "Cleaning up old GLM data..."
echo ""

# Remove old historical NetCDF (incompatible coordinates)
if [ -d "/mnt/workwork/geoserver_data/glm_fed_hist" ]; then
    echo "✓ Removing old historical NetCDF files..."
    rm -rf /mnt/workwork/geoserver_data/glm_fed_hist/*
fi

# Remove old GeoTIFFs (rolling window method)
if [ -d "/mnt/workwork/geoserver_data/glm_fed" ]; then
    echo "✓ Removing old GeoTIFF files..."
    rm -rf /mnt/workwork/geoserver_data/glm_fed/*
fi

# Remove raw temporary files
if [ -d "/mnt/workwork/geoserver_data/raw/glm_fed" ]; then
    echo "✓ Removing raw temporary files..."
    rm -rf /mnt/workwork/geoserver_data/raw/glm_fed/*
fi

echo ""
echo "================================================================================"
echo "✓ Cleanup complete!"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Run: python app/run_glm_fed_optimized.py"
echo "  2. Processing will use fixed 30-minute bins (research standard)"
echo "  3. Later add Brazil shapefile clipping as planned"
echo ""
echo "Expected processing time: ~1.5-2 hours per day"
echo "Coverage: Northern/Central Brazil (Amazon, Cerrado regions)"
echo "================================================================================"
