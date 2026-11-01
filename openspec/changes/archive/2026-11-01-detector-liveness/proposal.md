# Proposal

## Why

Home Assistant warns when the detector's MQTT heartbeat stops, but the heartbeat is sent by its own thread every 30 seconds regardless of whether detection is running. If the processing loop hangs or detection keeps failing (e.g. the `CUBLAS_STATUS_ALLOC_FAILED` / `NvMap ... error 12` GPU memory failure seen on the shared Jetson), pings continue, the Docker health check stays `healthy` (it only checks `is_streaming`) and nobody notices that cats no longer trigger the sprinklers.

## What Changes

- Heartbeat pings are only sent while a frame has completed detection within `liveness_timeout` seconds (new config key, default 60).
- `/api/status` reports `processing_alive`, `last_processed_time` and `seconds_since_processed`.
- The container health check requires `is_streaming` **and** `processing_alive`.
- A watchdog exits the process if the main loop makes no progress for `watchdog_timeout` seconds (new config key, default 120), so the restart policy restarts the container.

## Capabilities

### New Capabilities

### Modified Capabilities
- `mqtt-alerting`: the heartbeat is tied to detection actually running.
- `monitoring`: status endpoint and health check report processing liveness; watchdog restarts a hung process.

## Impact

- Code: `mqtt_handler.py`, `stream_processor.py`, `monitoring_collector.py`, `config.py`.
- `Dockerfile.jetson` health check, `config.txt.example`.
- Home Assistant: the existing "Katzenerkennung offline melden" automation now also fires when detection hangs or the camera stream is down for more than about 5 minutes, not only when the process is gone.
- See ADR 0013.
