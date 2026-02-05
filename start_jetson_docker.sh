#!/bin/bash

# Usage: ./start_jetson_docker.sh [config.txt]
# If no config file is specified, defaults to ./config.txt

# Get config file path from argument or use default
CONFIG_FILE=${1:-./config.txt}

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    echo "Usage: $0 [config.txt]"
    exit 1
fi

# Read camera_name from config file
CAMERA_NAME=$(grep -E "^camera_name=" "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]' || echo "")

# If camera_name is not found, use default
if [ -z "$CAMERA_NAME" ]; then
    echo "⚠️  Warning: camera_name not found in $CONFIG_FILE, using default 'katzenschreck'"
    CAMERA_NAME="katzenschreck"
fi

# Set container name based on camera_name
CONTAINER_NAME="katzenschreck-${CAMERA_NAME}"
RESULTS_DIR="./results_${CAMERA_NAME}"

echo "📋 Configuration:"
echo "   Config file: $CONFIG_FILE"
echo "   Camera name: $CAMERA_NAME"
echo "   Container name: $CONTAINER_NAME"
echo "   Results directory: $RESULTS_DIR"
echo ""

# Build the Docker image
# Set GIT_BRANCH environment variable to use a specific branch (default: main)
GIT_BRANCH=${GIT_BRANCH:-main}
echo "🔨 Building Jetson Docker image from branch: ${GIT_BRANCH}..."
docker build -f Dockerfile.jetson \
    --build-arg GIT_BRANCH=${GIT_BRANCH} \
    -t katzenschreck-jetson .

# Stop and remove existing container if it exists
echo "🛑 Stopping existing container: $CONTAINER_NAME..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

# Run the Docker container
echo "🚀 Starting Katzenschreck container: $CONTAINER_NAME..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --runtime nvidia \
    --restart unless-stopped \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    -v "$(realpath "$CONFIG_FILE"):/katzenschreck/config.txt:ro" \
    -v "$(realpath "$RESULTS_DIR"):/katzenschreck/results" \
    --network host \
    katzenschreck-jetson

echo ""
echo "✅ Container started successfully!"
echo "📊 View logs with: docker logs -f $CONTAINER_NAME"
echo "🛑 Stop with: docker stop $CONTAINER_NAME"
