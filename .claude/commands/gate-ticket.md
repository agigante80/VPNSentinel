<!-- gate-ticket-version: 1 -->

Run the ticket readiness gate on a GitHub issue in agigante80/VPNSentinel.

## Usage

Accepted argument: `<issue-number>` (required)

Example: `/gate-ticket 44`

## Steps

Use the Agent tool with `subagent_type: ticket-gate`, passing the issue number as the prompt.

The ticket-gate agent handles all steps:
1. Template version check - auto-synthesises missing sections if v < 4 or missing (no BLOCK)
2. Fetches the issue from agigante80/VPNSentinel on GitHub
3. Reads project context (CLAUDE.md, src/vpn_sentinel/common/, architecture docs, labels)
4. Runs 5 core agents + dynamic agents selected by labels and content, sequentially
5. Compiles and posts the scorecard as a GitHub comment on the issue
6. Returns PASS or BLOCKED with specific required changes

All agents must score 10/10 for the ticket to be considered implementation-ready.

## VPNSentinel readiness criteria

A ticket passes only when ALL of the following hold:

- Scope and acceptance criteria are clear and testable
- Tests are planned: unit tests for new functions/classes; integration tests for new endpoints; coverage gate is 80% on vpn_sentinel.common
- The issue author has acknowledged the relevant failure modes that apply:
  - in-memory client_status is lost on server restart (flag any feature that depends on historical data)
  - external HTTP calls (geolocation, DNS, Telegram) require retry/fallback; no single provider failure should break the flow
  - shared dicts (client_status and derivatives) require thread-safe access in Flask handlers
  - Telegram notifications that can fire in bursts must apply rate-limiting
- Code changes will be flake8 clean at max-line-length 120
- Work targets the develop branch; main is release-only

## Branch flow

Implementation goes to `develop`. The ticket is not ready if it proposes direct commits to `main`.
