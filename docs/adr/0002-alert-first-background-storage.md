# 0002. Alert first, store in the background

- Status: Accepted
- Date: 2025-12-11
- Commits: 1838c6f, d24c0b7

## Context
After a few days of running, alerts arrived up to 37 s after the event. Saving images to disk and to MariaDB ran in the same loop as detection, and every slow write pushed all following frames back.

## Decision
- The timestamp is taken before detection.
- The MQTT message is published first, directly in the processing loop.
- Image files and database rows are handed to two background worker threads through bounded queues (10 entries). When a queue is full, the save is dropped and logged.
- A monitoring server exposes a per-step timing breakdown so new delays can be located (d24c0b7).

## Consequences
- A slow or unreachable database no longer delays alerts. This happened in practice: the database was unreachable for months and detection kept working.
- Images can be lost under load or when the database is down. That is accepted: the alert matters, the archive does not.
- Since ADR 0012 there is no database anymore; only the file worker remains.
