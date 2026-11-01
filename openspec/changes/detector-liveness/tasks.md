# Tasks

## 1. Code

- [x] 1.1 Record last processed frame and last loop time in `stream_processor.py`
- [x] 1.2 Gate the MQTT heartbeat on processing liveness in `mqtt_handler.py`
- [x] 1.3 Expose `processing_alive`, `last_processed_time`, `seconds_since_processed` in `/api/status`
- [x] 1.4 Add the watchdog thread that exits the process on a stalled loop
- [x] 1.5 Add `liveness_timeout` and `watchdog_timeout` to `config.py` and `config.txt.example`
- [x] 1.6 Require `processing_alive` in the `Dockerfile.jetson` health check

## 2. Docs

- [x] 2.1 Add ADR 0013 and list it in `docs/adr/README.md`

## 3. Deploy

- [ ] 3.1 Rebuild and restart the container on the Jetson
- [ ] 3.2 Verify `/api/status`, health status and that pings still arrive in Home Assistant
