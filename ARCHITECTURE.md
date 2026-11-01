# Katzenschreck System Architecture

## High-Level Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IP Camera     │    │  Katzenschreck  │    │  Results folder │
│  (RTSP Stream)  │───▶│     System      │───▶│ (Detection JPGs)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
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

## Detailed System Architecture

```mermaid
graph TB
    %% Input Layer
    Camera[IP Camera<br/>RTSP Stream]
    
    %% Core Application Layer
    subgraph "Katzenschreck Application"
        Main[main.py<br/>Entry Point]
        Config[config.py<br/>Configuration Manager]
        
        subgraph "Processing Pipeline"
            Stream[stream_processor.py<br/>Main Processing Loop]
            Detector[object_detector.py<br/>YOLO Detection]
            MQTT[mqtt_handler.py<br/>MQTT Communication]
        end
    end
    
    %% Storage Layer
    subgraph "Data Storage"
        FileSystem[File System<br/>Detection Images]
    end
    
    %% External Services
    MQTTBroker[MQTT Broker<br/>Message Queue]
    SmartHome[Smart Home Systems<br/>Automation Triggers]
    
    %% Data Flow
    Camera -->|RTSP Stream| Stream
    Main --> Config
    Main --> Stream
    
    Stream --> Detector
    Stream --> MQTT
    Stream --> FileSystem
    
    Config -.-> Stream
    Config -.-> MQTT
    
    MQTT --> MQTTBroker
    MQTTBroker --> SmartHome
    
    %% Styling
    classDef input fill:#e1f5fe
    classDef processing fill:#f3e5f5
    classDef storage fill:#e8f5e8
    classDef external fill:#fff3e0
    
    class Camera input
    class Main,Config,Stream,Detector,MQTT processing
    class FileSystem storage
    class MQTTBroker,SmartHome external
```

## Component Details

### Core Modules

#### 1. **main.py** - Application Entry Point
- Argument parsing
- Application initialization
- Error handling and logging

#### 2. **config.py** - Configuration Management
- Configuration file parsing
- Environment variable handling
- Parameter validation

#### 3. **stream_processor.py** - Main Processing Engine
- RTSP stream handling
- Frame processing coordination
- Error recovery and reconnection

#### 4. **object_detector.py** - AI Detection Core
- YOLO model integration
- Cat detection algorithms
- Ignore zone filtering
- Confidence threshold management

#### 5. **mqtt_handler.py** - Real-time Communications
- MQTT broker connection
- Detection event publishing
- Health monitoring (ping)
- Message formatting

### Data Flow

1. **Input**: IP Camera streams video via RTSP
2. **Processing**: Stream processor captures frames
3. **Detection**: YOLO analyzes frames for cats
4. **Notification**: MQTT messages sent to smart home systems
5. **Storage**: Annotated detection images saved to the results folder in the background
6. **Action**: External systems (sprinklers) triggered

### Storage

Detection images are written as `frame_<timestamp>.jpg` to the results folder. When the root
partition exceeds `usage_threshold`, the oldest images are deleted.

## Deployment Architecture

### Option A: Native Deployment
```
┌─────────────────────────────────┐
│         Host System             │
│  ┌─────────────────────────────┐│
│  │    Python Virtual Env       ││
│  │  ┌─────────────────────────┐││
│  │  │   Katzenschreck App     │││
│  │  └─────────────────────────┘││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

### Option B: Docker Deployment
```
┌─────────────────────────────────┐
│         Docker Host             │
│  ┌─────────────────────────────┐│
│  │   Katzenschreck Container   ││
│  │  ┌─────────────────────────┐││
│  │  │     Application         │││
│  │  │   + Dependencies        │││
│  │  └─────────────────────────┘││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

## Integration Points

### External Systems
- **MQTT Brokers**: Mosquitto, HiveMQ, AWS IoT Core
- **Smart Home**: Home Assistant, OpenHAB, NodeRED
- **Cameras**: Any RTSP-compatible IP camera

### Network Requirements
- **RTSP**: Camera stream access
- **MQTT**: Port 1883 (unencrypted) or 8883 (TLS)
- **HTTP/HTTPS**: Optional for web interfaces

## Performance Characteristics

- **Frame Processing**: ~1-5 FPS (depending on hardware)
- **Detection Latency**: <2 seconds from capture to MQTT
- **Storage**: ~100KB per detection image
- **CPU Usage**: Moderate (YOLO inference)
- **Memory**: ~500MB-2GB (model dependent)

## Security Considerations

- MQTT authentication required
- RTSP stream credentials
- File system permissions
- Network isolation recommended
