#!/usr/bin/env python3
"""Test script for Telegram integration.

Usage:
    export TELEGRAM_BOT_TOKEN="your-bot-token"
    export TELEGRAM_CHAT_ID="your-chat-id"
    python3 tests/test_telegram_manual.py
"""
import sys
import os

# Add vpn_sentinel_common to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vpn_sentinel_common import telegram


def main():
    """Test Telegram integration."""
    print("🧪 Testing Telegram Integration\n")
    
    if not telegram.TELEGRAM_ENABLED:
        print("❌ Telegram is not configured!")
        print("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        sys.exit(1)
    
    print(f"✅ Telegram is configured")
    print(f"   Bot Token: {telegram.TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"   Chat ID: {telegram.TELEGRAM_CHAT_ID}\n")
    
    # Test 1: Server started notification
    print("📤 Test 1: Server started notification...")
    success = telegram.notify_server_started()
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}\n")
    
    # Test 2: Client connected notification
    print("📤 Test 2: Client connected notification...")
    success = telegram.notify_client_connected(
        client_id="test-client",
        vpn_ip="185.72.199.129",
        location="Toruń, Kujawsko-Pomorskie, PL",
        city="Toruń",
        region="Kujawsko-Pomorskie",
        country="PL",
        provider="AS50599 DATASPACE P.S.A.",
        timezone="Europe/Warsaw",
        dns_loc="PL",
        dns_colo="WAW"
    )
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}\n")
    
    # Test 3: IP changed notification
    print("📤 Test 3: IP changed notification...")
    success = telegram.notify_ip_changed(
        client_id="test-client",
        old_ip="185.72.199.129",
        new_ip="89.40.181.202",
        city="Warsaw",
        region="Mazowieckie",
        country="PL",
        provider="AS12741 netia.pl",
        timezone="Europe/Warsaw",
        dns_loc="PL",
        dns_colo="WAW"
    )
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}\n")
    
    # Test 4: No clients alert
    print("📤 Test 4: No clients alert...")
    success = telegram.notify_no_clients()
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}\n")
    
    # Test 5: Simple message
    print("📤 Test 5: Simple test message...")
    success = telegram.send_telegram_message("🧪 <b>Test message from VPN Sentinel</b>\n\nThis is a test.")
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}\n")
    
    print("=" * 60)
    print("✅ All tests completed!")
    print("\n💡 Now test bot commands by sending these messages in Telegram:")
    print("   /ping")
    print("   /status")
    print("   /help")
    print("   any other text")


if __name__ == '__main__':
    main()
