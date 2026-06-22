---
name: ai-tooling-claude
description: Project migrated from GitHub Copilot to Claude Code as the maintainer AI on 2026-06-21
metadata:
  type: project
---

On 2026-06-21 the project's AI tooling was migrated from GitHub Copilot to Claude Code. The owner
asked Claude to take over as the maintainer AI.

Removed: `.github/copilot-instructions.md`, the `.agents/` directory (Codex/Copilot skill).
Added: root `CLAUDE.md`, and `.claude/` with `settings.json`, `skills/vpnsentinel/`,
`agents/vpnsentinel-reviewer.md`, `commands/` (test, lint, build), and this `memory/`.

**How to apply:** `CLAUDE.md` is the single source of truth for working conventions; other AI tools
should read it too. The old Copilot skill content was ported (and de-`gate`-ified) into
`.claude/skills/vpnsentinel/SKILL.md`. See [[branch-model]] and [[in-memory-state]].
