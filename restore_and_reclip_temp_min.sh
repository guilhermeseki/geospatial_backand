#!/bin/bash
# Restore temp_min from backup and re-clip with correct bbox (matching temp_max)

set -e

echo "======================================================================="
echo "RESTORE AND RE-CLIP TEMP_MIN WITH CORRECT BBOX"
echo "======================================================================="
echo ""

TEMP_MIN_DIR="/mnt/workwork/geoserver_data/temp_min"
BACKUP_DIR="/mnt/workwork/geoserver_data/temp_min_backup"

# Count files
FILE_COUNT=$(ls -1 "$BACKUP_DIR"/temp_min_*.tif 2>/dev/null | wc -l)

echo "Found $FILE_COUNT files in backup"
echo ""

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "ERROR: No backup files found!"
    exit 1
fi

echo "Step 1: Restoring temp_min files from backup..."
echo "  Source: $BACKUP_DIR"
echo "  Target: $TEMP_MIN_DIR"
echo ""

# Copy all backup files back to temp_min directory
rsync -av --progress "$BACKUP_DIR"/temp_min_*.tif "$TEMP_MIN_DIR/"

echo ""
echo "✓ Files restored from backup"
echo ""

# Verify one file has correct bbox
echo "Verifying bbox of restored file..."
gdalinfo "$TEMP_MIN_DIR/temp_min_20240101.tif" | grep "Upper Left"

echo ""
echo "======================================================================="
echo "RESTORE COMPLETE"
echo "======================================================================="
echo ""
echo "Next: Delete GeoServer index files and restart"
echo "  rm -f $TEMP_MIN_DIR/temp_min.{shp,shx,dbf,prj,qix}"
echo "  sudo systemctl restart geoserver"
echo ""
