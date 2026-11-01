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
`GET /api/status` SHALL return at least `is_streaming`, `uptime`, `total_frames_processed`, `frames_skipped`, `last_frame_time` and `current_time`.

#### Scenario: Health check
- **WHEN** the container health check calls `/api/status`
- **THEN** the container is reported healthy only if `is_streaming` is true

### Requirement: Diagnostic endpoints
The system SHALL provide `/api/metrics`, `/api/detections`, `/api/queues`, `/api/timing`, `/api/timing/history`, `/api/frame` and `/api/all`, including frame age and a per-step timing breakdown (frame read, resize, detection, MQTT publish, queue waits).

#### Scenario: Investigating a delay
- **WHEN** alerts arrive late
- **THEN** `/api/timing` shows which processing step took the time and how old the processed frame was
