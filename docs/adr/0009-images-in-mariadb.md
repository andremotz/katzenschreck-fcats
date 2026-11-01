# 0009. Store images as BLOBs in MariaDB

- Status: Accepted, under review
- Date: 2025-09-24
- Commits: 5c504a6, f327f40, e720904, fdc20db, b524305, ccce3f5

## Context
Detections and reference images should be available outside the device, e.g. for a gallery or for training data.

## Decision
Detection images (with confidence) and one reference frame per hour (accuracy 0.0) are stored as full-resolution JPEG plus a 300 px thumbnail in the `detections_images` table. Image size is handled on the database side by raising `max_allowed_packet` (e720904), after scaling down the images (f327f40) was rejected in order to keep the full resolution.

## Consequences
- Images, metadata and camera name are in one place and easy to query.
- Every server has to raise `max_allowed_packet`. When it wasn't raised, every save failed with error 1153 (seen in production from April 2026). When the database is down, images only exist on the device.
- Large BLOBs make the database and its backups grow quickly.

## Open question
In production the database had been failing for months without anyone noticing. Before investing more, it should be decided whether the database archive is still needed, or whether the files on the device (with the disk usage cleanup) are enough.
