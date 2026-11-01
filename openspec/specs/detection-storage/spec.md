# detection-storage Specification

## Purpose
Keep a record of detections and periodic reference images on disk and in MariaDB, without letting storage slow down alerting or fill up the disk.

## Requirements

### Requirement: Annotated detection images on disk
For each accepted detection the system SHALL save the frame with drawn bounding boxes as `frame_<timestamp>.jpg` in the results directory.

#### Scenario: Cat detected
- **WHEN** a cat is detected above the threshold
- **THEN** an annotated JPEG is written to the results directory

### Requirement: Detections and hourly frames in the database
The system SHALL store each accepted detection, and one frame per hour with accuracy 0.0, in the `detections_images` table with `camera_name`, `accuracy`, the full JPEG and a 300 px wide thumbnail.

#### Scenario: Hourly reference image
- **WHEN** an hour has passed since the last reference frame
- **THEN** the current frame is stored with accuracy 0.0

### Requirement: Non-blocking background storage
Disk and database writes SHALL run on background worker threads with bounded queues (10 entries); when a queue is full the write SHALL be skipped rather than block processing.

#### Scenario: Database unreachable
- **WHEN** the database rejects connections
- **THEN** the error is logged and frame processing continues

### Requirement: Disk usage limit
Before saving an image the system SHALL delete the oldest `.jpg` files in the results directory while root partition usage is at or above `usage_threshold` (default 0.8).

#### Scenario: Disk almost full
- **WHEN** disk usage reaches 80 %
- **THEN** the oldest result images are deleted until usage is below 80 %
