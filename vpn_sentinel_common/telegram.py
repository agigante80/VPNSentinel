"""Telegram integration helpers migrated from vpn_sentinel_server."""
import requests
import os
from .log_utils import log_info, log_error

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')


def send_telegram_message(message: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=data, timeout=10, verify=True)
        success = response.status_code == 200
        if success:
            log_info('telegram', '✅ Message sent successfully')
        else:
            log_error('telegram', f'❌ Failed to send message: HTTP {response.status_code}')
        return success
    except Exception as e:
        log_error('telegram', f'❌ Error: {e}')
        return False
