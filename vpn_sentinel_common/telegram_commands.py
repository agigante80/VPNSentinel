"""Telegram bot command handlers for VPN Sentinel."""
from . import telegram
from .log_utils import log_info
from datetime import datetime


def format_time_ago(iso_string: str) -> str:
    """Format ISO time string as 'X minutes ago'.

    Args:
        iso_string: ISO format datetime string

    Returns:
        Human-readable time ago string
    """
    try:
        last_seen = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        now = datetime.utcnow()
        delta = now - last_seen
        minutes = int(delta.total_seconds() / 60)

        if minutes < 1:
            return "just now"
        elif minutes == 1:
            return "1 minute ago"
        elif minutes < 60:
            return f"{minutes} minutes ago"
        else:
            hours = minutes // 60
            if hours == 1:
                return "1 hour ago"
            else:
                return f"{hours} hours ago"
    except Exception:
        return "unknown"


def handle_ping(chat_id: str, message_text: str) -> None:
    """Handle /ping command.

    Args:
        chat_id: Telegram chat ID
        message_text: Full message text
    """
    from .api_routes import client_status

    active_count = len(client_status)
    server_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    response = f"""🏓 <b>Pong!</b>

Server time: {server_time}
Active clients: {active_count}
Alert threshold: 15 minutes
Check interval: 5 minutes"""

    telegram.send_telegram_message(response)


def handle_status(chat_id: str, message_text: str) -> None:
    """Handle /status command.

    Args:
        chat_id: Telegram chat ID
        message_text: Full message text
    """
    from .api_routes import client_status

    if not client_status:
        response = """📊 <b>VPN Status</b>

No active VPN clients connected.

Server time: """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        telegram.send_telegram_message(response)
        return

    response = "📊 <b>VPN Status</b>\n\n"

    for client_id, info in client_status.items():
        last_seen_str = format_time_ago(info.get('last_seen', ''))
        vpn_ip = info.get('ip', 'unknown')
        location = info.get('location', 'unknown')

        response += f"""🟢 <code>{client_id}</code> - Online
   IP: <code>{vpn_ip}</code>
   Location: {location}
   Last seen: {last_seen_str}

"""

    response += "\nServer time: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    telegram.send_telegram_message(response)


def handle_help(chat_id: str, message_text: str) -> None:
    """Handle /help command.

    Args:
        chat_id: Telegram chat ID
        message_text: Full message text
    """
    response = """❓ <b>VPN Sentinel Bot Help</b>

I monitor your VPN connections and send alerts.

<b>Available Commands:</b>

🏓 <b>/ping</b>
   Test bot connectivity and get server info

📊 <b>/status</b>
   Get detailed status of all VPN clients
   Shows IP, location, and last seen time

❓ <b>/help</b>
   Show this help message

<b>Automatic Notifications:</b>
• New client connects
• Client IP changes
• Client disconnects/timeout
• No clients connected

The bot monitors VPN connections 24/7 and sends alerts automatically."""

    telegram.send_telegram_message(response)


def register_all_commands() -> None:
    """Register all bot command handlers."""
    telegram.register_command('ping', handle_ping)
    telegram.register_command('status', handle_status)
    telegram.register_command('help', handle_help)
    log_info('telegram', '✅ Registered all bot commands')
