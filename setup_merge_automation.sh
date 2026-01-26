#!/bin/bash
# Setup script for MERGE data automation
# Installs systemd timers for daily updates and weekly gap checks

set -e

echo "=========================================="
echo "MERGE Data Automation Setup"
echo "=========================================="
echo ""

# Make scripts executable
echo "Making scripts executable..."
chmod +x /opt/geospatial_backend/app/run_merge_operational.py
chmod +x /opt/geospatial_backend/app/check_merge_gaps.py

# Install systemd service files
echo "Installing systemd service files..."

# Copy to systemd user directory
mkdir -p ~/.config/systemd/user/
cp /opt/geospatial_backend/systemd/merge-update.service ~/.config/systemd/user/
cp /opt/geospatial_backend/systemd/merge-update.timer ~/.config/systemd/user/
cp /opt/geospatial_backend/systemd/merge-gap-check.service ~/.config/systemd/user/
cp /opt/geospatial_backend/systemd/merge-gap-check.timer ~/.config/systemd/user/

# Reload systemd
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Enable and start timers
echo "Enabling timers..."
systemctl --user enable merge-update.timer
systemctl --user enable merge-gap-check.timer

echo "Starting timers..."
systemctl --user start merge-update.timer
systemctl --user start merge-gap-check.timer

# Enable linger (so timers run even when not logged in)
echo "Enabling linger (timers will run even when not logged in)..."
sudo loginctl enable-linger $USER

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Timers installed:"
echo "  - merge-update.timer: Daily at 8:00 AM"
echo "  - merge-gap-check.timer: Weekly on Sundays at 9:00 AM"
echo ""
echo "Check status:"
echo "  systemctl --user status merge-update.timer"
echo "  systemctl --user status merge-gap-check.timer"
echo ""
echo "View logs:"
echo "  journalctl --user -u merge-update -f"
echo "  tail -f /opt/geospatial_backend/logs/merge_operational_*.log"
echo ""
echo "Manual run (for testing):"
echo "  python3 /opt/geospatial_backend/app/run_merge_operational.py"
echo "  python3 /opt/geospatial_backend/app/check_merge_gaps.py"
echo ""
