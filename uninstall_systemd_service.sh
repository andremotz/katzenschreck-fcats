#!/bin/bash

# Katzenschreck systemd Service Uninstallation Script

set -e

echo "🐱 Uninstalling Katzenschreck systemd service"
echo "=============================================="

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SYSTEMD_USER_DIR/katzenschreck.service"

# Check if service is running
if systemctl --user is-active --quiet katzenschreck.service; then
    echo "🛑 Stopping service..."
    systemctl --user stop katzenschreck.service
fi

# Disable service
if systemctl --user is-enabled --quiet katzenschreck.service; then
    echo "❌ Disabling service..."
    systemctl --user disable katzenschreck.service
fi

# Remove service file
if [ -f "$SERVICE_FILE" ]; then
    echo "🗑️  Removing service file..."
    rm "$SERVICE_FILE"
fi

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl --user daemon-reload

echo "✅ Uninstallation complete!"

