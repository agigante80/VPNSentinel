"""Serve the web dashboard with fixed demo data, for README screenshots (issue #147).

No network lookups happen: the server's public IP and geolocation are replaced with a fixed
documentation-range address (RFC 5737), and the four demo clients use documentation addresses too,
so a screenshot can never show the real public IP of the machine that took it.

Usage: python scripts/dashboard_demo.py [port]   (default 18090, binds 127.0.0.1 only)
"""

import sys
from datetime import datetime, timedelta, timezone

from werkzeug.serving import make_server

from vpn_sentinel.common import dashboard_routes
from vpn_sentinel.common.api_routes import client_status, client_status_lock

DEMO_SERVER_IP = "203.0.113.10"

DEMO_SERVER_INFO = {
    "public_ip": DEMO_SERVER_IP,
    "location": "Chicago, Illinois, US",
    "provider": "Example Home ISP",
    "dns_status": "Operational",
}

# (client_id, version, public_ip, city, region, country, provider, dns_loc, dns_colo, minutes_ago)
DEMO_CLIENTS = [
    # Green: VPN exit in the US, DNS resolves in the US
    ("vpn-media-usa", "1.1.17", "198.51.100.23", "New York City", "New York", "US", "Example VPN NYC", "US", "EWR", 0),
    # Green: VPN exit in Bulgaria, DNS resolves in Bulgaria
    ("vpn-media", "1.1.17", "198.51.100.87", "Sofia", "Sofia-city", "BG", "Example VPN Sofia", "BG", "SOF", 1),
    # Yellow: VPN exit in the Netherlands, but DNS resolves in the US (DNS leak)
    (
        "office-vpn-primary",
        "1.1.16",
        "192.0.2.45",
        "Amsterdam",
        "North Holland",
        "NL",
        "Example VPN AMS",
        "US",
        "IAD",
        3,
    ),
    # Red: public IP equals the server's (VPN bypass, traffic leaves through the home ISP)
    ("home-network-leaked", "1.1.15", DEMO_SERVER_IP, "Chicago", "Illinois", "US", "Example Home ISP", "US", "ORD", 7),
]


def load_demo_clients(now=None):
    """Replace the in-memory client table with the demo clients."""
    now = now or datetime.now(timezone.utc)
    with client_status_lock:
        client_status.clear()
        for cid, version, ip, city, region, country, provider, dns_loc, dns_colo, minutes in DEMO_CLIENTS:
            client_status[cid] = {
                "last_seen": (now - timedelta(minutes=minutes)).isoformat(),
                "ip": ip,
                "location": f"{city}, {region}, {country}",
                "provider": provider,
                "country": country,
                "city": city,
                "region": region,
                "timezone": "UTC",
                "dns_loc": dns_loc,
                "dns_colo": dns_colo,
                "client_version": version,
            }


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18090
    dashboard_routes.get_server_info = lambda: dict(DEMO_SERVER_INFO)
    load_demo_clients()
    server = make_server("127.0.0.1", port, dashboard_routes.dashboard_app)
    print(f"Demo dashboard on http://127.0.0.1:{port}/dashboard", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
