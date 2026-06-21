---
name: execution-mode-preference
description: User standing preference — always execute implementation plans with subagent-driven development, never ask
metadata:
  type: feedback
---

When executing a written implementation plan, ALWAYS use subagent-driven development (fresh
implementer subagent per task, per-task spec + quality review, final whole-branch review). Never ask
the user which execution mode to use — they have hardcoded this preference ("always use subagent in
the future, don't bother me", 2026-06-21).

**Why:** The user values the quality gates and fresh-context-per-task isolation, and does not want to
re-decide it each time.

**How to apply:** After `writing-plans` produces a plan, skip the "which execution approach?" prompt
and go straight to `subagent-driven-development`. Also recorded in [[ai-tooling-claude]] / `CLAUDE.md`
working agreements.
