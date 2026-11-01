# Architecture Decision Records

Decisions that shaped Katzenschreck, reconstructed from the Git history (2024-11 to 2026-11).
Each record names the commits it is based on. New decisions get the next number; superseded
records stay and are marked as such.

What the system must do lives in `openspec/specs/`. ADRs record *why* it is built this way.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-mqtt-as-integration-interface.md) | MQTT as the only interface to home automation | Accepted |
| [0002](0002-alert-first-background-storage.md) | Alert first, store in the background | Accepted |
| [0003](0003-threaded-latest-frame-rtsp-reader.md) | Threaded latest-frame RTSP reader | Accepted |
| [0004](0004-skip-stale-frames.md) | Skip stale frames instead of detecting on them | Accepted |
| [0005](0005-yolo11x-with-hardware-specific-inference.md) | YOLO11x everywhere, tune inference per hardware | Accepted |
| [0006](0006-docker-on-jetpack6-base-image.md) | Docker on the Ultralytics JetPack 6 image for Jetson | Accepted |
| [0007](0007-build-image-from-local-checkout.md) | Build the image from the local checkout | Accepted, supersedes Git-clone build (2496d93) |
| [0008](0008-one-container-per-camera.md) | One container per camera | Accepted |
| [0009](0009-images-in-mariadb.md) | Store images as BLOBs in MariaDB | Superseded by 0012 |
| [0010](0010-key-value-config-file.md) | Single key=value config file, mounted at runtime | Accepted |
| [0011](0011-agpl-license.md) | AGPL-3.0 license | Accepted |
| [0012](0012-remove-database-archive.md) | Remove the database archive | Accepted, supersedes 0009 |

## Template

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD
- Commits: <hashes>

## Context
## Decision
## Consequences
```
