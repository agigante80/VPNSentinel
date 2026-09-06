"""Telegram integration with notifications and bot commands."""

import requests
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Callable, List, Tuple
from .log_utils import log_info, log_error, log_warn
from .country_codes import compare_country_codes

# Read configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED_ENV = os.getenv("VPN_SENTINEL_TELEGRAM_ENABLED", "").lower()

# Determine if Telegram should be enabled
if TELEGRAM_ENABLED_ENV == "true":
    # Explicit enable - validate credentials are present
    if not TELEGRAM_BOT_TOKEN:
        log_error("telegram", "❌ VPN_SENTINEL_TELEGRAM_ENABLED=true but TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        log_error("telegram", "❌ VPN_SENTINEL_TELEGRAM_ENABLED=true but TELEGRAM_CHAT_ID is not set")
        sys.exit(1)
    TELEGRAM_ENABLED = True
elif TELEGRAM_ENABLED_ENV == "false":
    # Explicit disable
    TELEGRAM_ENABLED = False
else:
    # Auto-detect based on credentials presence
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# Track message offset for polling
_last_update_id = 0
_command_handlers: Dict[str, Callable] = {}

# --- Telegram API hard limits (see issue #95 research comment for sources) ---

# Telegram rejects (does not truncate) any message whose text is longer than this once
# HTML entities are parsed. Chunking logic below must keep every rendered message under it.
TELEGRAM_MESSAGE_CHAR_LIMIT = 4096

# Hard cap on how many messages a single notify_clients_silent() call will ever send.
# Naive unbounded chunking of a huge sweep would trade one failure (message too long) for
# another (Telegram's ~30 messages/second per-chat rate limit, tighter still for groups,
# every API call counted). When a sweep would need more messages than this, the final
# message summarises the remainder as a count instead of sending more messages.
MAX_SILENT_CLIENT_MESSAGES = 5

# --- send_telegram_message retry-on-429 tuning ---
#
# send_telegram_message() is called both from background threads (the cleanup sweep, where
# blocking is harmless) and synchronously from the Flask /keepalive request handler (via
# notify_client_connected / notify_ip_changed), where any sleep here directly adds to the
# client's HTTP response latency. These two constants exist to bound that latency:
#
# - TELEGRAM_MAX_SEND_ATTEMPTS caps how many times we will call the API for one message, so
#   a persistent rate limit cannot turn into an unbounded retry loop.
# - TELEGRAM_RETRY_AFTER_CAP_SECONDS caps how long we are willing to sleep even when Telegram
#   asks for more via `parameters.retry_after`. If the API asks for longer than this, we do
#   NOT sleep -- we log at error level and give up, returning False. This is intentional: do
#   not "improve" this by removing the cap or always honouring retry_after verbatim, or a
#   Telegram-side back-pressure event becomes VPN monitor request latency on every keepalive.
TELEGRAM_MAX_SEND_ATTEMPTS = 2
TELEGRAM_RETRY_AFTER_CAP_SECONDS = 5


def _extract_retry_after(response: "requests.Response") -> Optional[int]:
    """Pull `parameters.retry_after` out of a Telegram 429 response body.

    Telegram's guidance is to treat this value as authoritative rather than inventing our
    own backoff. Returns None if the body is missing, not JSON, or does not carry it.
    """
    try:
        body = response.json()
    except ValueError:
        return None

    parameters = body.get("parameters") if isinstance(body, dict) else None
    if not isinstance(parameters, dict):
        return None

    retry_after = parameters.get("retry_after")
    if isinstance(retry_after, bool) or not isinstance(retry_after, (int, float)):
        return None

    return retry_after


def send_telegram_message(message: str, silent: bool = False) -> bool:
    """Send a message via Telegram Bot API.

    Retries once on HTTP 429 when the API's own `retry_after` is small enough to be worth
    waiting for (see TELEGRAM_RETRY_AFTER_CAP_SECONDS). This function is called from the
    Flask keepalive request path as well as the background cleanup thread, so the retry is
    deliberately bounded rather than honouring an arbitrarily long retry_after.

    Args:
        message: Message text (HTML formatted)
        silent: If True, send without notification sound

    Returns:
        True if message sent successfully
    """
    if not TELEGRAM_ENABLED:
        log_warn("telegram", "⚠️ Telegram not configured (missing BOT_TOKEN or CHAT_ID)")
        return False

    preview = message[:100].replace("\n", " ")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML", "disable_notification": silent}

    for attempt in range(1, TELEGRAM_MAX_SEND_ATTEMPTS + 1):
        try:
            log_info("telegram", f"📤 Sending message: {preview}... (attempt {attempt}/{TELEGRAM_MAX_SEND_ATTEMPTS})")
            response = requests.post(url, json=data, timeout=10, verify=True)

            if response.status_code == 200:
                log_info("telegram", "✅ Message sent successfully")
                return True

            if response.status_code == 429 and attempt < TELEGRAM_MAX_SEND_ATTEMPTS:
                retry_after = _extract_retry_after(response)
                if retry_after is not None and retry_after <= TELEGRAM_RETRY_AFTER_CAP_SECONDS:
                    log_warn(
                        "telegram",
                        f"⚠️ Rate limited (429); retrying in {retry_after}s per Telegram's retry_after "
                        f"(attempt {attempt}/{TELEGRAM_MAX_SEND_ATTEMPTS})",
                    )
                    time.sleep(retry_after)
                    continue
                log_error(
                    "telegram",
                    "❌ Rate limited (429) and retry_after "
                    f"({retry_after}) exceeds the {TELEGRAM_RETRY_AFTER_CAP_SECONDS}s cap or was not provided; "
                    f"giving up to protect request latency. Could not deliver: {preview}...",
                )
                return False

            log_error("telegram", f"❌ Failed to send message: HTTP {response.status_code}")
            log_error("telegram", f"Response: {response.text}")
            log_error("telegram", f"❌ Giving up on Telegram notification: {preview}...")
            return False
        except Exception as e:
            log_error("telegram", f"❌ Error sending message: {e}")
            log_error("telegram", f"❌ Giving up on Telegram notification: {preview}...")
            return False

    # Unreachable: every branch inside the loop returns. Kept only as a defensive
    # fallback in case TELEGRAM_MAX_SEND_ATTEMPTS is ever set to 0.
    return False  # pragma: no cover


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format datetime for Telegram messages.

    Args:
        dt: Datetime to format (uses current time if None)

    Returns:
        Formatted string like "2025-10-21 10:10:13 UTC"
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def notify_server_started(alert_threshold_min: int = 15, check_interval_min: int = 5) -> bool:
    """Send server startup notification.

    Args:
        alert_threshold_min: Minutes before alerting about missing client
        check_interval_min: Minutes between checks

    Returns:
        True if notification sent successfully
    """
    message = f"""🚀 <b>VPN Keepalive Server Started</b>

Server is now monitoring VPN connections.
Alert threshold: {alert_threshold_min} minutes
Check interval: {check_interval_min} minutes
🛡️ Security: Rate limiting (30 req/min)
🔐 API Auth: Enabled
Started at: {format_datetime()}

💡 Send /ping to test the connection!
📊 Send /status for detailed VPN status
❓ Send /help for all commands"""

    return send_telegram_message(message)


def notify_no_clients() -> bool:
    """Send alert when no VPN clients are connected.

    Returns:
        True if notification sent successfully
    """
    message = f"""⚠️ <b>No VPN Clients Connected</b>

No active VPN connections detected.
Time: {format_datetime()}

💡 This alert will not repeat until a client connects and disconnects again."""

    return send_telegram_message(message)


def _silent_client_line(client_id: str, minutes_silent: int) -> str:
    """Render one client's line for the multi-client silence alert."""
    return f"  - <code>{client_id}</code>: last seen {minutes_silent} minutes ago"


def _render_silent_clients_message(total: int, page_num: int, total_pages: int, body: str, summary: bool) -> str:
    """Render one page of the multi-client silence alert.

    `total` (the count of clients silent in this sweep) is always stated in the header, so
    the operator can always learn the total even when this page's body has been summarised
    rather than listing every client by name.
    """
    header = f"🔇 <b>{total} Clients Went Silent</b>"
    if total_pages > 1:
        header += f" (message {page_num}/{total_pages})"

    intro = (
        "Additional clients also went silent in this sweep and are not listed individually:"
        if summary
        else "The following clients stopped sending keepalives:"
    )

    return f"""{header}

{intro}
{body}

Time: {format_datetime()}

⚠️ Check that these client containers and their VPN connections are still up."""


def _chunk_silent_clients_messages(clients: List[Tuple[str, int]]) -> List[str]:
    """Split a multi-client silence alert into one or more Telegram messages.

    Every message is kept under TELEGRAM_MESSAGE_CHAR_LIMIT (Telegram rejects the whole
    message outright above that, it does not truncate). The number of messages is capped at
    MAX_SILENT_CLIENT_MESSAGES to avoid trading that failure for a rate-limit one; when the
    sweep needs more pages than the cap allows, the final message summarises the remainder as
    a count instead of naming it. The total client count is stated in every message's header.
    """
    total = len(clients)
    lines = [_silent_client_line(client_id, minutes_silent) for client_id, minutes_silent in clients]

    # Worst-case per-page overhead (header incl. pagination suffix + intro + footer, empty
    # body). Computed with the largest page numbers and both intro variants so the packing
    # budget below never under-estimates the fixed cost of a page.
    overhead = max(
        len(_render_silent_clients_message(total, MAX_SILENT_CLIENT_MESSAGES, MAX_SILENT_CLIENT_MESSAGES, "", s))
        for s in (True, False)
    )
    budget = max(TELEGRAM_MESSAGE_CHAR_LIMIT - overhead, 1)

    pages: List[List[str]] = []
    current: List[str] = []
    current_len = 0
    for line in lines:
        # Defend against a single pathological line wider than the whole budget: truncate it
        # rather than letting it blow the hard limit on its own page.
        if len(line) > budget:
            line = line[: budget - 3] + "..."

        added_len = len(line) + (1 if current else 0)  # +1 for the joining newline
        if current and current_len + added_len > budget:
            pages.append(current)
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += added_len
    if current:
        pages.append(current)

    if len(pages) <= MAX_SILENT_CLIENT_MESSAGES:
        total_pages = len(pages)
        return [
            _render_silent_clients_message(total, i + 1, total_pages, "\n".join(page), summary=False)
            for i, page in enumerate(pages)
        ]

    # The sweep needs more pages than the cap: keep the first (cap - 1) as full detail pages
    # and fold everything else into one summary tail naming only the remainder count.
    total_pages = MAX_SILENT_CLIENT_MESSAGES
    detail_page_count = MAX_SILENT_CLIENT_MESSAGES - 1
    detail_pages = pages[:detail_page_count]
    remainder_pages = pages[detail_page_count:]
    remainder_count = sum(len(page) for page in remainder_pages)

    messages = [
        _render_silent_clients_message(total, i + 1, total_pages, "\n".join(page), summary=False)
        for i, page in enumerate(detail_pages)
    ]
    summary_body = f"  ... and {remainder_count} more client(s) went silent (not listed individually)."
    messages.append(_render_silent_clients_message(total, total_pages, total_pages, summary_body, summary=True))
    return messages


def notify_clients_silent(clients: List[Tuple[str, int]]) -> bool:
    """Send alert when one or more clients stop sending keepalives.

    Handles both the single-client and multi-client case in one call, since a
    single cleanup sweep can remove several clients at once. A small batch is sent as a
    single message; a batch large enough to exceed the Telegram message-length limit is
    split into multiple messages (see _chunk_silent_clients_messages), each of which is
    always under the limit, up to a bounded maximum number of messages.

    Args:
        clients: List of (client_id, minutes_silent) tuples for clients that
            went silent in this sweep. Must not be empty.

    Returns:
        True if every message for this sweep sent successfully, False if the list was
        empty or any send failed.
    """
    if not clients:
        return False

    if len(clients) == 1:
        client_id, minutes_silent = clients[0]
        message = f"""🔇 <b>Client Went Silent</b>

Client <code>{client_id}</code> stopped sending keepalives.
Last seen: {minutes_silent} minutes ago
Time: {format_datetime()}

⚠️ Check that the client container and its VPN connection are still up."""
        return send_telegram_message(message)

    all_sent = True
    for message in _chunk_silent_clients_messages(clients):
        if not send_telegram_message(message):
            all_sent = False
    return all_sent


def notify_client_connected(
    client_id: str,
    vpn_ip: str,
    location: str,
    city: str,
    region: str,
    country: str,
    provider: str,
    timezone: str,
    dns_loc: str = "Unknown",
    dns_colo: str = "Unknown",
    server_ip: str = "Unknown",
    client_version: str = "Unknown",
) -> bool:
    """Send notification when a VPN client connects.

    Args:
        client_id: Client identifier
        vpn_ip: VPN IP address
        location: Full location string
        city: City name
        region: Region/state name
        country: Country code
        provider: ISP/provider name
        timezone: Timezone string
        dns_loc: DNS location code
        dns_colo: DNS colocation server
        server_ip: Server's public IP for comparison
        client_version: Client version string

    Returns:
        True if notification sent successfully
    """
    # Check for VPN bypass (same IP as server)
    if vpn_ip == server_ip or vpn_ip == "unknown" or vpn_ip == "Unknown":
        status_emoji = "🔴"
        status_text = "<b>⚠️ VPN BYPASS DETECTED!</b>"
        status_detail = "Client IP matches server IP - VPN is NOT working!"
        dns_status = "🔴 Unable to verify - VPN not active"
    else:
        # VPN is working, check DNS leak
        # Compare normalized country codes (handles "Romania" vs "RO")
        dns_leak = dns_loc != "Unknown" and country != "Unknown" and not compare_country_codes(dns_loc, country)

        if dns_leak:
            status_emoji = "🟡"
            status_text = "<b>⚠️ DNS Leak Detected</b>"
            status_detail = f"VPN is active but DNS queries leak to: {dns_loc}"
            dns_status = "🟡 DNS leak detected"
        elif dns_loc == "Unknown":
            status_emoji = "🟡"
            status_text = "<b>⚠️ DNS Test Inconclusive</b>"
            status_detail = "VPN is active but DNS status could not be verified"
            dns_status = "❓ DNS leak test inconclusive"
        else:
            status_emoji = "🟢"
            status_text = "<b>✅ Secure Connection</b>"
            status_detail = "VPN is active and no DNS leak detected"
            dns_status = "✅ No DNS leak detected"

    message = f"""{status_emoji} <b>VPN Connected!</b>

{status_text}
{status_detail}

Client: <code>{client_id}</code>
📦 Version: <code>{client_version}</code>
VPN IP: <code>{vpn_ip}</code>
Server IP: <code>{server_ip}</code>
📍 Location: {city}, {region}, {country}
🏢 Provider: {provider}
🕒 VPN Timezone: {timezone}
Connected at: {format_datetime()}

🔒 DNS Leak Test:
DNS Location: {dns_loc}
DNS Server: {dns_colo}
{dns_status}"""

    return send_telegram_message(message)


def notify_ip_changed(
    client_id: str,
    old_ip: str,
    new_ip: str,
    city: str,
    region: str,
    country: str,
    provider: str,
    timezone: str,
    dns_loc: str = "Unknown",
    dns_colo: str = "Unknown",
    server_ip: str = "Unknown",
    client_version: str = "Unknown",
) -> bool:
    """Send notification when a client's VPN IP changes.

    Args:
        client_id: Client identifier
        old_ip: Previous IP address
        new_ip: New IP address
        city: City name
        region: Region/state name
        country: Country code
        provider: ISP/provider name
        timezone: Timezone string
        dns_loc: DNS location code
        dns_colo: DNS colocation server
        server_ip: Server's public IP for comparison
        client_version: Client version string

    Returns:
        True if notification sent successfully
    """
    # Check for VPN bypass (same IP as server)
    if new_ip == server_ip or new_ip == "unknown" or new_ip == "Unknown":
        status_emoji = "🔴"
        status_text = "<b>⚠️ VPN BYPASS DETECTED!</b>"
        status_detail = "Client IP matches server IP - VPN is NOT working!"
        dns_status = "🔴 Unable to verify - VPN not active"
    else:
        # VPN is working, check DNS leak
        # Compare normalized country codes (handles "Romania" vs "RO")
        dns_leak = dns_loc != "Unknown" and country != "Unknown" and not compare_country_codes(dns_loc, country)

        if dns_leak:
            status_emoji = "🟡"
            status_text = "<b>⚠️ DNS Leak Detected</b>"
            status_detail = f"VPN is active but DNS queries leak to: {dns_loc}"
            dns_status = "🟡 DNS leak detected"
        elif dns_loc == "Unknown":
            status_emoji = "🟡"
            status_text = "<b>⚠️ DNS Test Inconclusive</b>"
            status_detail = "VPN is active but DNS status could not be verified"
            dns_status = "❓ DNS leak test inconclusive"
        else:
            status_emoji = "🟢"
            status_text = "<b>✅ Secure Connection</b>"
            status_detail = "VPN is active and no DNS leak detected"
            dns_status = "✅ No DNS leak detected"

    message = f"""{status_emoji} <b>VPN IP Changed!</b>

{status_text}
{status_detail}

Previous IP: <code>{old_ip}</code>
Client: <code>{client_id}</code>
📦 Version: <code>{client_version}</code>
VPN IP: <code>{new_ip}</code>
Server IP: <code>{server_ip}</code>
📍 Location: {city}, {region}, {country}
🏢 Provider: {provider}
🕒 VPN Timezone: {timezone}
Connected at: {format_datetime()}

🔒 DNS Leak Test:
DNS Location: {dns_loc}
DNS Server: {dns_colo}
{dns_status}"""

    return send_telegram_message(message)


def register_command(command: str, handler: Callable) -> None:
    """Register a Telegram bot command handler.

    Args:
        command: Command name (without /)
        handler: Function to call with (chat_id, message_text)
    """
    _command_handlers[command] = handler
    log_info("telegram", f"📝 Registered command: /{command}")


def get_updates(offset: int = 0) -> list:
    """Get updates from Telegram Bot API.

    Args:
        offset: Update ID offset for polling

    Returns:
        List of update objects
    """
    if not TELEGRAM_ENABLED:
        return []

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"offset": offset, "timeout": 30}
        response = requests.get(url, params=params, timeout=35, verify=True)

        if response.status_code == 200:
            data = response.json()
            return data.get("result", [])
        else:
            log_error("telegram", f"❌ Failed to get updates: HTTP {response.status_code}")
            return []
    except Exception as e:
        log_error("telegram", f"❌ Error getting updates: {e}")
        return []


def process_command(chat_id: str, message_text: str, message_id: int) -> None:
    """Process a Telegram bot command.

    Args:
        chat_id: Chat ID where command was sent
        message_text: Full message text
        message_id: Message ID
    """
    # Log incoming message
    log_info("telegram", f"📥 Received message (ID {message_id}): {message_text}")

    if not message_text.startswith("/"):
        # Not a command, send helpful response
        response = f"""👋 Hello! I'm your VPN monitoring bot.

I received: {message_text}

Use /help to see available commands.

<b>Available commands:</b>
🏓 /ping - Test connectivity
📊 /status - Get VPN status
❓ /help - Show help"""
        send_telegram_message(response)
        return

    # Extract command and call handler
    command = message_text.split()[0][1:].lower()  # Remove / and get first word

    if command in _command_handlers:
        log_info("telegram", f"🎯 Processing command: /{command}")
        _command_handlers[command](chat_id, message_text)
    else:
        log_warn("telegram", f"⚠️ Unknown command: /{command}")
        response = f"""❓ Unknown command: /{command}

<b>Available commands:</b>
🏓 /ping - Test connectivity
📊 /status - Get VPN status
❓ /help - Show help"""
        send_telegram_message(response)


def polling_loop() -> None:
    """Main polling loop for Telegram bot (runs in background thread)."""
    global _last_update_id

    log_info("telegram", "🤖 Starting Telegram bot polling loop")

    while True:
        try:
            updates = get_updates(_last_update_id + 1)

            for update in updates:
                _last_update_id = update["update_id"]

                # Extract message info
                if "message" in update:
                    message = update["message"]
                    chat_id = str(message["chat"]["id"])
                    message_text = message.get("text", "")
                    message_id = message["message_id"]

                    # Only process if from our configured chat
                    if chat_id == TELEGRAM_CHAT_ID:
                        process_command(chat_id, message_text, message_id)
                    else:
                        log_warn("telegram", f"⚠️ Ignoring message from unauthorized chat: {chat_id}")

            time.sleep(1)  # Brief pause between polling cycles

        except Exception as e:
            log_error("telegram", f"❌ Error in polling loop: {e}")
            time.sleep(5)  # Longer pause on error


def start_polling() -> threading.Thread:
    """Start Telegram bot polling in background thread.

    Returns:
        Thread object running the polling loop
    """
    if not TELEGRAM_ENABLED:
        log_warn("telegram", "⚠️ Telegram polling not started (not configured)")
        return None

    thread = threading.Thread(target=polling_loop, daemon=True, name="telegram-bot")
    thread.start()
    log_info("telegram", "✅ Telegram bot polling started")
    return thread
