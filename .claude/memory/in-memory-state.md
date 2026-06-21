---
name: in-memory-state
description: VPNSentinel server stores all client status in an in-memory dict; restart loses it
metadata:
  type: project
---

The server keeps all client state in a module-level dict `client_status = {}` in
`vpn_sentinel.common/api_routes.py`. There is no persistence layer. A server restart loses all client
history; clients re-register on their next keepalive (up to 60s gap). This is by design.

**How to apply:** Flag any change that adds state assumed to persist, or any feature depending on
historical data, in code review. See the [[vpnsentinel-reviewer]] agent and the
`.claude/skills/vpnsentinel/SKILL.md` checklist.
