#!/bin/bash
# Monitor solar radiation processing progress

echo "================================================================================"
echo "Solar Radiation Processing Progress Monitor"
echo "================================================================================"
echo ""

# Count GeoTIFF files
echo "📁 GeoTIFF Files:"
total_geotiffs=$(find /mnt/workwork/geoserver_data/solar_radiation/ -name "solar_radiation_*.tif" 2>/dev/null | wc -l)
echo "   Total files: $total_geotiffs"
if [ $total_geotiffs -gt 0 ]; then
    latest_geotiff=$(ls -t /mnt/workwork/geoserver_data/solar_radiation/solar_radiation_*.tif 2>/dev/null | head -1)
    echo "   Latest: $(basename $latest_geotiff)"
fi
echo ""

# Count historical NetCDF dates
echo "📊 Historical NetCDF:"
if [ -d "/mnt/workwork/geoserver_data/solar_radiation_hist" ]; then
    for nc_file in /mnt/workwork/geoserver_data/solar_radiation_hist/solar_radiation_*.nc; do
        if [ -f "$nc_file" ]; then
            year=$(basename "$nc_file" | sed 's/solar_radiation_//' | sed 's/.nc//')
            size=$(du -h "$nc_file" | cut -f1)
            echo "   Year $year: $size"
        fi
    done
else
    echo "   No historical files yet"
fi
echo ""

# Check running jobs
echo "🔄 Active Processing Jobs:"
ps aux | grep "python app/run_solar.py --year" | grep -v grep | while read line; do
    year=$(echo "$line" | grep -oP "year \K\d+")
    if [ ! -z "$year" ]; then
        echo "   ✓ Year $year processing..."
    fi
done
echo ""

# Check log progress
echo "📝 Recent Progress (from logs):"
for year in 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024; do
    log_file="logs/solar_${year}.log"
    if [ -f "$log_file" ]; then
        # Get last completed batch or current batch
        last_line=$(grep -E "Batch:|Completed batch:|✓ Updated" "$log_file" | tail -1)
        if [ ! -z "$last_line" ]; then
            echo "   Year $year: $(echo $last_line | sed 's/.*| INFO.*- //')"
        fi
    fi
done
echo ""

echo "================================================================================"
echo "Expected total: ~3,650 days (2015-2024)"
echo "Progress: $total_geotiffs / ~3,650 files ($(( total_geotiffs * 100 / 3650 ))%)"
echo "================================================================================"
