"""Version management for VPN Sentinel.

Provides version information from environment variables with fallbacks.
"""
import os
import subprocess
from typing import Optional


def get_version() -> str:
    """Get the VPN Sentinel version.

    Returns version from environment variable VERSION, or generates
    a development version from git commit hash.

    Returns:
        Version string (e.g., "1.0.0", "1.0.0-dev-abc123")
    """
    version = os.getenv("VERSION")
    if version:
        return version

    # Try to get commit hash for dev version
    commit = get_commit_hash()
    if commit:
        return f"1.0.0-dev-{commit[:7]}"

    return "1.0.0-dev"


def get_commit_hash() -> Optional[str]:
    """Get the current git commit hash.

    Returns:
        Short commit hash (first 7 characters) or None if unavailable
    """
    commit = os.getenv("COMMIT_HASH")
    if commit:
        return commit[:7] if len(commit) > 7 else commit

    # Try to get from git command
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return None


def get_version_info() -> dict:
    """Get detailed version information.

    Returns:
        Dictionary with version, commit, and build information
    """
    return {
        "version": get_version(),
        "commit": get_commit_hash() or "unknown",
        "environment": os.getenv("ENVIRONMENT", "production")
    }
