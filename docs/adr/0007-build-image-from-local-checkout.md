# 0007. Build the image from the local checkout

- Status: Accepted (supersedes the Git-clone build introduced in 2496d93)
- Date: 2026-11-01
- Commits: 2496d93, 7849465

## Context
Initially the Dockerfile copied the code from the build context. In 2496d93 it was changed to `git clone --branch $GIT_BRANCH` during the build, so that only pushed code would end up in the image. This had two problems:

- Docker caches a `RUN git clone` step by its command text. After a push to the same branch, a rebuild reused the cached layer and silently kept the old code.
- The image did not record which commit it contained. Finding out what was running required comparing files by hand.

## Decision
- The Dockerfile copies the code from the build context (`COPY`).
- `start_jetson_docker.sh` refuses to build when tracked files have uncommitted changes (`ALLOW_DIRTY=1` overrides).
- The image is tagged `katzenschreck-jetson:<commit>` and `:latest`, and carries the commit as an OCI label and as an environment variable.
- Deploying another version means `git checkout` on the device first.

Alternative considered: building in GitLab CI and pulling from the existing registry, as the other projects on the Jetson do. Rejected for now because it needs an ARM runner and the image is about 24 GB, for a single device.

## Consequences
- The code in the image is always the checked-out commit, and `docker inspect` shows which one.
- Rollback: start a previous `katzenschreck-jetson:<commit>` image.
- Old images use disk space and have to be pruned by hand.
- The build needs the repository on the device.
