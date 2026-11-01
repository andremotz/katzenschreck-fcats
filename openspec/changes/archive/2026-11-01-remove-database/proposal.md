# Proposal

## Why

The MariaDB image archive was failing in production for months (error 1153, later "connection refused") without anyone noticing, so nobody relies on it. It adds a dependency, a credential (with a hard-coded default password in the code) and a background thread for no benefit. See ADR 0012.

## What Changes

- **BREAKING**: Detection images and hourly reference frames are no longer stored in MariaDB. The `db_host`, `db_user`, `db_password` and `db_database` config keys are ignored.
- Remove the hard-coded default database password.
- Remove the database worker thread and queue, the database timing and queue fields from monitoring, and the `mysql-connector-python` dependency.
- Detection images on disk (with disk usage cleanup) remain the only archive.

## Capabilities

### New Capabilities

### Modified Capabilities
- `detection-storage`: database storage and hourly reference frames are removed; background storage only covers files.
- `mqtt-alerting`: the alert-priority requirement no longer mentions the database.

## Impact

- Code: `cat_detector/database_handler.py` and `database_setup.sql` deleted; `stream_processor.py`, `monitoring_collector.py`, `config.py`, monitoring dashboard.
- API: `/api/queues` no longer contains `db_queue`; `/api/timing` no longer contains `db_queue_wait` and `save_database_check`.
- Dependencies: `mysql-connector-python` and `libmariadb-dev` removed from requirements and Dockerfiles.
- Docs and Ansible templates no longer mention the database.
- Existing data in the `detections_images` table is left untouched.
