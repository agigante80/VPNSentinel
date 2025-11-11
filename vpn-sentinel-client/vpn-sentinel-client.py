#!/usr/bin/env python3
"""VPN Sentinel Client - Python implementation using shared libraries.

This script replaces the Bash vpn-sentinel-client.sh with a clean Python
implementation that leverages the vpn_sentinel_common libraries.
"""
import os
import sys
import time
import signal
import subprocess
import json
from pathlib import Path

# Add the parent directory to sys.path so we can import vpn_sentinel_common
sys.path.insert(0, str(Path(__file__).parent.parent))

from vpn_sentinel_common.config import load_config
from vpn_sentinel_common.geolocation import get_geolocation
from vpn_sentinel_common.network import parse_dns_trace
from vpn_sentinel_common.payload import build_payload_from_env, post_payload
from vpn_sentinel_common.log_utils import log_info, log_warn, log_error


def get_dns_info() -> dict:
    """Get DNS information by running a traceroute-like command.

    Returns a dict with 'loc' and 'colo' keys.
    """
    try:
        # Try to get DNS location info using cloudflare's DNS
        # This mimics the behavior of the shell script
        result = subprocess.run(
            ["dig", "TXT", "whoami.cloudflare", "@1.1.1.1", "+short"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            # Parse the DNS response
            trace_text = result.stdout.strip()
            log_info('dns-test', f"Using 'dig' output: {trace_text}")
            parsed = parse_dns_trace(trace_text)
            log_info('dns-test', f"Parsed DNS info: {parsed}")
            return parsed

    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    # If dig is not available or failed, fall back to HTTP trace endpoint
    # Cloudflare provides a trace endpoint that returns similar key=value pairs
    # Example response: "fl=... ip=... ts=... loc=PL colo=WAW"
    try:
        import requests

        # Prefer the 1.1.1.1 endpoint if reachable, otherwise use cloudflare.com
        urls = [
            "https://1.1.1.1/cdn-cgi/trace",
            "https://www.cloudflare.com/cdn-cgi/trace"
        ]
        for url in urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200 and resp.text:
                    trace_text = resp.text.strip()
                    log_info('dns-test', f"Using HTTP fallback ({url}): {trace_text}")
                    parsed = parse_dns_trace(trace_text)
                    log_info('dns-test', f"Parsed DNS info (HTTP): {parsed}")
                    return parsed
            except Exception as e:
                log_warn('dns-test', f"HTTP fallback failed for {url}: {e}")
                continue
    except Exception as e:
        # requests not available or other error - fall through to unknown
        log_warn('dns-test', f"Requests not available for HTTP fallback: {e}")
        pass

    # Fallback: return empty dict
    return {"loc": "Unknown", "colo": "Unknown"}


def send_keepalive(config: dict) -> bool:
    """Send a keepalive payload to the server.

    Args:
        config: Configuration dictionary from load_config()

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get geolocation data
        geolocation_service = os.environ.get("VPN_SENTINEL_GEOLOCATION_SERVICE", "auto")
        geo_data = get_geolocation(service=geolocation_service, timeout=config["timeout"])

        if not geo_data:
            log_error("vpn-info", "❌ All geolocation providers failed")
            return False

        # Store geolocation source for logging
        geolocation_source = geo_data.get("source", "unknown")

        # Set environment variables for payload building
        os.environ["CLIENT_ID"] = config["client_id"]
        os.environ["PUBLIC_IP"] = geo_data.get("public_ip", "unknown")
        os.environ["COUNTRY"] = geo_data.get("country", "Unknown")
        os.environ["CITY"] = geo_data.get("city", "Unknown")
        os.environ["REGION"] = geo_data.get("region", "Unknown")
        os.environ["ORG"] = geo_data.get("org", "Unknown")
        os.environ["VPN_TIMEZONE"] = geo_data.get("timezone", "Unknown")

        # Get DNS information
        dns_data = get_dns_info()
        os.environ["DNS_LOC"] = dns_data.get("loc", "Unknown")
        os.environ["DNS_COLO"] = dns_data.get("colo", "Unknown")

        # Build payload
        payload = build_payload_from_env()
        payload_json = json.dumps(payload, ensure_ascii=False)

        # Set environment for posting
        os.environ["SERVER_URL"] = config["server_url"]
        os.environ["TIMEOUT"] = str(config["timeout"])
        os.environ["VPN_SENTINEL_API_KEY"] = os.environ.get("VPN_SENTINEL_API_KEY", "")
        os.environ["VPN_SENTINEL_ALLOW_INSECURE"] = str(config.get("allow_insecure", False)).lower()

        # Send payload
        result = post_payload(payload_json)

        if result == 0:
            log_info("api", "✅ Keepalive sent successfully")
            log_info("vpn-info", f"📍 Location: {os.environ['CITY']}, {os.environ['REGION']}, {os.environ['COUNTRY']}")
            log_info("vpn-info", f"🌐 VPN IP: {os.environ['PUBLIC_IP']} (via {geolocation_source})")
            log_info("vpn-info", f"🏢 Provider: {os.environ['ORG']}")
            log_info("vpn-info", f"🕒 Timezone: {os.environ['VPN_TIMEZONE']}")
            log_info("dns-test", f"🔒 DNS: {os.environ['DNS_LOC']} ({os.environ['DNS_COLO']})")
            return True
        else:
            log_error("api", f"❌ Failed to send keepalive to {config['server_url']}")
            log_error("vpn-info", f"📍 Location: {os.environ['CITY']}, {os.environ['REGION']}, {os.environ['COUNTRY']}")
            log_error("vpn-info", f"🌐 VPN IP: {os.environ['PUBLIC_IP']} (via {geolocation_source})")
            log_error("vpn-info", f"🏢 Provider: {os.environ['ORG']}")
            log_error("vpn-info", f"🕒 Timezone: {os.environ['VPN_TIMEZONE']}")
            log_error("dns-test", f"🔒 DNS: {os.environ['DNS_LOC']} ({os.environ['DNS_COLO']})")
            return False

    except Exception as e:
        log_error("client", f"❌ Error sending keepalive: {e}")
        return False


def start_health_monitor(config: dict) -> subprocess.Popen:
    """Start the health monitor subprocess.

    Args:
        config: Configuration dictionary

    Returns:
        Popen object for the health monitor process
    """
    try:
        # Find the health monitor script
        # Check for the wrapper in vpn_sentinel_common/health_scripts first (works in both container and dev)
        repo_root = Path(__file__).parent.parent
        py_monitor = repo_root / "vpn_sentinel_common" / "health_scripts" / "health_monitor_wrapper.py"
        sh_monitor = repo_root / "vpn_sentinel_common" / "health_scripts" / "health-monitor.sh"

        # Fallback to /app locations if running in container with different structure
        container_py_monitor = Path("/app/vpn_sentinel_common/health_scripts/health_monitor_wrapper.py")
        container_sh_monitor = Path("/app/vpn_sentinel_common/health_scripts/health-monitor.sh")

        monitor_path = None
        if py_monitor.exists():
            monitor_path = py_monitor
        elif sh_monitor.exists():
            monitor_path = sh_monitor
        elif container_py_monitor.exists():
            monitor_path = container_py_monitor
        elif container_sh_monitor.exists():
            monitor_path = container_sh_monitor

        if not monitor_path:
            log_warn("client", "⚠️ Health monitor script not found")
            return None

        # Start the monitor
        # Log the monitor name without the full container path for clarity
        monitor_name = monitor_path.name if monitor_path else "health monitor"
        log_info("client", f"Starting health monitor: {monitor_name}")
        if monitor_path.suffix == '.py':
            cmd = [sys.executable, str(monitor_path)]
        else:
            cmd = [str(monitor_path)]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait a moment and check if it's still running
        time.sleep(1)
        if process.poll() is None:
            log_info("client", f"✅ Health monitor started (PID: {process.pid})")
            return process
        else:
            log_warn("client", "⚠️ Health monitor failed to start")
            return None

    except Exception as e:
        log_warn("client", f"⚠️ Error starting health monitor: {e}")
        return None


def main():
    """Main entry point for the VPN Sentinel client."""
    # Load configuration
    config = load_config(os.environ)

    # Log version information
    version = config.get("version", "1.0.0-dev")
    log_info("client", f"📦 Version: {version}")

    # Log startup information
    log_info("client", "🚀 Starting VPN Sentinel Client")
    log_info("config", f"📡 Server: {config['server_url']}")
    log_info("config", f"🏷️ Client ID: {config['client_id']}")
    log_info("config", f"⏱️ Interval: {config['interval']}s")

    # Log debug mode
    if config.get("debug", False):
        log_info("config", "🐛 Debug mode enabled")
    else:
        log_info("config", "ℹ️ Debug mode disabled")

    # Log geolocation service
    geolocation_service = os.environ.get("VPN_SENTINEL_GEOLOCATION_SERVICE", "auto")
    if geolocation_service == "auto":
        log_info("config", "🌐 Geolocation service: auto")
        log_info("config", "will try ipinfo.io first, fallback to ip-api.com then ipwhois.app")
    else:
        log_info("config", f"🌐 Geolocation service: forced to {geolocation_service}")

    # Start health monitor if enabled
    health_monitor_process = None
    if os.environ.get("VPN_SENTINEL_HEALTH_MONITOR", "true").lower() != "false":
        health_monitor_process = start_health_monitor(config)

    # Set up signal handlers for graceful shutdown
    stop_requested = False

    def signal_handler(signum, frame):
        nonlocal stop_requested
        log_info("client", "🛑 Received shutdown signal, stopping...")
        stop_requested = True
        if health_monitor_process:
            try:
                health_monitor_process.terminate()
                health_monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                health_monitor_process.kill()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Main loop
    try:
        while not stop_requested:
            if send_keepalive(config):
                pass  # Success already logged
            else:
                pass  # Error already logged

            log_info("client", f"⏳ Waiting {config['interval']} seconds until next keepalive...")
            log_info("client", "(Press Ctrl+C to stop monitoring)")

            # Sleep in small chunks to allow for quick shutdown
            for _ in range(config['interval']):
                if stop_requested:
                    break
                time.sleep(1)

    except KeyboardInterrupt:
        log_info("client", "Interrupted by user")
    finally:
        if health_monitor_process:
            try:
                health_monitor_process.terminate()
                health_monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                health_monitor_process.kill()
        log_info("client", "VPN Sentinel Client stopped")


if __name__ == "__main__":
    main()
