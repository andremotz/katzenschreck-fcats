# 0012. Remove the database archive

- Status: Accepted (supersedes 0009)
- Date: 2026-11-01
- Commits: 827fbca

## Context
ADR 0009 stored every detection and an hourly reference frame in MariaDB. In production, every
save failed from April 2026 (error 1153, `max_allowed_packet`) and later with "connection refused".
Nobody noticed for months, so nothing depends on the archive. The integration also carried a
hard-coded default database password in `config.py`, an extra dependency and a worker thread.

## Decision
The MariaDB integration is removed completely: handler, schema script, worker thread, config keys,
dependency and documentation. Annotated detection images in `results_<camera_name>/`, with the
disk usage cleanup, remain the only archive.

## Consequences
- No database credentials in the code or the config anymore.
- One dependency and one background thread less, which helps a little on the memory-constrained Jetson.
- No hourly reference frames and no central image archive across cameras. If that is needed again,
  it should be built as a separate consumer (e.g. syncing the results folder), not inside the detector.
- Existing data in the `detections_images` table stays where it is.
- `/api/queues` and `/api/timing` lose their database fields.
