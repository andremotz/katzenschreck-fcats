# 0013. Tie the heartbeat and health check to detection progress

- Status: Accepted
- Date: 2026-11-01
- Commits: ef825f9

## Context
Home Assistant raises an alarm when the MQTT heartbeat (`{mqtt_topic}/ping`) stops for 5 minutes. The heartbeat came from its own thread and only proved that the process and the MQTT connection were alive. The Docker health check only looked at `is_streaming`, which is set once at startup.

On the shared Jetson the GPU sometimes runs out of memory (`CUBLAS_STATUS_ALLOC_FAILED`, `NvMapMemAllocInternalTagged ... error 12`). In that state, or with a hung inference or a dead camera stream, the detector would keep sending pings and stay `healthy`, while no cat could trigger the sprinklers.

## Decision
- The heartbeat is only sent if a frame completed object detection within `liveness_timeout` (default 60 s). It now means "detection is running".
- `/api/status` reports `processing_alive`; the health check requires it together with `is_streaming`.
- A watchdog thread exits the process (`os._exit(1)`) if the processing loop has not advanced for `watchdog_timeout` (default 120 s). The `unless-stopped` restart policy then restarts the container.
- A loop that runs but gets no frames (camera unreachable) is not restarted; it is reported by the missing heartbeat.

## Consequences
- Home Assistant's existing offline alert now also covers hung or failing detection and long camera outages, not only a dead process.
- After a restart, pings only start once the first frame is processed (model load plus first inference).
- Docker alone does not restart `unhealthy` containers; automatic recovery depends on the watchdog or the process crashing.
- A camera outage longer than 5 minutes now produces an "offline" notification in Home Assistant, which is intended.
