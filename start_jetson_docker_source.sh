#!/bin/bash

# Build and start script for Katzenschreck with source-compiled PyTorch
# WARNUNG: Build dauert 3-5 Stunden auf Jetson Nano!

set -e

echo "🔨 Building Jetson Docker image with source-compiled PyTorch..."
echo "⚠️  WARNUNG: Dieser Build dauert 3-5 Stunden!"
echo ""

# Prüfe ob BuildKit verfügbar ist (empfohlen für besseres Caching)
if docker buildx version >/dev/null 2>&1; then
    echo "✅ BuildKit verfügbar - verwende optimiertes Build"
    export DOCKER_BUILDKIT=1
else
    echo "ℹ️  BuildKit nicht verfügbar - verwende Standard Build"
fi

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -f Dockerfile.jetson.source \
    -t katzenschreck:jetson-source .

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

