# 0008. One container per camera

- Status: Accepted
- Date: 2026-02-05
- Commits: 618befc, e87993f

## Context
More than one camera should be served by the same Jetson.

## Decision
Each camera gets its own process and container with its own config file. The container name (`katzenschreck-<camera_name>`), results directory (`results_<camera_name>/`) and monitoring port are derived from that config. Containers use host networking by default so RTSP works without extra configuration; bridge mode is optional to make ports visible in `docker ps` (e87993f).

## Consequences
- Cameras are isolated: one crashing stream does not affect the others.
- Every container loads its own copy of the model. On an 8 GB Jetson, memory limits the number of cameras.
- Ports must be assigned by hand per config.
