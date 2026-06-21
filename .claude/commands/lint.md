---
description: Lint VPNSentinel Python (flake8) and shell scripts (shellcheck/shfmt)
---

Lint the codebase and report findings concisely.

Python (PEP8, max line length 120):
```bash
flake8 --max-line-length=120 vpn-sentinel-server/ vpn-sentinel-client/ src/vpn_sentinel/common/
```

CI also runs the syntax-error subset — useful as a fast first pass:
```bash
flake8 vpn-sentinel-server/ src/vpn_sentinel/common/ --select=E9,F63,F7,F82 --show-source --statistics
```

Shell scripts (if any `.sh` files changed):
```bash
shellcheck tests/run_tests.sh scripts/**/*.sh 2>/dev/null
shfmt -i 2 -ci -d .
```

Report each issue as `file:line` with the rule code and a one-line fix suggestion. If everything is
clean, say so. Do not auto-fix unless asked.
