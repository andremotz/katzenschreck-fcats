# mqtt-alerting Specification

## Purpose
Notify the home automation (Home Assistant) about detections via MQTT as fast as possible, so that it can trigger the sprinkler, and signal that the detector is alive.

## Requirements

### Requirement: Detection message
For each accepted detection the system SHALL publish to `{mqtt_topic}/{class_name}` (e.g. `object_detection/Cat`) a JSON payload with `time`, `class` and `confidence`, using QoS 0.

#### Scenario: Cat detected
- **WHEN** a cat is detected above the threshold
- **THEN** a message `{"time": ..., "class": "Cat", "confidence": ...}` is published to `{mqtt_topic}/Cat`

### Requirement: Heartbeat
While connected, the system SHALL publish `{"timestamp": <unix seconds>}` to `{mqtt_topic}/ping` every 30 seconds, but only if a frame has completed object detection within the last `liveness_timeout` seconds (default 60). The heartbeat therefore means "detection is running", not only "the process is alive".

#### Scenario: Idle garden
- **WHEN** nothing is detected for an hour while frames are processed normally
- **THEN** ping messages keep arriving every 30 seconds

#### Scenario: Detection hangs
- **WHEN** no frame has completed detection for longer than `liveness_timeout` (e.g. GPU memory failure, hung inference, camera unreachable)
- **THEN** no ping messages are published until detection completes again

#### Scenario: Startup
- **WHEN** the detector has started but not yet processed its first frame
- **THEN** no ping messages are published

### Requirement: Persistent connection with auto-reconnect
The system SHALL keep one persistent MQTT connection with a unique client id (`katzenschreck_{camera_name}_{timestamp}`) and SHALL reconnect automatically when the broker becomes unavailable.

#### Scenario: Broker restart
- **WHEN** the broker restarts
- **THEN** the client reconnects without restarting the application

### Requirement: Alert before storage
The MQTT message SHALL be published before the detection image is saved, and saving SHALL NOT delay the publish. The timestamp SHALL be taken before detection runs.

#### Scenario: Slow disk
- **WHEN** saving the detection image is slow
- **THEN** the detection message is still published without waiting for it
