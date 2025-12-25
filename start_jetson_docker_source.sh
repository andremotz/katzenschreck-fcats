#!/bin/bash

# Build and start script for Katzenschreck with source-compiled PyTorch
# WARNUNG: Build dauert 3-5 Stunden auf Jetson Nano!

set -e

echo "🔨 Building Jetson Docker image with source-compiled PyTorch..."
echo "⚠️  WARNUNG: Dieser Build dauert 3-5 Stunden!"
echo ""

# BuildKit ist ERFORDERLICH für --mount Option
# Aktiviere BuildKit explizit
export DOCKER_BUILDKIT=1

if docker buildx version >/dev/null 2>&1; then
    echo "✅ BuildKit verfügbar - verwende optimiertes Build"
else
    echo "⚠️  WARNING: BuildKit wird benötigt für CUDA-Mount!"
    echo "   Installiere buildx oder aktiviere BuildKit in /etc/docker/daemon.json"
fi

# Build the Docker image
# WICHTIG: CUDA muss vom Host-System gemountet werden
echo "🔨 Building Docker image..."
echo "📦 Mounting CUDA from host system..."

# Finde CUDA-Pfad auf dem Host-System
CUDA_PATH=$(find /usr/local -name nvcc 2>/dev/null | head -1 | xargs dirname | xargs dirname)
if [ -z "$CUDA_PATH" ]; then
    CUDA_PATH="/usr/local/cuda-11.4"
fi

if [ ! -f "$CUDA_PATH/bin/nvcc" ]; then
    echo "⚠️  WARNING: CUDA not found at $CUDA_PATH"
    echo "   Trying to find CUDA..."
    CUDA_PATH=$(find /usr/local -name nvcc 2>/dev/null | head -1 | xargs dirname | xargs dirname)
fi

if [ -f "$CUDA_PATH/bin/nvcc" ]; then
    echo "✅ Found CUDA at: $CUDA_PATH"
    echo "🔧 Building with BuildKit and CUDA mount..."
    DOCKER_BUILDKIT=1 docker build --mount type=bind,source=$CUDA_PATH,target=$CUDA_PATH,readonly \
        -f Dockerfile.jetson.source \
        -t katzenschreck:jetson-source .
else
    echo "❌ ERROR: CUDA not found! Please install CUDA or specify CUDA_PATH"
    exit 1
fi

# Stop and remove existing container if it exists
echo "🛑 Stopping existing container..."
docker stop katzenschreck-source 2>/dev/null || true
docker rm katzenschreck-source 2>/dev/null || true

# Create results directory if it doesn't exist
mkdir -p ./results

# Run the Docker container
echo "🚀 Starting Katzenschreck container..."
docker run -d \
    --name katzenschreck-source \
    --runtime nvidia \
    --restart unless-stopped \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    -v ./config.txt:/katzenschreck/config.txt:ro \
    -v ./results:/katzenschreck/results \
    --network host \
    katzenschreck:jetson-source

echo ""
echo "✅ Container gestartet!"
echo ""
echo "📊 View logs with: docker logs -f katzenschreck-source"
echo "🛑 Stop with: docker stop katzenschreck-source"
echo ""
echo "🧪 Test CUDA:"
echo "   docker exec katzenschreck-source /usr/local/bin/python3.11 -c \"import torch; print(f'CUDA Available: {torch.cuda.is_available()}')\""

