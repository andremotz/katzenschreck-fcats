# monitoring Specification

## Purpose
Expose live status, timing and the current frame over HTTP so that delays and stream problems can be diagnosed, and provide the signal for the container health check.

## Requirements

### Requirement: Monitoring server
When `monitoring_enabled` is true (default), the system SHALL serve a REST API, a WebSocket (`/ws/monitoring`) and a web dashboard on `monitoring_port` (default 8080).

#### Scenario: Two cameras on one host
- **WHEN** two instances run with `monitoring_port=8080` and `monitoring_port=8081`
- **THEN** each serves its own dashboard on its port

### Requirement: Status endpoint
`GET /api/status` SHALL return at least `is_streaming`, `processing_alive`, `last_processed_time`, `seconds_since_processed`, `uptime`, `total_frames_processed`, `frames_skipped`, `last_frame_time` and `current_time`. `processing_alive` SHALL be true only if a frame completed object detection within the last `liveness_timeout` seconds.

#### Scenario: Health check
- **WHEN** the container health check calls `/api/status`
- **THEN** the container is reported healthy only if `is_streaming` and `processing_alive` are both true

#### Scenario: Detection stalled
- **WHEN** the stream is open but no frame has completed detection for longer than `liveness_timeout`
- **THEN** `processing_alive` is false and the container becomes unhealthy

### Requirement: Diagnostic endpoints
The system SHALL provide `/api/metrics`, `/api/detections`, `/api/queues`, `/api/timing`, `/api/timing/history`, `/api/frame` and `/api/all`, including frame age and a per-step timing breakdown (frame read, resize, detection, MQTT publish, queue waits).

#### Scenario: Investigating a delay
- **WHEN** alerts arrive late
- **THEN** `/api/timing` shows which processing step took the time and how old the processed frame was

### Requirement: Processing watchdog
The system SHALL exit the process with a non-zero status if the processing loop has not started a new iteration for `watchdog_timeout` seconds (default 120), so that the container restart policy restarts it.

#### Scenario: Inference hangs
- **WHEN** a call inside the processing loop blocks for longer than `watchdog_timeout`
- **THEN** the process exits and the container is restarted

#### Scenario: Camera unreachable
- **WHEN** the camera delivers no frames but the processing loop keeps polling
- **THEN** the process keeps running, pings stop and the container is unhealthy, but it is not restarted
