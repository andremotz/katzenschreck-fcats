# 0003. Threaded latest-frame RTSP reader

- Status: Accepted
- Date: 2025-12-21
- Commits: 1a08202, 674d30f, 15660fe, 6155df2, 6f23eb8

## Context
OpenCV buffers RTSP frames internally. When detection is slower than the camera frame rate, the buffer grows and the analysis falls further and further behind real time ("frame drift"). Earlier attempts with small buffers and frame skipping (674d30f, 15660fe) did not fully solve this.

## Decision
A dedicated reader thread calls `grab()`/`retrieve()` continuously and keeps only the latest frame. The processing loop always takes that frame. FFmpeg runs with low-delay options and a minimal buffer, over UDP by default.

As an alternative, `rtsp_connection_mode=reconnect_per_frame` opens the stream, reads one frame and closes it again for every frame (6f23eb8). This guarantees a fresh frame at the cost of 1–3 s per frame.

## Consequences
- Processing works on the current image regardless of how slow detection is.
- The reader decodes every frame, including the ones it discards, which costs CPU.
- UDP keeps latency low but loses packets on a weak link, which shows up as H.264 decode errors. `rtsp_transport=tcp` is available when the network is the bottleneck.
- If the stream stalls without disconnecting, the "latest" frame quietly gets older. See ADR 0004.
