## ADDED Requirements

### Requirement: Non-blocking file storage
Detection images SHALL be written to disk by a background worker thread with a bounded queue (10 entries); when the queue is full the write SHALL be skipped rather than block processing.

#### Scenario: Slow disk
- **WHEN** writing images to disk is slower than detections arrive
- **THEN** images that do not fit in the queue are skipped, a warning is logged, and frame processing continues

## REMOVED Requirements

### Requirement: Detections and hourly frames in the database
**Reason**: The database archive was broken in production for months without being noticed; nobody depends on it. See ADR 0012.
**Migration**: Use the annotated detection images in the results directory (`results_<camera_name>/`). Existing rows in `detections_images` are not touched.

### Requirement: Non-blocking background storage
**Reason**: Replaced by "Non-blocking file storage", since there is no database write anymore.
**Migration**: None.
