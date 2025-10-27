#!/bin/bash
# Check status of geospatial data update timers

echo "="*80
echo "GEOSPATIAL DATA SCHEDULER STATUS"
echo "="*80
echo ""

echo "📅 TIMER STATUS"
echo "-"*80
systemctl list-timers geospatial-* --all --no-pager
echo ""

echo "🔄 SERVICE STATUS"
echo "-"*80
echo ""
echo "[ERA5 Temperature]"
systemctl status geospatial-era5.timer --no-pager | head -10
echo ""

echo "[Precipitation CHIRPS/MERGE]"
systemctl status geospatial-precipitation.timer --no-pager | head -10
echo ""

echo "[MODIS NDVI]"
systemctl status geospatial-ndvi.timer --no-pager | head -10
echo ""

echo "📊 RECENT LOGS"
echo "-"*80
echo ""

if [ -f /opt/geospatial_backend/logs/era5-daily.log ]; then
    echo "[ERA5 - Last 5 lines]"
    tail -5 /opt/geospatial_backend/logs/era5-daily.log
    echo ""
fi

if [ -f /opt/geospatial_backend/logs/precipitation-daily.log ]; then
    echo "[Precipitation - Last 5 lines]"
    tail -5 /opt/geospatial_backend/logs/precipitation-daily.log
    echo ""
fi

if [ -f /opt/geospatial_backend/logs/ndvi-daily.log ]; then
    echo "[NDVI - Last 5 lines]"
    tail -5 /opt/geospatial_backend/logs/ndvi-daily.log
    echo ""
fi

echo "="*80
echo ""
echo "To view full logs:"
echo "  journalctl -u geospatial-era5.service -f"
echo "  tail -f logs/era5-daily.log"
echo ""
echo "To manually trigger:"
echo "  sudo systemctl start geospatial-era5.service"
echo ""
echo "To disable:"
echo "  sudo systemctl stop geospatial-era5.timer"
echo "  sudo systemctl disable geospatial-era5.timer"
