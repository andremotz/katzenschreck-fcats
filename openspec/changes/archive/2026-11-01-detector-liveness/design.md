# Design

See ADR 0013 (`docs/adr/0013-heartbeat-tied-to-detection.md`).

## Liveness signal

- `StreamProcessor` records `_last_processed_time` right after `detect_objects()` returns, and `_last_loop_time` at the start of every loop iteration.
- `is_processing_alive()` is true if `_last_processed_time` is set and not older than `liveness_timeout`.
- `MQTTHandler` receives `is_processing_alive` as a callback and skips the ping when it returns false. It logs once when pings are suspended and once when they resume.
- `MonitoringCollector` gets the same timestamp and exposes `processing_alive`, `last_processed_time` and `seconds_since_processed` in `/api/status`. The Docker health check requires `is_streaming and processing_alive`.

## Watchdog

- A daemon thread checks every 10 s whether `_last_loop_time` is older than `watchdog_timeout` and then calls `os._exit(1)`. `os._exit` is used because a hung native call (CUDA, FFmpeg) in the main thread cannot be interrupted, and `sys.exit` from a thread only ends that thread.
- The watchdog only covers a blocked loop. A loop that runs but never gets a frame (camera down) is not restarted, since a restart does not fix the camera; it is reported via missing pings and the health status instead.
- Docker does not restart containers that are merely `unhealthy`. Restarts happen only through the watchdog exit or an unhandled exception, both with `--restart unless-stopped`.

## Timeouts

- `liveness_timeout` 60 s: frames are processed several times per second; 60 s tolerates short stream reconnects (`max_frame_age` 10 s plus reconnect backoff) without flapping. Home Assistant alerts after 5 minutes without a ping.
- `watchdog_timeout` 120 s: well above model warm-up and the slowest observed frame, so it only fires on real hangs. The watchdog starts after model loading, when `run()` begins.
