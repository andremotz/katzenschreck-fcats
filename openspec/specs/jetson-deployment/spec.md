# jetson-deployment Specification

## Purpose
Build and run the detector as a GPU-accelerated Docker container on NVIDIA Jetson (JetPack 6), one container per camera, in a reproducible and traceable way.

## Requirements

### Requirement: Build from local checkout
The image SHALL be built from the code checked out in the repository directory on the host. `start_jetson_docker.sh` SHALL refuse to build when tracked files have uncommitted changes, unless `ALLOW_DIRTY=1` is set.

#### Scenario: Uncommitted change
- **WHEN** a tracked file is modified and `ALLOW_DIRTY` is not set
- **THEN** the script lists the changes, exits with an error, and does not touch the running container

#### Scenario: Deploying another version
- **WHEN** the operator checks out a branch or commit and runs the script
- **THEN** the image contains exactly that checkout

### Requirement: Image traceability
Each image SHALL be tagged `katzenschreck-jetson:<short-commit>` (suffix `-dirty` when built with `ALLOW_DIRTY=1`) and `:latest`, and SHALL carry the commit in the `org.opencontainers.image.revision` label and `KATZENSCHRECK_GIT_COMMIT`. The container SHALL carry the label `katzenschreck.git.commit`.

#### Scenario: Which version is running
- **WHEN** the operator inspects the running container
- **THEN** the commit it was built from is visible from its labels

#### Scenario: Rollback
- **WHEN** a new version misbehaves
- **THEN** the container can be restarted from a previous `katzenschreck-jetson:<commit>` image without rebuilding

### Requirement: No secrets or results in the image
`config.txt` and `results*/` SHALL be excluded from the build context; the real `config.txt` SHALL be mounted read-only at runtime.

#### Scenario: Inspecting the image
- **WHEN** `/katzenschreck/config.txt` is read from a freshly built image
- **THEN** it contains only a placeholder

### Requirement: One container per camera
The container name SHALL be `katzenschreck-<camera_name>` and results SHALL be written to `results_<camera_name>/` on the host, so that several cameras can run on one host with different configs.

#### Scenario: Second camera
- **WHEN** the script is run with a second config file with another `camera_name` and `monitoring_port`
- **THEN** a second container runs alongside the first without conflicts

### Requirement: GPU runtime
The container SHALL run with `--gpus all`, restart policy `unless-stopped`, host networking by default (`NETWORK_MODE=bridge` optional), and the script SHALL verify after start that CUDA is available inside the container.

#### Scenario: GPU missing
- **WHEN** CUDA is not available in the started container
- **THEN** the script prints a warning that detection will run on CPU
