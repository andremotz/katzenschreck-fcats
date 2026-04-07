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

# Read monitoring_port from config file (default: 8080)
MONITORING_PORT=$(grep -E "^monitoring_port=" "$CONFIG_FILE" | cut -d'=' -f2 | tr -d '[:space:]' || echo "8080")

# Set container name based on camera_name
CONTAINER_NAME="katzenschreck-${CAMERA_NAME}"
RESULTS_DIR="./results_${CAMERA_NAME}"

echo "📋 Configuration:"
echo "   Config file: $CONFIG_FILE"
echo "   Camera name: $CAMERA_NAME"
echo "   Container name: $CONTAINER_NAME"
echo "   Results directory: $RESULTS_DIR"
echo "   Monitoring port: $MONITORING_PORT"
echo ""

echo "🔍 Checking GPU/CUDA availability..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ nvidia-smi found on host"
else
    echo "⚠️  WARNING: nvidia-smi not found on host"
    echo "   GPU acceleration may not work properly"
fi

# Check if nvidia-container-runtime is available
if docker info 2>/dev/null | grep -q "nvidia"; then
    echo "✅ NVIDIA Container Runtime detected"
else
    echo "⚠️  WARNING: NVIDIA Container Runtime not detected in Docker"
    echo "   Install with: sudo apt-get install nvidia-container-runtime"
    echo "   Continuing anyway..."
fi
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

# Run the Docker container with GPU support
echo "🚀 Starting Katzenschreck container: $CONTAINER_NAME..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --gpus all \
    --restart unless-stopped \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e MONITORING_PORT="$MONITORING_PORT" \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:256,garbage_collection_threshold:0.6 \
    -v "$(realpath "$CONFIG_FILE"):/katzenschreck/config.txt:ro" \
    -v "$(realpath "$RESULTS_DIR"):/katzenschreck/results" \
    --network host \
    --shm-size=512m \
    --label "katzenschreck.monitoring.port=$MONITORING_PORT" \
    --label "katzenschreck.camera.name=$CAMERA_NAME" \
    katzenschreck-jetson

echo ""
echo "✅ Container started successfully!"
echo ""
echo "🔍 Validating GPU access in container..."
sleep 3

# Check GPU availability inside container
GPU_CHECK=$(docker exec "$CONTAINER_NAME" python3 -c "
import torch
if torch.cuda.is_available():
    print('GPU_OK')
    print(f'Device: {torch.cuda.get_device_name(0)}')
    print(f'CUDA Version: {torch.version.cuda}')
    props = torch.cuda.get_device_properties(0)
    print(f'Compute Capability: {props.major}.{props.minor}')
else:
    print('GPU_FAIL')
" 2>&1)

if echo "$GPU_CHECK" | grep -q "GPU_OK"; then
    echo "✅ GPU is ACCESSIBLE inside container!"
    echo "$GPU_CHECK" | grep -E "(Device|CUDA|Compute)" | sed 's/^/   /'
    echo ""
    echo "🎯 Expected performance: ~0.3-0.5s per frame detection"
else
    echo "❌ WARNING: GPU NOT accessible inside container!"
    echo "   The application will run on CPU (very slow: ~20-25s per frame)"
    echo "   Common causes:"
    echo "   - nvidia-container-runtime not installed"
    echo "   - Docker not restarted after nvidia-runtime installation"
    echo "   - Incompatible base image"
    echo ""
    echo "   Continuing anyway (application will work but slow)..."
fi

echo ""
echo "📊 View logs with: docker logs -f $CONTAINER_NAME"
echo "🎯 Monitor GPU usage: watch -n 1 tegrastats"
echo "🌐 Monitoring dashboard: http://localhost:$MONITORING_PORT"
echo "📈 API Status: curl http://localhost:$MONITORING_PORT/api/status"
echo "❤️  Health check: docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME"
echo "🛑 Stop with: docker stop $CONTAINER_NAME"
