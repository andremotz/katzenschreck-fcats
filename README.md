# Katzenschreck-FCATS

(a) Fully Configurable Automated Tracking Software: A containerized end-to-end monitoring system that uses YOLO object detection to identify cats from ip-camera streams, stores results in a database, and sends real-time alerts via MQTT. This might be used to trigger your sprinkler...

**Tested and running 24/7 on Raspberry Pi 3, 4 and NVIDIA Jetson Xavier NX Developer Board** by the author, providing reliable cat detection in real-world garden environments.

![Katzenschreck Detection Example](photos/PHOTO-2025-09-24-11-28-54.jpg)

## Hardware Requirements & Performance

The inference script can run on a Raspberry Pi, but an accelerated device like a **Jetson Nano** is highly recommended for better performance.

**Real-world performance measurements (based on YOLO11x):**
- **Raspberry Pi 3**: Over 50 seconds per frame (which might be sufficient for detecting a cat)
- **Raspberry Pi 4**: ~22 seconds per frame
- **Jetson Xavier NX Developer Board**: 180ms per frame

## Features

- **Object Detection**: Automatic cat detection using YOLO
- **MQTT Integration**: Send notifications when detections occur
- **Database Storage**: Automatic frame storage every hour and detection images in MariaDB
- **RTSP Stream Support**: Support for IP cameras with RTSP protocol
- **Ignore Zones**: Configurable areas to be ignored
- **Image Generation**: Automatic creation of 300px wide thumbnails & detection-images.

## Installation & Setup

Follow these steps in order:

### 1. Set up database
First, create the database and required tables. Adjust the script to your needs:
```bash
mysql -u root -p < database_setup.sql
```

### 2. Configure the system
Create and edit the configuration file:
```bash
cp config.txt.example config.txt
# Edit config.txt with your RTSP stream, MQTT broker, and database settings
```

### 3. Run the application

Choose one of the following deployment methods:

#### Option A: Native Execution (Recommended for Development)
Use the start script to automatically set up the environment and run the system natively:
```bash
./start_script.sh
```

**Note**: The start script supports different modes:
- `./start_script.sh` - Full mode: Setup (venv, dependencies, models) + Run
- `./start_script.sh --setup-only` - Only setup: Creates venv, installs dependencies, downloads models
- `./start_script.sh --run-only` - Only run: Assumes setup is done, just starts the application

The start script will automatically:
- Create a Python virtual environment in `cat_detector/venv/`
- Install all required dependencies from `requirements.txt`
- Activate the virtual environment
- Run the detection system

#### Option B: Docker Container (Recommended for Production)
Build and run the application in a Docker container:

```bash
# Build the Docker image
docker build -t katzenschreck .

# Run the container with volume mounts for config and output
docker run -d \
  --name katzenschreck-container \
  -v $(pwd)/config.txt:/app/config.txt:ro \
  -v $(pwd)/results:/app/results \
  katzenschreck
```

**Docker Benefits**:
- Isolated environment with all dependencies
- Consistent deployment across different systems
- Easy scaling and orchestration
- No need to manage Python environments locally

#### Option C: systemd Service (Recommended for Production Native Setup)
Run Katzenschreck as a systemd user service for automatic startup and process management:

```bash
# Install the systemd service
./install_systemd_service.sh
```

The installation script will:
- Create a systemd user service configuration
- Enable automatic startup on boot
- Start the service immediately
- Configure logging via journald

**Service Management Commands**:
```bash
# Check service status
systemctl --user status katzenschreck

# View live logs
journalctl --user -u katzenschreck -f

# Stop/start/restart service
systemctl --user stop katzenschreck
systemctl --user start katzenschreck
systemctl --user restart katzenschreck

# Disable auto-start on boot
systemctl --user disable katzenschreck
```

**Uninstall the service**:
```bash
./uninstall_systemd_service.sh
```

**systemd Service Benefits**:
- Automatic startup on system boot
- Automatic restart on failure
- Centralized logging via journald
- Process management and monitoring
- No need to manually start the application

## Additional Documentation

This repository includes specialized documentation for Jetson devices:

- **[README_DOCKER_JETSON.md](README_DOCKER_JETSON.md)**: Complete guide for running Katzenschreck in a Docker container on NVIDIA Jetson devices. This is the recommended approach for production deployments on Jetson, as it provides a pre-configured environment with all dependencies (including PyTorch with CUDA support) already built and optimized.

- **[JETSON_PYTORCH_SETUP.md](JETSON_PYTORCH_SETUP.md)**: Step-by-step instructions for setting up PyTorch with CUDA support natively on Jetson Nano without Docker. This guide covers compiling Python 3.11 from source, building PyTorch and torchvision with CUDA support, and configuring the environment for optimal GPU acceleration. Use this if you prefer native installation or need to customize the Python/PyTorch setup.

**When to use which guide:**
- **Docker approach** (README_DOCKER_JETSON.md): Faster setup, easier maintenance, recommended for most users
- **Native approach** (JETSON_PYTORCH_SETUP.md): More control, custom Python versions, advanced configurations

## Manual Usage

If you prefer to run manually without automation:

```bash
cd cat_detector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py <output_folder>
```

## Architecture

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IP Camera     │    │  Katzenschreck  │    │   MariaDB       │    │  Schreckmonitor │
│  (RTSP Stream)  │───▶│     System      │───▶│   Database      │───▶│   Desktop-App   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  MQTT Broker    │
                       │  (Notifications)│
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Smart Home     │
                       │  Integration    │
                       │ (Sprinkler etc.)│
                       └─────────────────┘
```

### Detailed Architecture
```mermaid
graph TB
    Camera[IP Camera<br/>RTSP Stream]
    
    subgraph "Katzenschreck Application"
        Main[main.py<br/>Entry Point]
        Config[config.py<br/>Configuration]
        
        subgraph "Processing Pipeline"
            Stream[stream_processor.py<br/>Main Loop]
            Detector[object_detector.py<br/>YOLO Detection]
            DB[database_handler.py<br/>Database Ops]
            MQTT[mqtt_handler.py<br/>MQTT Comm]
        end
    end
    
    subgraph "Data Storage"
        MariaDB[(MariaDB<br/>Images & Metadata)]
        FileSystem[File System<br/>Detection Images]
    end
    
    MQTTBroker[MQTT Broker]
    SmartHome[Smart Home Systems]
    
    Camera -->|RTSP| Stream
    Main --> Config
    Main --> Stream
    Stream --> Detector
    Stream --> DB
    Stream --> MQTT
    Stream --> FileSystem
    Config -.-> Stream
    Config -.-> DB
    Config -.-> MQTT
    DB --> MariaDB
    MQTT --> MQTTBroker
    MQTTBroker --> SmartHome
```

> 📋 **Detailed Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md) for comprehensive system documentation, deployment options, and integration details.

## Configuration

The `config.txt` file contains all system configuration parameters. Copy `config.txt.example` to `config.txt` and adjust the values for your environment.

### RTSP Stream Configuration

- **`rtsp_stream_url`** (required): Full RTSP URL for the IP camera stream
  - Example: `rtsp://username:password@192.168.1.100:554/stream1`
- **`rtsp_transport`** (optional, default: `udp`): Transport protocol for RTSP stream
  - Options: `udp` (lower latency, recommended) or `tcp` (more reliable but higher latency)
- **`rtsp_low_delay`** (optional, default: `true`): Enable low delay mode for RTSP stream
  - Reduces buffering to minimize frame delay
- **`rtsp_connection_mode`** (optional, default: `continuous`): RTSP connection strategy
  - `continuous`: Maintains persistent connection (faster, but may buffer old frames)
  - `reconnect_per_frame`: Reconnects for each frame (slower, but ensures freshest frame)
  - Use `reconnect_per_frame` if you experience frame drift/delay issues

### MQTT Configuration

- **`mqtt_broker_url`** (required): MQTT broker hostname or IP address
- **`mqtt_broker_port`** (optional, default: `1883`): MQTT broker port
- **`mqtt_topic`** (required): MQTT topic for publishing detection alerts
- **`mqtt_username`** (required): MQTT authentication username
- **`mqtt_password`** (required): MQTT authentication password

### Database Configuration

- **`db_host`** (optional, default: `localhost`): MariaDB/MySQL database host
- **`db_user`** (optional, default: `katzenschreck_app`): Database username
- **`db_password`** (optional, default: `p7eWPjGeIRXtMvCJw--`): Database password
- **`db_database`** (optional, default: `katzenschreck`): Database name
- **`camera_name`** (optional, default: `cam_garten`): Camera identifier for database records

### Object Detection Configuration

- **`confidence_threshold`** (optional, default: `0.5`): Minimum confidence level (0.0-1.0) required for detections
  - Lower values = more detections (including false positives)
  - Higher values = fewer detections (only high-confidence matches)
- **`usage_threshold`** (optional, default: `0.8`): Disk usage threshold (0.0-1.0)
  - When exceeded, oldest images are automatically deleted to free space
- **`yolo_model`** (optional): Specific YOLO model to use
  - If not set, auto-detection based on hardware will be used
  - Options: `yolo11x.pt`, `yolo11l.pt`, `yolo11m.pt`, `yolo11s.pt`, `yolo11n.pt`
  - Larger models (x, l) = better accuracy but slower
  - Smaller models (s, n) = faster but less accurate
- **`ignore_zone`** (optional): Area to ignore for detections
  - Format: `x_min,y_min,x_max,y_max` as decimal values (0.0-1.0)
  - Example: `0.1,0.1,0.3,0.3` ignores the top-left 20% of the frame

### Monitoring Configuration

- **`monitoring_enabled`** (optional, default: `true`): Enable real-time monitoring web server
  - Provides web interface at `http://localhost:8080` for performance monitoring
- **`monitoring_port`** (optional, default: `8080`): Port for the monitoring web server

### Hardware Configuration

- **`hardware_type`** (optional): Override automatic hardware detection
  - Use when automatic detection fails (e.g., in Docker containers)
  - Options: `jetson`, `raspberry_pi`, `generic`

## Database Schema

The system automatically stores frames in the `detections_images` table:
- `camera_name`: Camera name
- `accuracy`: Accuracy value (0.0 for monitoring images, >0.0 for detections)
- `blob_jpeg`: JPEG image data as BLOB
- `thumbnail_jpeg`: 300px wide thumbnail as BLOB
- `created_at`: Storage timestamp

## Module Structure

The application is organized into modular components:

- **`config.py`**: Configuration management
- **`mqtt_handler.py`**: MQTT communication
- **`database_handler.py`**: Database operations and thumbnail creation
- **`object_detector.py`**: YOLO-based cat detection
- **`stream_processor.py`**: Video stream processing coordination
- **`main.py`**: Application entry point

## Detection Logic

- **Monitoring Images**: Saved every hour with accuracy = 0.0
- **Detection Images**: Saved when cats are detected with accuracy = YOLO confidence
- **File Storage**: Detection images also saved as annotated files in output folder
- **MQTT Notifications**: Real-time alerts sent for each detection

## TODO

### DevOps & Infrastructure
- [ ] Verify Docker container functionality
- [ ] Set up CI/CD pipeline (GitHub Actions/GitLab CI)
- [*] Implement health checks and monitoring endpoints
- [ ] Add Prometheus metrics collection
- [ ] Create Kubernetes deployment manifests
- [ ] Add environment-specific configurations (different locations!)

### Code Quality & Testing
- [ ] Add unit tests for all modules
- [ ] Implement integration tests
- [ ] Set up code coverage reporting
- [ ] Add linting and formatting (black, flake8, mypy)
- [ ] Add security scanning (bandit, safety)
- [ ] Implement automated dependency updates (Dependabot)

### Documentation & Usability
- [*] Create architecture diagrams
- [ ] Add troubleshooting guide
- [ ] Document performance tuning recommendations
- [*] Add screenshot
- [ ] Add changelog maintenance

### Security & Production Readiness
- [ ] Implement proper secret management and config management for Docker container
- [ ] Add SSL/TLS support for MQTT
