# stream-ingestion Specification

## Purpose
Read frames from the camera's RTSP stream so that detection always works on a current image, and recover automatically when the stream stalls or the camera drops off the network.

## Requirements

### Requirement: Latest-frame delivery
In `continuous` mode (default) the system SHALL read the RTSP stream on a dedicated thread and keep only the most recent decoded frame, so that processing never works through a backlog of buffered frames.

#### Scenario: Processing slower than the camera frame rate
- **WHEN** detection takes longer than the interval between camera frames
- **THEN** intermediate frames are dropped and the next processed frame is the latest one received

### Requirement: Connection mode selection
The system SHALL support the connection modes `continuous` and `reconnect_per_frame`, selected via `rtsp_connection_mode`, and SHALL fall back to `continuous` for unknown values.

#### Scenario: Reconnect per frame
- **WHEN** `rtsp_connection_mode=reconnect_per_frame`
- **THEN** the stream is opened, exactly one frame is read, and the stream is closed again for every processed frame

### Requirement: Configurable transport
The system SHALL use the RTSP transport configured in `rtsp_transport` (`udp` or `tcp`, default `udp`) with low-delay FFmpeg options.

#### Scenario: Invalid transport value
- **WHEN** `rtsp_transport` is neither `udp` nor `tcp`
- **THEN** `udp` is used

### Requirement: Automatic reconnection
The reader SHALL reconnect with exponential backoff (starting at 2 s, capped at 30 s) when the stream cannot be opened, and SHALL reconnect after 10 consecutive grab or read failures.

#### Scenario: Camera temporarily unreachable
- **WHEN** opening the stream fails because the camera is unreachable
- **THEN** the reader retries with increasing delay until the stream can be opened again

### Requirement: Stale frame guard
The system SHALL NOT run detection on a frame older than `max_frame_age` seconds (default 10). In `continuous` mode it SHALL request a reconnect, and the reader thread SHALL release and re-open its own capture.

#### Scenario: Stream freezes while the connection stays open
- **WHEN** no new frame has arrived for longer than `max_frame_age`
- **THEN** the stale frame is discarded, no detection or MQTT message is produced from it, and the reader re-opens the stream

#### Scenario: Repeated reconnect requests
- **WHEN** a reconnect has already been requested and not yet performed
- **THEN** further requests have no additional effect

### Requirement: Frame normalisation
Frames larger than Full HD SHALL be downscaled to 1920x1080 before detection.

#### Scenario: 4K camera
- **WHEN** the camera delivers 3840x2160 frames
- **THEN** detection runs on a 1920x1080 version of the frame
