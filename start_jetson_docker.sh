#!/bin/bash

# Usage: ./start_jetson_docker.sh [config.txt]
# If no config file is specified, defaults to ./config.txt
# Environment variables:
#   NETWORK_MODE=host|bridge (default: host)
#   - host: Use host network (RTSP streams work directly, no port visibility)
#   - bridge: Use bridge network (ports visible in docker ps, requires RTSP IP config)
#   ALLOW_DIRTY=1 (build even with uncommitted changes, tagged <commit>-dirty)
# The image is built from the currently checked-out code and tagged with its commit.

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

# Network mode (default: host for RTSP compatibility)
NETWORK_MODE=${NETWORK_MODE:-host}

# Set container name based on camera_name
CONTAINER_NAME="katzenschreck-${CAMERA_NAME}"
RESULTS_DIR="./results_${CAMERA_NAME}"

echo "📋 Configuration:"
echo "   Config file: $CONFIG_FILE"
echo "   Camera name: $CAMERA_NAME"
echo "   Container name: $CONTAINER_NAME"
echo "   Results directory: $RESULTS_DIR"
echo "   Monitoring port: $MONITORING_PORT"
echo "   Network mode: $NETWORK_MODE"
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

# Build the Docker image from the checked-out code in this directory.
# Select the version with git first, e.g.: git fetch && git checkout <branch-or-commit>
# Set ALLOW_DIRTY=1 to build with uncommitted changes (e.g. for quick tests).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! git -C "$SCRIPT_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: $SCRIPT_DIR is not a git repository"
    exit 1
fi

GIT_COMMIT=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD)
GIT_BRANCH=$(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref HEAD)
if [ -n "$(git -C "$SCRIPT_DIR" status --porcelain --untracked-files=no)" ]; then
    if [ "${ALLOW_DIRTY:-0}" = "1" ]; then
        echo "⚠️  WARNING: Building with uncommitted changes (ALLOW_DIRTY=1)"
        GIT_COMMIT="${GIT_COMMIT}-dirty"
    else
        echo "❌ Error: Uncommitted changes in $SCRIPT_DIR:"
        git -C "$SCRIPT_DIR" status --short --untracked-files=no | sed 's/^/   /'
        echo "   Commit or stash them, or set ALLOW_DIRTY=1 to build anyway."
        exit 1
    fi
fi

IMAGE_NAME="katzenschreck-jetson"
echo "🔨 Building Jetson Docker image from ${GIT_BRANCH} @ ${GIT_COMMIT}..."
DOCKER_BUILDKIT=1 docker build -f "$SCRIPT_DIR/Dockerfile.jetson" \
    --build-arg GIT_COMMIT="${GIT_COMMIT}" \
    -t "${IMAGE_NAME}:${GIT_COMMIT}" \
    -t "${IMAGE_NAME}:latest" \
    "$SCRIPT_DIR" || { echo "❌ Docker build failed"; exit 1; }

# Stop and remove existing container if it exists
echo "🛑 Stopping existing container: $CONTAINER_NAME..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

# Run the Docker container with GPU support
echo "🚀 Starting Katzenschreck container: $CONTAINER_NAME..."

# Build network arguments based on mode
if [ "$NETWORK_MODE" = "bridge" ]; then
    NETWORK_ARGS="-p ${MONITORING_PORT}:${MONITORING_PORT}"
    echo "   Using bridge network with port mapping: ${MONITORING_PORT}:${MONITORING_PORT}"
else
    NETWORK_ARGS="--network host"
    echo "   Using host network (ports accessible directly on host)"
fi

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
    $NETWORK_ARGS \
    --shm-size=512m \
    --label "katzenschreck.monitoring.port=$MONITORING_PORT" \
    --label "katzenschreck.camera.name=$CAMERA_NAME" \
    --label "katzenschreck.network.mode=$NETWORK_MODE" \
    --label "katzenschreck.git.commit=$GIT_COMMIT" \
    "${IMAGE_NAME}:${GIT_COMMIT}"

echo ""
echo "✅ Container started successfully! (image ${IMAGE_NAME}:${GIT_COMMIT})"
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
echo "🏷️  Running commit: docker inspect -f '{{index .Config.Labels \"katzenschreck.git.commit\"}}' $CONTAINER_NAME"
echo "⏪ Available versions: docker images $IMAGE_NAME"
