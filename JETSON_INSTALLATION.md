# Jetson Orin Installation Guide

This document describes all installations and configurations performed on the NVIDIA Jetson Orin to build and run the Katzenschreck Docker image.

## Overview

- **Hardware**: NVIDIA Jetson Orin
- **JetPack Version**: R36 (4.7)
- **CUDA Version**: Included in JetPack (CUDA 11.4 compatible)
- **Python Version**: 3.10.12
- **Git Version**: 2.34.1
- **Docker Version**: 29.1.5

## Prerequisites

The Jetson Orin comes with JetPack R36 pre-installed, which includes:
- Ubuntu 22.04 (Jammy)
- CUDA toolkit
- NVIDIA drivers
- Basic system packages

## Installation Steps

### 1. System Updates

First, update the system to ensure all packages are up to date:

```bash
sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y
```

### 2. Install Basic Utilities

Install useful system utilities for monitoring and terminal management:

```bash
# Install btop (system monitor)
sudo apt install btop

# Install tmux (terminal multiplexer)
sudo apt update && sudo apt install tmux

# Install nano (text editor)
sudo apt install nano
```

### 3. Install Docker

Docker was initially installed via the default Ubuntu package, but this was removed and replaced with the official Docker CE installation for better compatibility and features.

#### 3.1 Remove Old Docker Installation

```bash
# Remove old Docker packages
sudo apt remove -y docker docker-engine docker.io containerd runc
```

#### 3.2 Install Docker Dependencies

```bash
# Update package index
sudo apt update

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg lsb-release
```

#### 3.3 Add Docker GPG Key

```bash
# Create keyring directory
sudo mkdir -p /etc/apt/keyrings

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

#### 3.4 Add Docker Repository

```bash
# Add Docker repository for ARM64 architecture
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

#### 3.5 Install Docker

```bash
# Update package index with new repository
sudo apt update

# Install Docker CE and plugins
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

#### 3.6 Verify Docker Installation

```bash
# Check Docker version
docker --version
# Expected output: Docker version 29.1.5, build 0e6fee6
```

### 4. Install NVIDIA Container Toolkit

The NVIDIA Container Toolkit is required to enable GPU access from within Docker containers.

#### 4.1 Install NVIDIA Container Toolkit

```bash
sudo apt update
sudo apt install -y nvidia-container-toolkit
```

#### 4.2 Configure Docker to Use NVIDIA Runtime

```bash
# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker

# Restart Docker service
sudo systemctl restart docker
```

#### 4.3 Verify NVIDIA Runtime Configuration

```bash
# Check if NVIDIA runtime is available
sudo docker info | grep -i nvidia
# Expected output should show "nvidia" in the runtimes list
```

The Docker daemon configuration file (`/etc/docker/daemon.json`) should now contain:

```json
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    }
}
```

### 5. Install Python Tools

Install Python package manager and Jetson monitoring tools:

```bash
# Install Python pip and setuptools
sudo apt install -y python3-pip python3-setuptools

# Install jetson-stats for system monitoring
sudo pip3 install -U jetson-stats
```

After installation, you can use `jtop` to monitor the Jetson system status.

### 6. Clone Repository

Clone the Katzenschreck repository:

```bash
git clone https://github.com/andremotz/katzenschreck-fcats.git
cd katzenschreck-fcats
```

## Verification

### Test Docker Installation

```bash
# Check Docker version
docker --version

# Check Docker service status
sudo systemctl status docker

# Verify NVIDIA runtime is configured
sudo docker info | grep -i runtime
```

### Test NVIDIA Container Runtime

You can test GPU access in a container using the ultralytics base image:

```bash
docker run --rm --runtime nvidia ultralytics/ultralytics:latest-jetson nvidia-smi
```

### Test Katzenschreck Build

Build the Docker image:

```bash
sudo ./start_jetson_docker.sh
```

Or manually:

```bash
docker build -f Dockerfile.jetson \
    --build-arg GIT_BRANCH=main \
    -t katzenschreck-jetson .
```

## Installed Packages Summary

### Docker Packages
- `docker-ce` (5:29.1.5-1~ubuntu.22.04~jammy)
- `docker-ce-cli` (5:29.1.5-1~ubuntu.22.04~jammy)
- `containerd.io`
- `docker-buildx-plugin` (0.30.1-1~ubuntu.22.04~jammy)
- `docker-compose-plugin` (5.0.2-1~ubuntu.22.04~jammy)

### NVIDIA Container Toolkit Packages
- `nvidia-container-toolkit` (1.16.2-1)
- `nvidia-container-toolkit-base` (1.16.2-1)
- `libnvidia-container1` (1.16.2-1)
- `libnvidia-container-tools` (1.16.2-1)

### System Utilities
- `btop` - System monitor
- `tmux` - Terminal multiplexer
- `nano` - Text editor
- `python3-pip` - Python package manager
- `python3-setuptools` - Python setuptools

### Python Packages (via pip)
- `jetson-stats` - Jetson system monitoring tool

## Configuration Files

### Docker Configuration
- **Location**: `/etc/docker/daemon.json`
- **Content**: NVIDIA runtime configuration

### System Service
- **Docker Service**: Enabled and running
- **Status**: Active since installation

## Notes

1. **Docker Permissions**: By default, Docker commands require `sudo`. To run Docker without sudo, add your user to the `docker` group:
   ```bash
   sudo usermod -aG docker $USER
   ```
   Then log out and log back in for the changes to take effect.

2. **NVIDIA Runtime**: The NVIDIA Container Toolkit must be installed and configured before building or running GPU-accelerated containers.

3. **JetPack Version**: The system is running JetPack R36 (4.7), which provides CUDA 11.4 compatibility. The Docker base image `ultralytics/ultralytics:latest-jetson-jetpack5` is compatible with this version.

4. **System Monitoring**: Use `jtop` (after installing jetson-stats) to monitor GPU usage, temperature, and power consumption.

## References

- [Docker Installation Guide for Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [NVIDIA Container Toolkit Documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- [Jetson Stats Documentation](https://github.com/rbonghi/jetson_stats)
- [Ultralytics Docker Images](https://hub.docker.com/r/ultralytics/ultralytics)

## Troubleshooting

### Docker Service Not Running

```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker
```

### NVIDIA Runtime Not Available

```bash
# Reconfigure NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker

# Restart Docker
sudo systemctl restart docker

# Verify configuration
sudo docker info | grep -i nvidia
```

### Permission Denied Errors

If you encounter permission errors when running Docker commands:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, or run:
newgrp docker
```

### Build Failures

If the Docker build fails, check:

1. Network connectivity (for pulling base images)
2. Available disk space: `df -h`
3. Docker service status: `sudo systemctl status docker`
4. NVIDIA runtime configuration: `sudo docker info | grep -i nvidia`
