#!/bin/bash


# Build the Docker image
# Set GIT_BRANCH environment variable to use a specific branch (default: main)
GIT_BRANCH=${GIT_BRANCH:-main}
echo "🔨 Building Jetson Docker image from branch: ${GIT_BRANCH}..."
docker build -f Dockerfile.jetson \
    --build-arg GIT_BRANCH=${GIT_BRANCH} \
    -t katzenschreck-jetson .

# Stop and remove existing container if it exists
echo "🛑 Stopping existing container..."
docker stop katzenschreck 2>/dev/null || true
docker rm katzenschreck 2>/dev/null || true

# Create results directory if it doesn't exist
mkdir -p ./results

# Run the Docker container
echo "🚀 Starting Katzenschreck container..."
docker run -d \
    --name katzenschreck \
    --runtime nvidia \
    --restart unless-stopped \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    -v ./config.txt:/katzenschreck/config.txt:ro \
    -v ./results:/katzenschreck/results \
    --network host \
    katzenschreck-jetson

echo "📊 View logs with: docker logs -f katzenschreck"
echo "🛑 Stop with: docker stop katzenschreck"
