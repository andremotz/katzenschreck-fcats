# object-detection Specification

## Purpose
Detect cats (and persons) in camera frames with a YOLO model and decide which detections should trigger the deterrent.

## Requirements

### Requirement: Target classes
The system SHALL report detections of the COCO classes Person (id 0) and Cat (id 15) and SHALL ignore all other classes.

#### Scenario: Dog in frame
- **WHEN** the model detects only a dog
- **THEN** no detection is reported

### Requirement: Confidence threshold
A detection SHALL only be acted on when its confidence is strictly greater than `confidence_threshold` (default 0.5).

#### Scenario: Low-confidence cat
- **WHEN** a cat is detected with confidence 0.35 and the threshold is 0.5
- **THEN** the detection is logged as skipped and no MQTT message is sent

### Requirement: Ignore zone
When `ignore_zone` is configured as relative coordinates `x_min,y_min,x_max,y_max` (0.0–1.0), detections whose bounding box overlaps that zone SHALL be skipped.

#### Scenario: Cat inside ignore zone
- **WHEN** a cat's bounding box overlaps the configured ignore zone
- **THEN** the detection is skipped

### Requirement: Model selection
The system SHALL use the model configured in `yolo_model` (absolute path or path relative to the project root) and SHALL default to `yolo11x.pt` when none is configured.

#### Scenario: Custom trained weights
- **WHEN** `yolo_model=runs/train15/weights/best.pt`
- **THEN** the weights are loaded from that path relative to the project root

### Requirement: Hardware-specific inference
The system SHALL detect whether it runs on an NVIDIA Jetson, natively or inside a container, and SHALL then run inference on the GPU with FP16 and an input size of 640. On other hardware it SHALL use an input size of 1280. Setting `hardware_type` SHALL override detection.

#### Scenario: Jetson container without override
- **WHEN** the system runs in a Docker container on a Jetson without `hardware_type` set
- **THEN** it is detected as Jetson via `/etc/nv_tegra_release` or the CUDA device name, and GPU FP16 inference is used

#### Scenario: Forced hardware type
- **WHEN** `hardware_type=jetson` is set
- **THEN** Jetson inference settings are used regardless of detection
