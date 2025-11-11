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
