# 0006. Docker on the Ultralytics JetPack 6 image for Jetson

- Status: Accepted
- Date: 2026-04-07
- Commits: 149e404, 40e4794, 4e8466b, 254bdf5, 3a132a4, ab63096, 4f9181f, cf36a38

## Context
Native installation on Jetson meant matching PyTorch wheels to JetPack, CUDA and Python by hand (`install_jetson.sh`, `install_universal.sh`). The first Docker attempt was based on the JetPack 5 image. On the Jetson Orin with JetPack 6 that led to a GLIBC mismatch, and the detector silently ran on the CPU (about 23 s per frame).

## Decision
- On Jetson the detector runs in Docker on `ultralytics/ultralytics:latest-jetson-jetpack6`. The base image provides PyTorch, CUDA, OpenCV and Ultralytics. Only the few extra Python packages are installed on top.
- The container runs with `--gpus all`. After start, the script checks `torch.cuda.is_available()` inside the container.
- Native operation via `start_script.sh` and a systemd user service (ab63096) remains for Raspberry Pi and other hosts.

## Consequences
- Detection runs on the GPU (about 0.3–0.5 s per frame instead of about 23 s).
- The image is about 24 GB and the base image is tagged `latest`, so two builds at different times can get different PyTorch or Ultralytics versions.
- Two ways to run the detector (Docker, native) have to be kept working.
