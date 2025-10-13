#!/bin/bash


# Build the Docker image
echo "🔨 Building Jetson Docker image..."
docker build -f Dockerfile.jetson -t katzenschreck-jetson .

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
    -v ./config.txt:/katzenschreck/config.txt:ro \
    -v ./results:/katzenschreck/results \
    --network host \
    katzenschreck-jetson

echo "✅ Katzenschreck container started successfully!"
echo "📊 View logs with: docker logs -f katzenschreck"
echo "🛑 Stop with: docker stop katzenschreck"
