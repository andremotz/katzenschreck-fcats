#!/bin/bash
# Wrapper script to run Katzenschreck with venv activated
# This ensures the virtual environment is properly activated

# Get the directory where this script is located (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project directory
cd "$SCRIPT_DIR"

# Activate virtual environment
source "$SCRIPT_DIR/cat_detector/venv/bin/activate"

# Run the application
python -m cat_detector.main "$SCRIPT_DIR/cat_detector/results"

