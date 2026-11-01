# mqtt-alerting Specification

## Purpose
Notify the home automation (Home Assistant) about detections via MQTT as fast as possible, so that it can trigger the sprinkler, and signal that the detector is alive.

## Requirements

### Requirement: Detection message
For each accepted detection the system SHALL publish to `{mqtt_topic}/{class_name}` (e.g. `object_detection/Cat`) a JSON payload with `time`, `class` and `confidence`, using QoS 0.

#### Scenario: Cat detected
- **WHEN** a cat is detected above the threshold
- **THEN** a message `{"time": ..., "class": "Cat", "confidence": ...}` is published to `{mqtt_topic}/Cat`

### Requirement: Alert has priority
The MQTT message SHALL be published before any image is saved to disk or database, and those saves SHALL NOT delay the publish. The timestamp SHALL be taken before detection runs.

#### Scenario: Slow database
- **WHEN** the database is slow or unreachable
- **THEN** detection messages are still published without waiting for it

### Requirement: Heartbeat
While connected, the system SHALL publish `{"timestamp": <unix seconds>}` to `{mqtt_topic}/ping` every 30 seconds.

#### Scenario: Idle garden
- **WHEN** nothing is detected for an hour
- **THEN** ping messages keep arriving every 30 seconds

### Requirement: Persistent connection with auto-reconnect
The system SHALL keep one persistent MQTT connection with a unique client id (`katzenschreck_{camera_name}_{timestamp}`) and SHALL reconnect automatically when the broker becomes unavailable.

#### Scenario: Broker restart
- **WHEN** the broker restarts
- **THEN** the client reconnects without restarting the application
