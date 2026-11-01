# 0010. Single key=value config file, mounted at runtime

- Status: Accepted
- Date: 2024-12-30
- Commits: 65c58e3, 687a7af, 95823be, 43db15e, d0cfd5c, b32ed31, 7849465

## Context
Settings differ per camera and contain credentials (MQTT, database). Early versions hard-coded values or read them in the shell script.

## Decision
All settings live in one `config.txt` with `key=value` lines, read by `cat_detector/config.py` with defaults for optional keys. `config.txt` is git-ignored, `config.txt.example` documents the keys. In Docker the file is mounted read-only to `/katzenschreck/config.txt` and is not part of the image (7849465).

## Consequences
- Simple to edit on the device, one file per camera.
- No types, no validation beyond required keys, and lines starting with `#` are only ignored if they don't contain `=`.
- `config.py` used to contain a default database password. It was removed together with the database (ADR 0012).
