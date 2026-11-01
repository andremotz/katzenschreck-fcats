## MODIFIED Requirements

### Requirement: Status endpoint
`GET /api/status` SHALL return at least `is_streaming`, `processing_alive`, `last_processed_time`, `seconds_since_processed`, `uptime`, `total_frames_processed`, `frames_skipped`, `last_frame_time` and `current_time`. `processing_alive` SHALL be true only if a frame completed object detection within the last `liveness_timeout` seconds.

#### Scenario: Health check
- **WHEN** the container health check calls `/api/status`
- **THEN** the container is reported healthy only if `is_streaming` and `processing_alive` are both true

#### Scenario: Detection stalled
- **WHEN** the stream is open but no frame has completed detection for longer than `liveness_timeout`
- **THEN** `processing_alive` is false and the container becomes unhealthy

## ADDED Requirements

### Requirement: Processing watchdog
The system SHALL exit the process with a non-zero status if the processing loop has not started a new iteration for `watchdog_timeout` seconds (default 120), so that the container restart policy restarts it.

#### Scenario: Inference hangs
- **WHEN** a call inside the processing loop blocks for longer than `watchdog_timeout`
- **THEN** the process exits and the container is restarted

#### Scenario: Camera unreachable
- **WHEN** the camera delivers no frames but the processing loop keeps polling
- **THEN** the process keeps running, pings stop and the container is unhealthy, but it is not restarted
