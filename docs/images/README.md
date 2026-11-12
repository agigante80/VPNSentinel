# Dashboard Screenshots

This directory holds the dashboard screenshot used by the root README, plus the project icon.

## Current Screenshot

- **File**: `dashboard-screenshot.png` (1400x1000 PNG)
- Shows all three statuses: two green clients, one yellow (DNS leak) and one red (VPN bypass)
- All data is fixed demo data: every IP is from the documentation ranges (RFC 5737), so the
  image never contains a real public IP

## Regenerating the Screenshot

```bash
VERSION=1.2.3 scripts/generate_dashboard_screenshot.sh   # VERSION is the footer badge
```

The script starts `scripts/dashboard_demo.py`, which serves the dashboard on `127.0.0.1:18090`
(`DEMO_PORT` to change it) with the demo clients loaded and the server's geolocation lookup replaced
by a fixed demo identity. It then captures the page with headless Chromium or Chrome and stops the
demo server. No running VPN Sentinel stack is needed, and nothing is sent over the network.

Review the image before committing it:

```bash
git add docs/images/dashboard-screenshot.png
```

## Project Icon

| File | Purpose |
|---|---|
| `icon.svg` | Master: the Owl sentinel (a night-watch owl with green eyes; square 512 grid, transparent background, light outline so it reads on light and dark) |
| `icon-512.png`, `icon-256.png` | PNG renders of the master |
| `src/vpn_sentinel/common/static/favicon.svg`, `favicon.png` | Served copies of `icon.svg` and `icon-256.png`, shipped as package data and served by the dashboard at `/favicon.svg` and `/favicon.ico` |

The `net.unraid.docker.icon` image label and the Unraid template `<Icon>` point at the raw
GitHub URL of `icon-256.png` on `main`. After editing the master, regenerate and recopy:

```bash
rsvg-convert -w 512 -h 512 docs/images/icon.svg -o docs/images/icon-512.png
rsvg-convert -w 256 -h 256 docs/images/icon.svg -o docs/images/icon-256.png
cp docs/images/icon-256.png src/vpn_sentinel/common/static/favicon.png
cp docs/images/icon.svg src/vpn_sentinel/common/static/favicon.svg
```

A unit test fails if the served copies drift from the masters.
