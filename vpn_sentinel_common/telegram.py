"""Telegram integration with notifications and bot commands."""
import requests
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Callable
from .log_utils import log_info, log_error, log_warn
from .country_codes import compare_country_codes

# Read configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
TELEGRAM_ENABLED_ENV = os.getenv('VPN_SENTINEL_TELEGRAM_ENABLED', '').lower()

# Determine if Telegram should be enabled
if TELEGRAM_ENABLED_ENV == 'true':
    # Explicit enable - validate credentials are present
    if not TELEGRAM_BOT_TOKEN:
        log_error('telegram', '❌ VPN_SENTINEL_TELEGRAM_ENABLED=true but TELEGRAM_BOT_TOKEN is not set')
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        log_error('telegram', '❌ VPN_SENTINEL_TELEGRAM_ENABLED=true but TELEGRAM_CHAT_ID is not set')
        sys.exit(1)
    TELEGRAM_ENABLED = True
elif TELEGRAM_ENABLED_ENV == 'false':
    # Explicit disable
    TELEGRAM_ENABLED = False
else:
    # Auto-detect based on credentials presence
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# Track message offset for polling
_last_update_id = 0
_command_handlers: Dict[str, Callable] = {}


def send_telegram_message(message: str, silent: bool = False) -> bool:
    """Send a message via Telegram Bot API.

    Args:
        message: Message text (HTML formatted)
        silent: If True, send without notification sound

    Returns:
        True if message sent successfully
    """
    if not TELEGRAM_ENABLED:
        log_warn('telegram', '⚠️ Telegram not configured (missing BOT_TOKEN or CHAT_ID)')
        return False

    try:
        # Log outgoing message
        preview = message[:100].replace('\n', ' ')
        log_info('telegram', f'📤 Sending message: {preview}...')

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_notification": silent
        }
        response = requests.post(url, json=data, timeout=10, verify=True)
        success = response.status_code == 200

        if success:
            log_info('telegram', '✅ Message sent successfully')
        else:
            log_error('telegram', f'❌ Failed to send message: HTTP {response.status_code}')
            log_error('telegram', f'Response: {response.text}')

        return success
    except Exception as e:
        log_error('telegram', f'❌ Error sending message: {e}')
        return False


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format datetime for Telegram messages.

    Args:
        dt: Datetime to format (uses current time if None)

    Returns:
        Formatted string like "2025-10-21 10:10:13 UTC"
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')


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


def notify_client_connected(client_id: str, vpn_ip: str, location: str,
                            city: str, region: str, country: str,
                            provider: str, timezone: str,
                            dns_loc: str = "Unknown", dns_colo: str = "Unknown",
                            server_ip: str = "Unknown", client_version: str = "Unknown") -> bool:
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
        dns_leak = (dns_loc != "Unknown" and country != "Unknown" and 
                   not compare_country_codes(dns_loc, country))
        
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


def notify_ip_changed(client_id: str, old_ip: str, new_ip: str,
                      city: str, region: str, country: str,
                      provider: str, timezone: str,
                      dns_loc: str = "Unknown", dns_colo: str = "Unknown",
                      server_ip: str = "Unknown", client_version: str = "Unknown") -> bool:
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
        dns_leak = (dns_loc != "Unknown" and country != "Unknown" and 
                   not compare_country_codes(dns_loc, country))
        
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
    log_info('telegram', f'📝 Registered command: /{command}')


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
            return data.get('result', [])
        else:
            log_error('telegram', f'❌ Failed to get updates: HTTP {response.status_code}')
            return []
    except Exception as e:
        log_error('telegram', f'❌ Error getting updates: {e}')
        return []


def process_command(chat_id: str, message_text: str, message_id: int) -> None:
    """Process a Telegram bot command.

    Args:
        chat_id: Chat ID where command was sent
        message_text: Full message text
        message_id: Message ID
    """
    # Log incoming message
    log_info('telegram', f'📥 Received message (ID {message_id}): {message_text}')

    if not message_text.startswith('/'):
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
        log_info('telegram', f'🎯 Processing command: /{command}')
        _command_handlers[command](chat_id, message_text)
    else:
        log_warn('telegram', f'⚠️ Unknown command: /{command}')
        response = f"""❓ Unknown command: /{command}

<b>Available commands:</b>
🏓 /ping - Test connectivity
📊 /status - Get VPN status
❓ /help - Show help"""
        send_telegram_message(response)


def polling_loop() -> None:
    """Main polling loop for Telegram bot (runs in background thread)."""
    global _last_update_id

    log_info('telegram', '🤖 Starting Telegram bot polling loop')

    while True:
        try:
            updates = get_updates(_last_update_id + 1)

            for update in updates:
                _last_update_id = update['update_id']

                # Extract message info
                if 'message' in update:
                    message = update['message']
                    chat_id = str(message['chat']['id'])
                    message_text = message.get('text', '')
                    message_id = message['message_id']

                    # Only process if from our configured chat
                    if chat_id == TELEGRAM_CHAT_ID:
                        process_command(chat_id, message_text, message_id)
                    else:
                        log_warn('telegram', f'⚠️ Ignoring message from unauthorized chat: {chat_id}')

            time.sleep(1)  # Brief pause between polling cycles

        except Exception as e:
            log_error('telegram', f'❌ Error in polling loop: {e}')
            time.sleep(5)  # Longer pause on error


def start_polling() -> threading.Thread:
    """Start Telegram bot polling in background thread.

    Returns:
        Thread object running the polling loop
    """
    if not TELEGRAM_ENABLED:
        log_warn('telegram', '⚠️ Telegram polling not started (not configured)')
        return None

    thread = threading.Thread(target=polling_loop, daemon=True, name='telegram-bot')
    thread.start()
    log_info('telegram', '✅ Telegram bot polling started')
    return thread
