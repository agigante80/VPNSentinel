---
name: lean-repo-preference
description: User wants a lean repository (especially root, bare minimum); prefers deleting over archiving
metadata:
  type: feedback
---

The user wants a lean repository, especially the root: keep ONLY the bare minimum there (tooling
pinned files and GitHub conventions). Documents may be moved freely to the most sensible location.

**Strong preference: delete over archiving.** Do not keep stale or superseded files "just in case",
and do not create archive folders. Git history and GitHub (PRs, releases) are the archive. When in
doubt between deleting and keeping a no-longer-referenced file, delete it.

**How to apply:**
- Root stays minimal: `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`, `.shellcheckrc`,
  `README.md`, `LICENSE`, `CLAUDE.md`, `compose.yaml`, `VERSION`, `.env.example`,
  `.vulture_allowlist.py`. New top-level files need a strong tooling/convention reason.
- Process artifacts (design specs/plans, scratch notes) are deleted once merged, not archived in the
  tree. (Done 2026-06-22: removed `docs/superpowers/`, the leftover `.agents/` skill, `bin/README.md`;
  moved `dockerhub/` under `.github/`.)
- See [[block-dashes]] for the related no-em-dash writing rule the user also enabled.
