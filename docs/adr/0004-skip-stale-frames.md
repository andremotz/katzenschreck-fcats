# 0004. Skip stale frames instead of detecting on them

- Status: Accepted
- Date: 2026-11-01
- Commits: 202b7c5

## Context
In production the stream regularly stalled for minutes (`Stream timeout triggered after 30000 ms`, `No route to host` to the camera) while the reader still held its last frame. The processing loop kept running detection on that same frame, which was up to 470 s old. If a cat had been on it, the sprinkler would have been triggered over and over for a cat that was long gone.

An earlier, never-deployed patch released the `VideoCapture` from the processing thread while the reader thread was using it, which risks a crash in native code.

## Decision
- Frames older than `max_frame_age` (default 10 s) are not passed to detection.
- In `continuous` mode the processing loop then only sets a reconnect event. The reader thread notices it, releases its own capture and reconnects. The capture object is only ever touched by the reader thread.

## Consequences
- A stalled stream produces no detections and no alerts until fresh frames arrive.
- Reconnecting does not help if the camera itself is unreachable. That remains a network or camera issue.
- `max_frame_age` has to be larger than the normal frame age, otherwise healthy frames would be dropped.
