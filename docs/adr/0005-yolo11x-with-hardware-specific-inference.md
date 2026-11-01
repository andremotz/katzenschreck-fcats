# 0005. YOLO11x everywhere, tune inference per hardware

- Status: Accepted
- Date: 2025-10-23
- Commits: 8568f6b, 3109ea0, 18039f7, 36f2da4, 4b034e6, bf3e5ba, 7cce5dd, 15660fe, 19f1f3d, 9147b0f

## Context
The model changed several times: yolo11n, yolo11s, yolo12x, yolo12l, and back to YOLO11. Selecting the model by available RAM (4b034e6) made behaviour differ between devices. Small models missed cats in the dark or at the edge of the frame.

## Decision
- Default model is `yolo11x.pt` on all hardware (7cce5dd). `yolo_model` can point to other or fine-tuned weights, e.g. `runs/.../best.pt` (19f1f3d).
- Hardware only changes inference settings, not the model: on Jetson GPU, FP16, input size 640 (15660fe); elsewhere input size 1280.
- Jetson is detected via the device tree, `/etc/nv_tegra_release` or the CUDA device name, so this also works inside containers (9147b0f). `hardware_type` can force it.

## Consequences
- Same model and accuracy everywhere. Only speed differs.
- On a Raspberry Pi, YOLO11x is slow. That is accepted in favour of accuracy.
- YOLO11x needs about 1.7 GB on the Jetson Orin Nano (8 GB shared with the GPU). Together with other containers on the same device, CUDA memory allocation can fail at startup (observed on 2026-11-01, resolved by restarting).
