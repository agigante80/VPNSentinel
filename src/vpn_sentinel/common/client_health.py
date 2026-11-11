"""Client health classification shared by the dashboard and the /metrics endpoint.

Kept free of Flask and api_routes imports so both callers can use it without cycles.
"""

from .country_codes import compare_country_codes


def classify_client(client, server_ip):
    """Return "green", "yellow" or "red" for a stored client record.

    red: the client's public IP equals the server's (VPN bypass) or is undetectable.
    yellow: DNS leak (resolver country differs from the client's) or undetectable DNS.
    green: everything else.
    """
    client_ip = client.get("ip", "unknown")
    dns_loc = client.get("dns_loc", "Unknown")
    country = client.get("country", "Unknown")

    if client_ip == server_ip or client_ip == "unknown" or client_ip == "Unknown":
        return "red"

    dns_leak = False
    if dns_loc != "Unknown" and country != "Unknown":
        dns_leak = not compare_country_codes(dns_loc, country)

    if dns_leak or dns_loc == "Unknown":
        return "yellow"

    return "green"
