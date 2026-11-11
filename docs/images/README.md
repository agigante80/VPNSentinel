# Dashboard Screenshots

This directory contains screenshots of the VPN Sentinel dashboard for documentation purposes.

## Current Screenshot

- **File**: `dashboard-screenshot.png`
- **Resolution**: 1400x900 pixels
- **Format**: PNG
- **Size**: ~341KB
- **Last Updated**: 2025-11-11

The screenshot shows the dashboard with multiple clients displaying all status types (🟢 Green, 🟡 Yellow, 🔴 Red).

## Regenerating Screenshot Automatically

The dashboard screenshot can be regenerated automatically using the following command:

```bash
# Start the VPN Sentinel server and client first
docker compose up -d

# Wait for services to be ready
sleep 5

# Generate screenshot using chromium headless mode
chromium-browser --headless --disable-gpu \
  --screenshot=docs/images/dashboard-screenshot.png \
  --window-size=1400,900 \
  --virtual-time-budget=3000 \
  http://localhost:18080/dashboard
```

### Prerequisites

- VPN Sentinel server running on port 18080 (or adjust URL)
- Chromium browser installed (`sudo apt install chromium-browser`)
- At least 2-3 clients connected with varied statuses for best visual

### Alternative Browsers

```bash
# Using Firefox
firefox --headless --screenshot docs/images/dashboard-screenshot.png \
  http://localhost:18080/dashboard

# Using Chrome
google-chrome --headless --disable-gpu \
  --screenshot=docs/images/dashboard-screenshot.png \
  --window-size=1400,900 \
  http://localhost:18080/dashboard
```

## Screenshot Guidelines

When regenerating screenshots:
- Ensure at least 2-3 clients are connected
- Include examples of all status indicators (🟢 Green, 🟡 Yellow, 🔴 Red)
- Full interface should be visible (header, server info, stats, table, footer)
- Resolution: 1400x900 pixels minimum
- Format: PNG for best quality
- Show realistic data (varied locations, providers, statuses)

## Updating Documentation

After regenerating the screenshot:

```bash
git add docs/images/dashboard-screenshot.png
git commit -m "docs: Update dashboard screenshot"
git push origin develop
```

## Project Icon

| File | Purpose |
|---|---|
| `icon.svg` | Master (shield with a red, yellow and green traffic light, square, readable on light and dark) |
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
