---
name: branch-model
description: develop is the active development branch; main is the release branch
metadata:
  type: project
---

`develop` is the active development branch. `main` is the release branch. Do not commit directly to
`main`; feature work and AI-driven changes land on `develop` and are merged to `main` for releases.
CI (`.github/workflows/ci-cd.yml`) triggers on `develop` and `main`; arm64 builds are skipped on
`develop` to speed up CI.
