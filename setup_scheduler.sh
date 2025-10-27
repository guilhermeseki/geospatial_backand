#!/bin/bash
# Setup systemd timers for automated daily updates

echo "="*80
echo "GEOSPATIAL DATA AUTOMATED SCHEDULER SETUP"
echo "="*80
echo ""
echo "This will install systemd timers for:"
echo "  - ERA5 temperature (runs at 02:00 AM)"
echo "  - Precipitation CHIRPS/MERGE (runs at 02:15 AM)"
echo "  - MODIS NDVI (runs at 02:30 AM)"
echo ""
echo "Requires sudo access to install systemd files."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Setup cancelled."
    exit 1
fi

echo ""
echo "Installing systemd service and timer files..."

# Create logs directory
mkdir -p /opt/geospatial_backend/logs

# Copy service files
sudo cp systemd/geospatial-era5.service /etc/systemd/system/
sudo cp systemd/geospatial-era5.timer /etc/systemd/system/
sudo cp systemd/geospatial-precipitation.service /etc/systemd/system/
sudo cp systemd/geospatial-precipitation.timer /etc/systemd/system/
sudo cp systemd/geospatial-ndvi.service /etc/systemd/system/
sudo cp systemd/geospatial-ndvi.timer /etc/systemd/system/

echo "✓ Service files installed"

# Reload systemd
sudo systemctl daemon-reload
echo "✓ Systemd reloaded"

# Enable timers (so they start on boot)
sudo systemctl enable geospatial-era5.timer
sudo systemctl enable geospatial-precipitation.timer
sudo systemctl enable geospatial-ndvi.timer
echo "✓ Timers enabled (will start on boot)"

# Start timers
sudo systemctl start geospatial-era5.timer
sudo systemctl start geospatial-precipitation.timer
sudo systemctl start geospatial-ndvi.timer
echo "✓ Timers started"

echo ""
echo "="*80
echo "✅ SETUP COMPLETE!"
echo "="*80
echo ""
echo "Daily updates are now scheduled:"
echo "  - ERA5 temperature: 02:00 AM daily"
echo "  - Precipitation: 02:15 AM daily"
echo "  - MODIS NDVI: 02:30 AM daily"
echo ""
echo "Check status:"
echo "  ./check_scheduler_status.sh"
echo ""
echo "View logs:"
echo "  tail -f logs/era5-daily.log"
echo "  tail -f logs/precipitation-daily.log"
echo "  tail -f logs/ndvi-daily.log"
echo ""
echo "Manual trigger (for testing):"
echo "  sudo systemctl start geospatial-era5.service"
echo "  sudo systemctl start geospatial-precipitation.service"
echo "  sudo systemctl start geospatial-ndvi.service"
