#!/bin/bash

# Katzenschreck systemd Service Installation Script
# This script installs Katzenschreck as a systemd user service

set -e

echo "🐱 Installing Katzenschreck as systemd service"
echo "=============================================="

# Get the directory where this script is located (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/katzenschreck.service"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Check if start_script.sh exists
if [ ! -f "$SCRIPT_DIR/start_script.sh" ]; then
    echo "❌ Error: start_script.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Run setup using start_script.sh (venv, dependencies, models)
echo "🔧 Running setup via start_script.sh..."
echo "   (This will create venv, install dependencies, and download models if needed)"
cd "$SCRIPT_DIR"
bash "$SCRIPT_DIR/start_script.sh" --setup-only

# Create systemd user directory if it doesn't exist
echo "📁 Creating systemd user directory..."
mkdir -p "$SYSTEMD_USER_DIR"

# Replace placeholders in service file
INSTALLED_SERVICE="$SYSTEMD_USER_DIR/katzenschreck.service"
sed "s|PROJECT_DIR_PLACEHOLDER|$SCRIPT_DIR|g" "$SERVICE_FILE" > "$INSTALLED_SERVICE"

echo "📝 Service file installed to: $INSTALLED_SERVICE"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl --user daemon-reload

# Enable service (start on boot)
echo "✅ Enabling service (auto-start on boot)..."
systemctl --user enable katzenschreck.service

# Start service
echo "🚀 Starting service..."
systemctl --user start katzenschreck.service

# Wait a moment for service to start
sleep 2

# Check service status
echo ""
echo "📊 Service status:"
systemctl --user status katzenschreck.service --no-pager -l || true

echo ""
echo "✅ Installation complete!"
echo ""
echo "Useful commands:"
echo "  Check status:    systemctl --user status katzenschreck"
echo "  View logs:        journalctl --user -u katzenschreck -f"
echo "  Stop service:     systemctl --user stop katzenschreck"
echo "  Start service:    systemctl --user start katzenschreck"
echo "  Restart service:  systemctl --user restart katzenschreck"
echo "  Disable service:  systemctl --user disable katzenschreck"

