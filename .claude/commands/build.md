---
description: Build the VPNSentinel server and client Docker images and verify they start
---

Build both Docker images (build context is the repo root) and verify they run.

```bash
docker build -t vpn-sentinel-server:latest -f vpn-sentinel-server/Dockerfile .
docker build -t vpn-sentinel-client:latest -f vpn-sentinel-client/Dockerfile .
```

Then smoke-check that each image's entry point responds:
```bash
docker run --rm vpn-sentinel-server:latest --help
docker run --rm vpn-sentinel-client:latest --help
```

Report build success/failure for each image and any error output. Per project convention, both images
should build cleanly before pushing image changes.
