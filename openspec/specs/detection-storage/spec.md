# detection-storage Specification

## Purpose
Keep annotated images of detections on disk, without letting storage slow down alerting or fill up the disk.

## Requirements

### Requirement: Annotated detection images on disk
For each accepted detection the system SHALL save the frame with drawn bounding boxes as `frame_<timestamp>.jpg` in the results directory.

#### Scenario: Cat detected
- **WHEN** a cat is detected above the threshold
- **THEN** an annotated JPEG is written to the results directory

### Requirement: Disk usage limit
Before saving an image the system SHALL delete the oldest `.jpg` files in the results directory while root partition usage is at or above `usage_threshold` (default 0.8).

#### Scenario: Disk almost full
- **WHEN** disk usage reaches 80 %
- **THEN** the oldest result images are deleted until usage is below 80 %

### Requirement: Non-blocking file storage
Detection images SHALL be written to disk by a background worker thread with a bounded queue (10 entries); when the queue is full the write SHALL be skipped rather than block processing.

#### Scenario: Slow disk
- **WHEN** writing images to disk is slower than detections arrive
- **THEN** images that do not fit in the queue are skipped, a warning is logged, and frame processing continues
