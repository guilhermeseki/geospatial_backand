#!/bin/bash
#
# Install Cron Schedule for Daily Data Updates
#
# This script installs the cron job that runs daily updates at 2:00 AM

set -e

echo "========================================================================"
echo "Installing Cron Schedule for Daily Data Updates"
echo "========================================================================"
echo ""

# Check if script is run as the correct user
CURRENT_USER=$(whoami)
echo "Current user: $CURRENT_USER"
echo ""

# Create logs directory
LOG_DIR="/opt/geospatial_backend/logs"
mkdir -p "$LOG_DIR"
echo "✓ Logs directory: $LOG_DIR"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "run_daily_updates_2am.sh"; then
    echo "⚠️  Cron entry already exists!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep "run_daily_updates_2am.sh"
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    # Remove old entry
    crontab -l | grep -v "run_daily_updates_2am.sh" | crontab -
fi

# Add new cron entry
echo "Adding cron entry..."
(crontab -l 2>/dev/null; echo "# Daily data updates at 2:00 AM") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/geospatial_backend/run_daily_updates_2am.sh >> /opt/geospatial_backend/logs/daily_updates.log 2>&1") | crontab -

echo "✓ Cron entry added successfully!"
echo ""

# Show current crontab
echo "========================================================================"
echo "Current Crontab:"
echo "========================================================================"
crontab -l
echo ""

echo "========================================================================"
echo "Installation Complete!"
echo "========================================================================"
echo ""
echo "Schedule:"
echo "  • Daily updates run at 2:00 AM every day"
echo "  • Includes: CHIRPS, MERGE, ERA5 (temp/wind), GLM"
echo "  • Excludes: NDVI (schedule separately if needed)"
echo ""
echo "Logs:"
echo "  • Location: /opt/geospatial_backend/logs/daily_updates.log"
echo "  • View: tail -f /opt/geospatial_backend/logs/daily_updates.log"
echo ""
echo "Testing:"
echo "  • Test run: /opt/geospatial_backend/run_daily_updates_2am.sh"
echo ""
echo "Uninstall:"
echo "  • crontab -e"
echo "  • Remove the line with 'run_daily_updates_2am.sh'"
echo ""
