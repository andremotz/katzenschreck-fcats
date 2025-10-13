#!/bin/bash

# Fix script for Jetson ultralytics:jetpack5 container
# Run this inside the container to fix OpenCV and dependency issues

echo "🔧 Fixing Jetson Container Issues"
echo "=================================="

# Activate virtual environment if it exists
if [ -d "/katzenschreck/cat_detector/venv" ]; then
    echo "🐍 Activating virtual environment..."
    source /katzenschreck/cat_detector/venv/bin/activate
fi

# Fix OpenCV issues by uninstalling headless version and installing full version
echo "🔧 Fixing OpenCV compatibility..."
pip uninstall -y opencv-python-headless || true
pip install --no-cache-dir opencv-python==4.8.1.78

# Install missing dependencies
echo "📦 Installing additional dependencies..."
pip install --no-cache-dir \
    paho-mqtt==1.6.1 \
    mysql-connector-python==8.0.33

# Verify OpenCV installation
echo "✅ Verifying OpenCV installation..."
python3 -c "
import cv2
print(f'OpenCV version: {cv2.__version__}')
try:
    # Test if DictValue is available
    from cv2.dnn import DictValue
    print('✅ OpenCV DictValue is available')
except AttributeError:
    print('❌ OpenCV DictValue is not available')
except ImportError:
    print('❌ OpenCV dnn module import failed')
"

# Test the application
echo "🧪 Testing application..."
cd /katzenschreck
python3 -c "
try:
    from cat_detector.stream_processor import StreamProcessor
    print('✅ StreamProcessor import successful')
except Exception as e:
    print(f'❌ StreamProcessor import failed: {e}')
"

echo "🎉 Fix completed! You can now run the application."
