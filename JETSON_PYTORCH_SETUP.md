# PyTorch CUDA Setup on Jetson Nano - Documentation

## Overview

To run Katzenschreck natively without Docker: This documentation describes the complete installation of PyTorch with CUDA support for Python 3.11 on a Jetson Nano (JetPack 6.3, CUDA 11.4).

## Prerequisites

- Jetson Nano with JetPack 6.3 (R35)
- Ubuntu 18/20
- Basic build tools and dependencies

## Steps

### 1. Compile and Install Python 3.11

```bash
# Install build dependencies for Python:
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev

# Download Python 3.11 source:
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar -xzf Python-3.11.9.tgz
cd Python-3.11.9

# Configure and compile (this takes 30-60 minutes):
./configure --enable-optimizations --prefix=/usr/local
make -j$(nproc)

# Install Python 3.11:
sudo make altinstall

# Link Python 3.11 globally:
sudo update-alternatives --install /usr/bin/python python /usr/local/bin/python3.11 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.11 1

# Verify installation:
python3.11 --version
# Should show: Python 3.11.9

# Create virtual environment with Python 3.11:
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install CUDA Toolkit and nvcc

```bash
# CUDA Toolkit is already installed (cuda-toolkit-11-4)
# Find nvcc:
find /usr/local -name nvcc 2>/dev/null
# Result: /usr/local/cuda-11.4/bin/nvcc

# Set PATH permanently:
echo 'export PATH=/usr/local/cuda-11.4/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verify:
nvcc --version
# Should show: Cuda compilation tools, release 11.4, V11.4.315
```

### 3. Install Build Dependencies

```bash
sudo apt install -y libopenblas-dev libblas-dev liblapack-dev libatlas-base-dev git cmake build-essential
```

### 4. Update CMake

```bash
# Remove old CMake version (3.16.3 is too old, PyTorch requires >= 3.18.0)
sudo apt remove -y cmake

# Install new CMake version:
wget https://github.com/Kitware/CMake/releases/download/v3.24.0/cmake-3.24.0-linux-aarch64.sh
chmod +x cmake-3.24.0-linux-aarch64.sh
sudo ./cmake-3.24.0-linux-aarch64.sh --skip-license --prefix=/usr/local

# Verify:
cmake --version
# Should show: cmake version 3.24.0
```

### 5. Compile PyTorch from Source

```bash
# Clone PyTorch:
cd ~
git clone --recursive --branch v2.1.0 https://github.com/pytorch/pytorch
cd pytorch
git submodule update --init --recursive

# Set environment variables for CUDA compilation:
export USE_CUDA=1
export USE_CUDNN=1
export TORCH_CUDA_ARCH_LIST="7.2"  # Jetson Nano Compute Capability
export CUDA_HOME=/usr/local/cuda-11.4
export CMAKE_CUDA_ARCHITECTURES="72"
export CMAKE_CUDA_COMPILER=/usr/local/cuda-11.4/bin/nvcc

# Install wheel (if not already present):
pip install wheel

# Compile PyTorch (takes 2-4 hours!):
python3.11 setup.py bdist_wheel

# After successful compilation, install:
cd ~/pytorch
pip install dist/torch-*.whl
```

### 6. Test CUDA Availability

```bash
# IMPORTANT: Change directory away from PyTorch repository, otherwise Python loads the repository instead of the installed version
cd ~/katzenschreck_wernberg

# Test:
python3.11 -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'Device Count: {torch.cuda.device_count()}'); print(f'CUDA Version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}'); print(f'Device Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

# Expected output:
# CUDA Available: True
# Device Count: 1
# CUDA Version: 11.4
# Device Name: Xavier (or similar)
```

### 7. Compile torchvision from Source (Required)

```bash
cd ~
git clone --recursive --branch v0.16.0 https://github.com/pytorch/vision
cd vision
python3.11 setup.py bdist_wheel
pip install dist/torchvision-*.whl
```

### 8. Check GPU Memory (without nvidia-smi)

```bash
# Check GPU memory via PyTorch:
python3.11 -c "import torch; print(f'GPU Memory Allocated: {torch.cuda.memory_allocated(0)/1024**2:.2f} MB'); print(f'GPU Memory Reserved: {torch.cuda.memory_reserved(0)/1024**2:.2f} MB'); print(f'GPU Memory Total: {torch.cuda.get_device_properties(0).total_memory/1024**2:.2f} MB')"
```

## Important Notes

1. **Compilation Time**: 
   - Python 3.11 compilation takes 30-60 minutes on Jetson Nano
   - PyTorch compilation takes 2-4 hours on Jetson Nano
   - Use `screen` or `tmux` for long-running processes

2. **Directory Change**: After installation, always change directory away from `~/pytorch`, otherwise Python loads the repository instead of the installed version.

3. **GPU Memory**: YOLO11x requires significant GPU memory. For "out of memory" errors:
   - Clear GPU memory cache: `torch.cuda.empty_cache()`
   - Use FP16 (half precision): `.half()`
   - Use smaller image size: `imgsz=640` instead of `1280`

4. **Environment Variables**: CUDA environment variables must be set for each new shell session, or permanently saved in `~/.bashrc`.

## Troubleshooting

### Problem: "CUDA Available: False"

- Check if PyTorch was compiled with CUDA libraries: `python3.11 -c "import torch; import os; lib_path = os.path.join(os.path.dirname(torch.__file__), 'lib'); files = os.listdir(lib_path); cuda_files = [f for f in files if 'cuda' in f.lower()]; print(f'CUDA libs: {cuda_files}')"`
- If no CUDA libraries are found, PyTorch was compiled without CUDA. Recompile with correct environment variables.

### Problem: "out of memory"

- Clear GPU memory cache: `torch.cuda.empty_cache()`
- Use FP16: `.half()`
- Use smaller model version (e.g., YOLO11n instead of YOLO11x)

### Problem: "nvcc: command not found"

- Set PATH: `export PATH=/usr/local/cuda-11.4/bin:$PATH`
- Save permanently in `~/.bashrc`

### Problem: "python3.11: command not found" after compilation

- Verify Python 3.11 is in PATH: `which python3.11`
- If not found, add to PATH: `export PATH=/usr/local/bin:$PATH`
- Or use full path: `/usr/local/bin/python3.11`

## Summary

The installation includes:

1. Compile and install Python 3.11 from source
2. Configure CUDA Toolkit and nvcc
3. Install build dependencies
4. Update CMake to version >= 3.18.0
5. Compile PyTorch from source with CUDA support
6. Compile torchvision from source (required)
7. Verify GPU memory availability

After successful installation, PyTorch should correctly detect CUDA and YOLO11x should run with GPU acceleration.
