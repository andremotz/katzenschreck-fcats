#!/bin/bash

# Katzenschreck Universal Start Script
# For native operation: installs all dependencies from requirements.txt

# Check if running as systemd service (skip git operations)
if [ -z "$SYSTEMD_SERVICE" ]; then
    echo "🐱 Starting Katzenschreck - Universal Detection System"
    echo "======================================================"
    
    # Get the latest changes
    echo "📥 Updating repository..."
    git config --global credential.helper store
    git pull https://github.com/andremotz/katzenschreck.git || true
    
    # Remove config.txt from index (only if it exists in git)
    git rm --cached config.txt 2>/dev/null || true
else
    echo "🐱 Starting Katzenschreck (systemd service mode)"
    echo "======================================================"
fi

# Repository directory, which is the same as this script's directory + /cat_detector
REPO_DIR=$(pwd)/cat_detector

# Virtual environment directory
# Set VENV_DIR based on REPO_DIR
VENV_DIR="${REPO_DIR}/venv"

# Requirements file (always use requirements.txt for native operation)
REQUIREMENTS_FILE="${REPO_DIR}/requirements.txt"

# Change to repository directory
cd $REPO_DIR

# Create virtual environment if it doesn't exist
VENV_JUST_CREATED=false
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv $VENV_DIR
    VENV_JUST_CREATED=true
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source $VENV_DIR/bin/activate

# Check if requirements need to be installed
INSTALL_MARKER="${VENV_DIR}/.requirements_installed"

SHOULD_INSTALL=false

# If venv was just created, always install
if [ "$VENV_JUST_CREATED" = true ]; then
    SHOULD_INSTALL=true
    echo "📦 New virtual environment detected, installing requirements..."
# If marker doesn't exist, install
elif [ ! -f "$INSTALL_MARKER" ]; then
    SHOULD_INSTALL=true
    echo "📦 Installation marker not found, installing requirements..."
# If requirements file is newer than marker, install
elif [ -f "$REQUIREMENTS_FILE" ] && [ "$REQUIREMENTS_FILE" -nt "$INSTALL_MARKER" ]; then
    SHOULD_INSTALL=true
    echo "📦 Requirements file updated, reinstalling..."
# Check if key packages are actually installed
elif ! python3 -c "import torch" 2>/dev/null; then
    SHOULD_INSTALL=true
    echo "📦 Key packages missing, installing requirements..."
fi

if [ "$SHOULD_INSTALL" = true ]; then
    echo "📦 Installing/updating requirements from requirements.txt..."
    
    # Install requirements (includes numpy==1.26.4 and torch==2.2.2)
    pip install -r "$REQUIREMENTS_FILE"
    
    # Create marker file
    touch "$INSTALL_MARKER"
    echo "✅ Requirements installed successfully!"
else
    echo "✅ Requirements are up to date. Skipping installation."
fi

# Check if --setup-only flag is set
if [ "$1" = "--setup-only" ]; then
    echo "✅ Setup complete! (--setup-only flag detected, skipping Python start)"
    deactivate
    exit 0
fi

# Check if --run-only flag is set (skip setup, just run)
if [ "$1" = "--run-only" ]; then
    # Verify venv exists
    if [ ! -d "$VENV_DIR" ]; then
        echo "❌ Error: Virtual environment not found at $VENV_DIR"
        echo "   Please run './start_script.sh --setup-only' first to create the environment"
        exit 1
    fi
    
    # Activate virtual environment (if not already activated)
    if [ -z "$VIRTUAL_ENV" ]; then
        source $VENV_DIR/bin/activate
    fi
    
    # Run the Python script
    echo "🚀 Starting Katzenschreck detection system..."
    echo "======================================================"
    
    # Change to parent directory to run as module
    cd ..
    python3 -m cat_detector.main $REPO_DIR/results
    
    # Deactivate virtual environment (optional, when process ends)
    deactivate
    exit 0
fi

# Normal mode: Setup + Run
# Run the Python script
echo "🚀 Starting Katzenschreck detection system..."
echo "======================================================"

# Change to parent directory to run as module
cd ..
python3 -m cat_detector.main $REPO_DIR/results

# Deactivate virtual environment (optional, when process ends)
deactivate