#!/bin/bash
# Script to delete all GeoServer shapefile indexes
# This forces GeoServer to regenerate them with the new timestamp:String schema

set -e

DATA_DIR="/mnt/workwork/geoserver_data"

# List of datasets to clean
DATASETS=(
    "chirps"
    "merge"
    "temp_max"
    "temp_mean"
    "temp_min"
    "wind_speed"
    "glm_fed"
    "ndvi_modis"
)

echo "============================================================"
echo "DELETING SHAPEFILE INDEXES FOR ALL DATASETS"
echo "============================================================"
echo ""

for dataset in "${DATASETS[@]}"; do
    dir="$DATA_DIR/$dataset"

    if [ ! -d "$dir" ]; then
        echo "⚠️  Directory not found: $dir (skipping)"
        continue
    fi

    echo "Processing: $dataset"

    # Count files before deletion
    shp_count=$(find "$dir" -maxdepth 1 -name "*.shp" -o -name "*.dbf" -o -name "*.shx" -o -name "*.prj" -o -name "*.cpg" -o -name "*.fix" -o -name "*.qix" 2>/dev/null | wc -l)
    props_count=$(find "$dir" -maxdepth 1 -name "${dataset}.properties" 2>/dev/null | wc -l)

    if [ "$shp_count" -eq 0 ] && [ "$props_count" -eq 0 ]; then
        echo "  ✓ No shapefile indexes to delete"
    else
        # Delete shapefile components
        find "$dir" -maxdepth 1 \( -name "*.shp" -o -name "*.dbf" -o -name "*.shx" -o -name "*.prj" -o -name "*.cpg" -o -name "*.fix" -o -name "*.qix" \) -delete 2>/dev/null || true

        # Delete mosaic properties file (but keep indexer.properties and timeregex.properties)
        rm -f "$dir/${dataset}.properties" 2>/dev/null || true

        echo "  ✓ Deleted $shp_count shapefile component(s) and $props_count mosaic properties file(s)"
    fi
    echo ""
done

echo "============================================================"
echo "CLEANUP COMPLETE"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Restart GeoServer manually or run: sudo systemctl restart geoserver"
echo "2. Shapefiles will be automatically regenerated on first WMS request"
echo "3. New shapefiles will use timestamp:String field type"
echo ""
