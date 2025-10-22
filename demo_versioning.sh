#!/bin/bash
# VPN Sentinel Versioning Demonstration
# This script shows how automatic versioning works in different scenarios

echo "🔖 VPN Sentinel Automatic Versioning Demo"
echo "=========================================="
echo

# Script should be run from project root directory

echo "📍 Current Git Status:"
echo "   Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "   Latest tag: $(git describe --tags --abbrev=0 2>/dev/null || echo 'none')"
echo "   Commits ahead: $(git rev-list --count $(git describe --tags --abbrev=0)..HEAD 2>/dev/null || echo 'N/A')"
echo

echo "🎯 Versioning Logic:"
echo "   • main branch + clean tag → '1.0.0' (production release)"
echo "   • main branch + commits ahead → '1.0.0+{commits}' (pre-release)"
echo "   • develop branch → '1.0.0-dev-{commit}' (development)"
echo "   • other branches → '1.0.0-{branch}-{commit}' (feature branches)"
echo

echo "📊 Current Version: $(./get_version.sh)"
echo

echo "🔮 Example Scenarios:"
echo "   Clean tag on main: 1.0.0"
echo "   Main + 5 commits: 1.0.0+5"
echo "   Develop branch: 1.0.0-dev-{commit}"
echo "   Feature branch: 1.0.0-feature-x-{commit}"
echo

echo "🚀 To create a new release:"
echo "   1. Merge changes to main branch"
echo "   2. Create and push a new tag: git tag v1.0.1 && git push origin v1.0.1"
echo "   3. CI/CD will automatically build with version '1.0.1'"
echo

echo "✨ Automatic versioning is now active!"