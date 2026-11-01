## MODIFIED Requirements

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
