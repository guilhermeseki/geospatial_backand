#!/bin/bash
# Reindex GeoServer temperature mosaics after clipping files
# This deletes old shapefile indexes and forces GeoServer to regenerate them

set -e

echo "======================================================================="
echo "REINDEXING GEOSERVER TEMPERATURE MOSAICS"
echo "======================================================================="
echo ""

# Delete old index files for each temperature dataset
for dataset in temp_max temp_min temp_mean; do
    echo "Processing $dataset..."

    DATA_DIR="/mnt/workwork/geoserver_data/$dataset"

    # Delete shapefile index files
    rm -f "$DATA_DIR/$dataset.shp"
    rm -f "$DATA_DIR/$dataset.shx"
    rm -f "$DATA_DIR/$dataset.dbf"
    rm -f "$DATA_DIR/$dataset.prj"
    rm -f "$DATA_DIR/$dataset.qix"

    echo "  ✓ Deleted old index files for $dataset"
done

echo ""
echo "======================================================================="
echo "INDEX FILES DELETED - NOW RESTART GEOSERVER"
echo "======================================================================="
echo ""
echo "Next steps:"
echo "1. sudo systemctl restart geoserver"
echo "2. GeoServer will automatically regenerate index files with correct bbox"
echo "3. Check WMS layers to verify alignment"
echo ""
