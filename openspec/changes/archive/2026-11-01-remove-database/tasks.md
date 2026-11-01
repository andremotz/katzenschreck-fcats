# Tasks

## 1. Code

- [x] 1.1 Delete `cat_detector/database_handler.py` and `database_setup.sql`
- [x] 1.2 Remove the database worker, queue and hourly frame save from `stream_processor.py`
- [x] 1.3 Remove database queue and timing fields from `monitoring_collector.py` and the dashboard
- [x] 1.4 Remove the `db_*` config keys and the default password from `config.py` and `config.txt.example`

## 2. Dependencies and docs

- [x] 2.1 Remove `mysql-connector-python` and `libmariadb-dev` from requirements and Dockerfiles
- [x] 2.2 Update README, ARCHITECTURE, README_DOCKER_JETSON and Ansible templates
- [x] 2.3 Add ADR 0012, mark ADR 0009 as superseded

## 3. Deploy

- [x] 3.1 Remove `db_*` lines from `config.txt` on the Jetson
- [x] 3.2 Rebuild and restart the container, verify detections and MQTT
