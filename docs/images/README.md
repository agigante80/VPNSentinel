# Dashboard Screenshots

## Adding Dashboard Screenshot

To add a dashboard screenshot:

1. **Access the dashboard**: Navigate to `http://your-server:8080/dashboard` in your browser
2. **Take screenshot**: Use your browser or screenshot tool to capture the dashboard
3. **Save as**: `dashboard-screenshot.png` in this directory (`docs/images/`)
4. **Recommended size**: 1400x900 pixels for best display in README

## Screenshot Guidelines

- Show the dashboard with at least 2-3 connected clients
- Include examples of different status indicators (🟢 Green, 🟡 Yellow, 🔴 Red)
- Ensure the full interface is visible (header, stats, table, footer)
- Use high resolution (at least 1200px wide)
- Save as PNG format for best quality

## Alternative: Manual Screenshot Instructions

If you need to generate a screenshot manually:

```bash
# Option 1: Using Firefox
firefox --headless --screenshot dashboard-screenshot.png http://localhost:8080/dashboard

# Option 2: Using Chromium/Chrome
chromium --headless --disable-gpu --screenshot=dashboard-screenshot.png --window-size=1400,900 http://localhost:8080/dashboard

# Option 3: Using cutycapt (if installed)
cutycapt --url=http://localhost:8080/dashboard --out=dashboard-screenshot.png --min-width=1400 --min-height=900
```

## Current Status

⚠️ **Screenshot pending**: A dashboard screenshot will be added in the next commit once the dashboard is properly deployed and can be captured with sample data.
