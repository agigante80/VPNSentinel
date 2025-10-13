#!/usr/bin/env python3

"""
=============================================================================
VPN Sentinel Monitoring Server
=============================================================================

A comprehensive VPN monitoring server that receives keepalive messages from
VPN clients, performs DNS leak detection, and sends real-time notifications
via Telegram. Designed to work with any VPN-protected Docker environment.

Features:
- Real-time VPN client monitoring and status tracking
- DNS leak detection and alerting system
- Telegram bot integration for instant notifications
- Rate limiting and security middleware
- IP change detection and geolocation tracking
- Client health monitoring with customizable thresholds
- RESTful API endpoints for status queries
- Interactive Telegram commands (/ping, /status, /help)

Architecture:
- Flask web server for HTTP API endpoints
- Threading for concurrent client monitoring
- In-memory storage for client status (production: consider Redis/DB)
- Telegram Bot API integration for notifications
- Security features: rate limiting, IP whitelisting, API key auth

Environment Variables:
- TELEGRAM_BOT_TOKEN: Telegram bot token for notifications (required)
- TELEGRAM_CHAT_ID: Target chat ID for notifications (required) 
- VPN_SENTINEL_API_KEY: API key for client authentication (optional)
- VPN_SENTINEL_SERVER_ALLOWED_IPS: Comma-separated IP whitelist (optional)
- VPN_SENTINEL_SERVER_API_PATH: API path prefix (default: /api/v1)
- TZ: Timezone for timestamps (default: UTC)
- VPN_SENTINEL_SERVER_RATE_LIMIT_REQUESTS: Rate limit per IP (default: 30)

API Endpoints:
- POST /keepalive: Receive client status updates
- GET /status: Get server and client status
- POST /heartbeat: Simulate keepalive for testing
- GET /health: Health check endpoint

Security Features:
- API key authentication for keepalive endpoints
- Rate limiting per IP address
- IP whitelisting support
- Request logging with security headers
- Input validation and sanitization

Dependencies:
- flask: Web framework for API endpoints
- requests: HTTP client for Telegram API calls
- pytz: Timezone handling for accurate timestamps

Usage:
    python vpn-sentinel-server.py

Docker Usage:
    docker run -p 5000:5000 \
        -e TELEGRAM_BOT_TOKEN=your_token \
        -e TELEGRAM_CHAT_ID=your_chat_id \
        vpn-sentinel/server

Author: VPN Sentinel Project
License: MIT
Version: 1.0.0
Repository: https://github.com/your-username/vpn-sentinel
=============================================================================
"""

# =============================================================================
# Import Dependencies
# =============================================================================

import json              # JSON parsing and generation
import time              # Time handling and sleep functions
import threading         # Background thread management for monitoring
import os                # Environment variable access
from datetime import datetime, timedelta  # Date/time operations
from flask import Flask, request, jsonify # Web framework and HTTP utilities
from collections import defaultdict, deque # Data structures for rate limiting
import requests          # HTTP client for Telegram API communication
import pytz             # Timezone handling for accurate timestamps

# =============================================================================
# Application Configuration and Constants
# =============================================================================

# Initialize Flask application
app = Flask(__name__)

# Telegram Bot Configuration
# These credentials enable the server to send notifications via Telegram Bot API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# API Configuration
API_PATH = os.getenv("VPN_SENTINEL_SERVER_API_PATH", "/api/v1")          # API path prefix for endpoints

# Security Configuration
API_KEY = os.getenv("VPN_SENTINEL_API_KEY", "")                          # Optional API key for authentication
ALLOWED_IPS = os.getenv("VPN_SENTINEL_SERVER_ALLOWED_IPS", "").split(",") if os.getenv("VPN_SENTINEL_SERVER_ALLOWED_IPS") else []  # IP whitelist

# Rate Limiting Configuration
# Prevents abuse by limiting requests per IP address
RATE_LIMIT_REQUESTS = int(os.getenv("VPN_SENTINEL_SERVER_RATE_LIMIT_REQUESTS", "30"))  # Max requests per IP per minute
RATE_LIMIT_WINDOW = 60                                                # Time window in seconds

# Monitoring Configuration
ALERT_THRESHOLD_MINUTES = 15    # Minutes before considering a client offline
CHECK_INTERVAL_MINUTES = 5      # How often to check client status (background thread)

# Timezone Configuration
# Ensures consistent timestamp formatting across different deployment environments
TIMEZONE = pytz.timezone(os.getenv("TZ", "UTC"))

# =============================================================================
# Global State Management
# =============================================================================

# Client Status Storage
# In production environments, consider using Redis or a database for persistence
clients = {}                    # Dict[str, Dict]: Active client information and status
announced_clients = set()       # Set[str]: Clients that have been announced to prevent spam
no_clients_alert_sent = False   # Bool: Flag to prevent repeated "no clients" notifications

# Rate Limiting Storage
# Maps IP addresses to deque of recent request timestamps
rate_limit_storage = defaultdict(deque)  # Dict[str, deque]: IP -> request timestamps

# Server IP Detection (cached)
server_public_ip = None  # Cached server public IP for VPN detection warnings

# =============================================================================
# Utility Functions
# =============================================================================

def get_current_time():
    """
    Get current time in configured timezone.
    
    Returns:
        datetime: Current datetime object with timezone information
        
    Note:
        Uses the TIMEZONE constant configured from TZ environment variable.
        Ensures consistent timestamp formatting across all server operations.
    """
    return datetime.now(TIMEZONE)

def log_message(level, message):
    """
    Log a message with structured format: timestamp level message
    
    Args:
        level (str): Log level (INFO, ERROR, WARN)
        message (str): Message to log
    """
    timestamp = datetime.now(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"{timestamp} {level} {message}", flush=True)

def log_info(message):
    """Log an info message"""
    log_message("INFO", message)

def log_error(message):
    """Log an error message"""
    log_message("ERROR", message)

def log_warn(message):
    """Log a warning message"""
    log_message("WARN", message)

def get_server_public_ip():
    """
    Get the server's public IP address for comparison with client IPs.
    
    Returns:
        str: Server's public IP address or 'Unknown' if detection fails
        
    Note:
        Uses the same endpoint as clients (ipinfo.io) to ensure consistent results.
        Caches the result to avoid repeated API calls during server operation.
    """
    try:
        # Use the same service as clients to ensure consistent IP detection
        response = requests.get('https://ipinfo.io/json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('ip', 'Unknown')
    except Exception:
        pass
    
    # Fallback to alternative service
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('ip', 'Unknown')
    except Exception:
        pass
    
    return 'Unknown'

def send_telegram_message(message):
    """
    Send notification message via Telegram Bot API.
    
    Args:
        message (str): Message text to send (supports HTML formatting)
        
    Returns:
        bool: True if message sent successfully, False otherwise
        
    Features:
        - HTML formatting support for rich notifications
        - Automatic error handling and logging
        - 10-second timeout for API requests
        - Detailed success/failure logging with timestamps
        
    Environment Dependencies:
        - TELEGRAM_BOT_TOKEN: Bot token from @BotFather
        - TELEGRAM_CHAT_ID: Target chat ID for notifications
        
    Example:
        success = send_telegram_message("🚨 <b>VPN Alert!</b>\nConnection lost")
    """
    try:
        # Construct Telegram Bot API endpoint URL
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Prepare message payload with HTML parsing enabled
        data = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": message, 
            "parse_mode": "HTML"
        }
        
        # Send POST request with timeout protection
        response = requests.post(url, json=data, timeout=10)
        success = response.status_code == 200
        
        # Log operation result with structured format
        if success:
            log_info("✅ Telegram message sent successfully")
        else:
            log_error(f"❌ Failed to send Telegram message: HTTP {response.status_code}")
        
        return success
        
    except Exception as e:
        # Handle network errors, timeouts, and other exceptions
        log_error(f"❌ Telegram error: {e}")
        return False

# =============================================================================
# Security and Network Utility Functions
# =============================================================================

def get_client_ip():
    """
    Extract the real client IP address from HTTP request headers.
    
    Returns:
        str: Client IP address
        
    Behavior:
        - Checks X-Forwarded-For header first (proxy/load balancer scenarios)
        - Falls back to X-Real-IP header (reverse proxy scenarios) 
        - Uses direct connection IP as final fallback
        - Handles comma-separated X-Forwarded-For values (takes first IP)
        
    Security Note:
        In production behind proxies, ensure proxy sets headers correctly
        to prevent IP spoofing attacks.
    """
    if request.headers.get('X-Forwarded-For'):
        # Handle comma-separated list of IPs (take the first/original)
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        # Single IP from reverse proxy
        return request.headers.get('X-Real-IP')
    else:
        # Direct connection IP
        return request.remote_addr

def check_rate_limit(ip):
    """
    Implement sliding window rate limiting per IP address.
    
    Args:
        ip (str): Client IP address to check
        
    Returns:
        bool: True if request is allowed, False if rate limit exceeded
        
    Algorithm:
        - Maintains a deque of request timestamps per IP
        - Removes timestamps older than RATE_LIMIT_WINDOW seconds
        - Allows request if current count < RATE_LIMIT_REQUESTS
        - Adds current timestamp if request is allowed
        
    Configuration:
        - RATE_LIMIT_REQUESTS: Max requests per window (default: 30)
        - RATE_LIMIT_WINDOW: Time window in seconds (default: 60)
        
    Memory Management:
        - Automatically cleans old timestamps to prevent memory leaks
        - Uses deque for efficient left-side operations (O(1) popleft)
    """
    now = time.time()
    
    # Clean expired entries for this IP (sliding window maintenance)
    while rate_limit_storage[ip] and rate_limit_storage[ip][0] < now - RATE_LIMIT_WINDOW:
        rate_limit_storage[ip].popleft()
    
    # Check if rate limit would be exceeded
    if len(rate_limit_storage[ip]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request timestamp (request is allowed)
    rate_limit_storage[ip].append(now)
    return True

def check_ip_whitelist(ip):
    """
    Verify if IP address is allowed by whitelist configuration.
    
    Args:
        ip (str): Client IP address to verify
        
    Returns:
        bool: True if IP is allowed, False if blocked
        
    Behavior:
        - Returns True if no whitelist is configured (open access)
        - Returns True if IP is explicitly listed in ALLOWED_IPS
        - Returns False if whitelist exists but IP is not listed
        
    Configuration:
        Set VPN_SENTINEL_SERVER_ALLOWED_IPS environment variable as comma-separated list:
        VPN_SENTINEL_SERVER_ALLOWED_IPS="192.168.1.100,10.0.0.50,172.16.0.10"
        
    Security Note:
        Use in conjunction with proper firewall rules for defense in depth.
    """
    if not ALLOWED_IPS or ALLOWED_IPS == ['']:
        return True  # No whitelist configured - allow all IPs
    return ip in ALLOWED_IPS

def log_access(endpoint, ip, user_agent, auth_header, status):
    """
    Log API access attempts with security-relevant information.
    
    Args:
        endpoint (str): API endpoint being accessed
        ip (str): Client IP address
        user_agent (str): User-Agent header value
        auth_header (str): Authorization header value
        status (str): Response status (e.g., "200_OK", "403_BLOCKED")
        
    Log Format:
        [timestamp] 🌐 API Access: endpoint | IP: x.x.x.x | Auth: WITH_KEY/NO_KEY | Status: status | UA: user_agent...
        
    Security Features:
        - Truncates user agent to prevent log injection
        - Masks authorization header (shows presence, not value)
        - Includes timestamp in configured timezone
        - Uses flush=True for immediate log output
        
    Use Cases:
        - Security monitoring and intrusion detection
        - Access pattern analysis
        - Debugging authentication issues
        - Compliance and audit trails
    """
    auth_info = "WITH_KEY" if auth_header and auth_header.startswith("Bearer") else "NO_KEY"
    log_info(f"🌐 API Access: {endpoint} | IP: {ip} | Auth: {auth_info} | Status: {status} | UA: {user_agent[:50]}...")

def security_middleware():
    """
    Apply comprehensive security checks to incoming requests.
    
    Returns:
        tuple: (error_response, status_code) if request blocked, None if allowed
        
    Security Checks Applied:
        1. IP Whitelist Validation - Block non-whitelisted IPs
        2. Rate Limiting - Prevent abuse via request frequency limits
        
    Response Codes:
        - 403: IP address not in whitelist
        - 429: Rate limit exceeded
        
    Logging:
        - All blocked requests are logged with full details
        - Includes IP, endpoint, auth status, and block reason
        
    Integration:
        - Called by Flask before_request hook
        - Automatically applied to all routes
        - Returns early with error response if request should be blocked
        
    Performance:
        - Efficient O(1) IP lookups
        - Sliding window rate limiting with automatic cleanup
        - Minimal overhead for allowed requests
    """
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    auth_header = request.headers.get('Authorization', '')
    endpoint = request.endpoint or request.path
    
    # IP Whitelist Check
    if not check_ip_whitelist(client_ip):
        log_access(endpoint, client_ip, user_agent, auth_header, "403_IP_BLOCKED")
        return jsonify({'error': 'IP not allowed'}), 403
    
    # Rate Limit Check
    if not check_rate_limit(client_ip):
        log_access(endpoint, client_ip, user_agent, auth_header, "429_RATE_LIMITED")
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # API Key Authentication Check (REQUIRED - not optional)
    # Server will not respond to any requests without valid API key
    if not API_KEY:
        # API key not configured - server should not start
        log_access(endpoint, client_ip, user_agent, auth_header, "500_NO_API_KEY")
        return jsonify({'error': 'Server configuration error'}), 500
    
    if auth_header != f'Bearer {API_KEY}':
        log_access(endpoint, client_ip, user_agent, auth_header, "401_UNAUTHORIZED")
        # Return no response body to hide server existence
        return '', 401
    
    # Request allowed - log successful access
    log_access(endpoint, client_ip, user_agent, auth_header, "200_OK")
    return None

# =============================================================================
# Flask Application Middleware
# =============================================================================

@app.before_request
def before_request():
    """
    Apply security middleware to all incoming HTTP requests.
    
    This Flask hook runs before any route handler and implements:
    - IP whitelisting validation
    - Rate limiting per IP address  
    - API key authentication
    - Comprehensive access logging
    
    Exemptions:
        - /health endpoint bypasses security for monitoring systems
        - Additional paths can be added to exemption list as needed
        
    Returns:
        - None: Request is allowed to proceed to route handler
        - Response tuple: Request blocked with appropriate error code
        
    Security Flow:
        1. Check if path is exempted from security
        2. Apply IP whitelist, rate limiting, and auth checks
        3. Log all access attempts with detailed information
        4. Block or allow request based on security results
    """
    # Apply comprehensive security middleware to ALL endpoints
    # No exemptions - all endpoints require proper authentication
    security_result = security_middleware()
    if security_result:
        return security_result

# =============================================================================
# API Route Handlers
# =============================================================================

@app.route(f'{API_PATH}/keepalive', methods=['POST'])
def keepalive():
    """
    Main keepalive endpoint for receiving VPN client status updates.
    
    HTTP Method: POST
    Content-Type: application/json
    Authentication: Bearer token (if VPN_SENTINEL_API_KEY is configured)
    
    Request Payload:
        {
            "client_id": "unique-client-identifier",
            "timestamp": "2025-10-12T10:25:18+0200", 
            "public_ip": "89.40.181.202",
            "status": "alive",
            "location": {
                "country": "RO",
                "city": "Bucharest", 
                "region": "București",
                "org": "AS9009 M247 Europe SRL",
                "timezone": "Europe/Bucharest"
            },
            "dns_test": {
                "location": "RO",
                "colo": "OTP"
            }
        }
    
    Features:
        - Tracks client connection status and IP changes
        - Performs DNS leak detection by comparing VPN vs DNS locations  
        - Sends Telegram notifications for new connections and IP changes
        - Updates client registry with comprehensive location data
        - Provides detailed status information in notifications
        
    DNS Leak Detection Logic:
        - Compares location.country (VPN exit country) with dns_test.location
        - Reports potential leak if countries don't match
        - Handles unknown/missing data gracefully
        
    Telegram Notifications Sent For:
        - New client connections (first time seen)
        - IP address changes (VPN server switches)  
        - DNS leak detection results (secure vs leaked)
        
    Response:
        200 OK: {"status": "ok", "message": "Keepalive received", "server_time": "..."}
        400 Bad Request: Invalid JSON or missing required fields
        401 Unauthorized: Missing or invalid API key
        403 Forbidden: IP not whitelisted
        429 Too Many Requests: Rate limit exceeded
        
    Error Handling:
        - Gracefully handles missing or malformed data
        - Uses "Unknown" as fallback for missing location fields
        - Continues processing even if Telegram notifications fail
        - Logs all errors with timestamps for debugging
    """
    try:
        # Parse and validate incoming JSON payload
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
            
        client_id = data.get('client_id', 'unknown')
        # Use client_id for both identification and display purposes
        public_ip = data.get('public_ip', 'unknown')
        
        # Determine if this is a new connection or IP change event
        is_new_connection = client_id not in clients
        previous_ip = clients.get(client_id, {}).get('public_ip', None)
        ip_changed = previous_ip is not None and previous_ip != public_ip
        
        # Extract and validate location and DNS test data
        location = data.get('location', {})
        dns_test = data.get('dns_test', {})
        
        # Update client registry with comprehensive status information
        clients[client_id] = {
            'last_seen': get_current_time(),
            'client_name': client_id,  # Using client_id for display name
            'public_ip': public_ip,
            'status': 'alive',
            'location': {
                'country': location.get('country', 'Unknown'),
                'city': location.get('city', 'Unknown'),
                'region': location.get('region', 'Unknown'),
                'org': location.get('org', 'Unknown'),
                'timezone': location.get('timezone', 'Unknown')
            },
            'dns_test': {
                'location': dns_test.get('location', 'Unknown'),
                'colo': dns_test.get('colo', 'Unknown')
            }
        }
        
        if is_new_connection or ip_changed:
            
            country = location.get('country', 'Unknown')
            city = location.get('city', 'Unknown')
            region = location.get('region', 'Unknown')
            org = location.get('org', 'Unknown')
            vpn_timezone = location.get('timezone', 'Unknown')
            dns_location = dns_test.get('location', 'Unknown')
            dns_colo = dns_test.get('colo', 'Unknown')
            
            if is_new_connection:
                message = f"✅ <b>VPN Connected!</b>\n\n"
            else:
                message = f"🔄 <b>VPN IP Changed!</b>\n\nPrevious IP: <code>{previous_ip}</code>\n"
            
            message += f"Client: <code>{client_id}</code>\n"
            message += f"VPN IP: <code>{public_ip}</code>\n"
            message += f"📍 Location: <b>{city}, {region}, {country}</b>\n"
            message += f"🏢 Provider: <code>{org}</code>\n"
            message += f"🕒 VPN Timezone: <code>{vpn_timezone}</code>\n"
            message += f"Connected at: {get_current_time().strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
            message += f"🔒 <b>DNS Leak Test:</b>\n"
            message += f"DNS Location: <code>{dns_location}</code>\n"
            message += f"DNS Server: <code>{dns_colo}</code>\n"
            
            if dns_location != 'Unknown' and country != 'Unknown':
                if dns_location.upper() == country.upper():
                    message += f"✅ <b>No DNS leak detected</b>"
                else:
                    message += f"⚠️ <b>Possible DNS leak:</b> DNS in {dns_location}, VPN in {country}"
            else:
                message += f"❓ <b>DNS leak test inconclusive</b>"
            
            # =============================================================================
            # VPN Bypass Warning - Check if client and server have same IP
            # =============================================================================
            global server_public_ip
            if server_public_ip is None:
                server_public_ip = get_server_public_ip()
                log_info(f"Server public IP detected: {server_public_ip}")
            
            if public_ip != 'unknown' and server_public_ip != 'Unknown' and public_ip == server_public_ip:
                log_warn(f"⚠️ VPN BYPASS WARNING: Client {client_id} has same IP as server: {public_ip}")
                message += f"\n\n🚨 <b>VPN BYPASS WARNING!</b>\n"
                message += f"⚠️ Client IP matches server IP: <code>{public_ip}</code>\n"
                message += f"🔴 <b>Possible Issues:</b>\n"
                message += f"• VPN tunnel is not working properly\n"
                message += f"• Client and server are on the same network\n"
                message += f"• VPN client failed to establish connection\n"
                message += f"• DNS resolution bypassing VPN\n\n"
                message += f"🛠️ <b>Recommended Actions:</b>\n"
                message += f"• Check VPN container logs\n"
                message += f"• Verify VPN credentials and configuration\n"
                message += f"• Test VPN connection manually\n"
                message += f"• Ensure proper network isolation"
            
            send_telegram_message(message)
            announced_clients.add(client_id)
        
        log_info(f"Keepalive received from {client_id} - IP: {public_ip}")
        
        return jsonify({
            'status': 'ok',
            'message': 'Keepalive received',
            'server_time': get_current_time().isoformat()
        })
        
    except Exception as e:
        log_error(f"Error processing keepalive: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route(f'{API_PATH}/status', methods=['GET'])
def status():
    now = get_current_time()
    status_info = {}
    
    for client_id, info in clients.items():
        minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
        status_info[client_id] = {
            'last_seen': info['last_seen'].isoformat(),
            'minutes_ago': minutes_ago,
            'public_ip': info['public_ip'],
            'status': 'alive' if minutes_ago < ALERT_THRESHOLD_MINUTES else 'dead'
        }
    
    return jsonify(status_info)

@app.route(f'{API_PATH}/fake-heartbeat', methods=['POST'])
def fake_heartbeat():
    """Testing endpoint to simulate client heartbeats"""
    try:
        # Get data from request or use defaults for testing
        data = request.get_json() or {}
        
        client_id = data.get('client_id', f'test-client-{int(time.time())}')
        # Use client_id for both identification and display purposes
        public_ip = data.get('public_ip', '192.168.1.100')
        
        # Default test location data
        default_location = {
            'country': data.get('country', 'Spain'),
            'city': data.get('city', 'Madrid'),
            'region': data.get('region', 'Community of Madrid'),
            'org': data.get('org', 'Test VPN Provider'),
            'timezone': data.get('timezone', 'Europe/Madrid')
        }
        
        # Default test DNS data
        default_dns = {
            'location': data.get('dns_location', 'Spain'),
            'colo': data.get('dns_colo', 'MAD')
        }
        
        location = data.get('location', default_location)
        dns_test = data.get('dns_test', default_dns)
        
        # Simulate the same logic as real keepalive
        is_new_connection = client_id not in clients
        previous_ip = clients.get(client_id, {}).get('public_ip', None)
        ip_changed = previous_ip is not None and previous_ip != public_ip
        
        clients[client_id] = {
            'last_seen': get_current_time(),
            'client_name': client_id,  # Using client_id for display name
            'public_ip': public_ip,
            'status': 'alive',
            'location': {
                'country': location.get('country', 'Unknown'),
                'city': location.get('city', 'Unknown'),
                'region': location.get('region', 'Unknown'),
                'org': location.get('org', 'Unknown'),
                'timezone': location.get('timezone', 'Unknown')
            },
            'dns_test': {
                'location': dns_test.get('location', 'Unknown'),
                'colo': dns_test.get('colo', 'Unknown')
            }
        }
        
        if is_new_connection or ip_changed:
            country = location.get('country', 'Unknown')
            city = location.get('city', 'Unknown')
            region = location.get('region', 'Unknown')
            org = location.get('org', 'Unknown')
            vpn_timezone = location.get('timezone', 'Unknown')
            dns_location = dns_test.get('location', 'Unknown')
            dns_colo = dns_test.get('colo', 'Unknown')
            
            if is_new_connection:
                message = f"🧪 <b>TEST VPN Connected!</b>\n\n"
            else:
                message = f"🧪 <b>TEST VPN IP Changed!</b>\n\nPrevious IP: <code>{previous_ip}</code>\n"
            
            message += f"Client: <code>{client_id}</code>\n"
            message += f"VPN IP: <code>{public_ip}</code>\n"
            message += f"📍 Location: <b>{city}, {region}, {country}</b>\n"
            message += f"🏢 Provider: <code>{org}</code>\n"
            message += f"🕒 VPN Timezone: <code>{vpn_timezone}</code>\n"
            message += f"Connected at: {get_current_time().strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
            message += f"🔒 <b>DNS Leak Test:</b>\n"
            message += f"DNS Location: <code>{dns_location}</code>\n"
            message += f"DNS Server: <code>{dns_colo}</code>\n"
            
            if dns_location != 'Unknown' and country != 'Unknown':
                if dns_location.upper() == country.upper():
                    message += f"✅ <b>No DNS leak detected</b>"
                else:
                    message += f"⚠️ <b>Possible DNS leak:</b> DNS in {dns_location}, VPN in {country}"
            else:
                message += f"❓ <b>DNS leak test inconclusive</b>"
            
            # VPN Bypass Warning for test endpoint
            global server_public_ip
            if server_public_ip is None:
                server_public_ip = get_server_public_ip()
                log_info(f"Server public IP detected: {server_public_ip}")
            
            if public_ip != 'unknown' and server_public_ip != 'Unknown' and public_ip == server_public_ip:
                log_warn(f"⚠️ TEST VPN BYPASS WARNING: Client {client_id} has same IP as server: {public_ip}")
                message += f"\n\n🚨 <b>TEST VPN BYPASS WARNING!</b>\n"
                message += f"⚠️ Client IP matches server IP: <code>{public_ip}</code>\n"
                message += f"🔴 This indicates VPN is not working properly!"
            
            message += f"\n\n<i>This was a test heartbeat via /fake-heartbeat endpoint</i>"
            
            send_telegram_message(message)
            announced_clients.add(client_id)
        
        log_info(f"FAKE heartbeat received from {client_id} - IP: {public_ip}")
        
        return jsonify({
            'status': 'ok',
            'message': 'Fake heartbeat processed',
            'client_id': client_id,
            'public_ip': public_ip,
            'is_new_connection': is_new_connection,
            'ip_changed': ip_changed,
            'server_time': get_current_time().isoformat()
        })
        
    except Exception as e:
        log_error(f"Error processing fake heartbeat: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route(f'{API_PATH}/health', methods=['GET'])
def health():
    """Health check endpoint - requires API key authentication like all other endpoints"""
    return jsonify({
        'status': 'healthy',
        'server_time': get_current_time().isoformat(),
        'active_clients': len(clients),
        'uptime_info': 'VPN Keepalive Server is running'
    })

def check_clients():
    global no_clients_alert_sent
    alerted_clients = set()
    
    while True:
        try:
            now = get_current_time()
            
            if len(clients) == 0:
                log_info("🔍 Monitoring check: No clients registered")
                
                # Send Telegram alert for no clients (only once)
                if not no_clients_alert_sent:
                    message = f"⚠️ <b>No VPN Clients Connected</b>\n\n"
                    message += f"No active VPN connections detected.\n"
                    message += f"Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
                    message += f"💡 This alert will not repeat until a client connects and disconnects again."
                    
                    if send_telegram_message(message):
                        log_info("📤 No clients alert sent to Telegram")
                        no_clients_alert_sent = True
                    else:
                        log_error("❌ Failed to send no clients alert")
            else:
                log_info(f"🔍 Monitoring check: {len(clients)} client(s) registered")
                
                # Reset the no_clients_alert flag when we have clients again
                if no_clients_alert_sent:
                    no_clients_alert_sent = False
                    log_info("🔄 Reset no-clients alert flag (clients are back)")
                
                for client_id, info in clients.items():
                    minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
                    status = '🟢 Online' if minutes_ago < ALERT_THRESHOLD_MINUTES else '🔴 Offline'
                    log_info(f"   └── {client_id}: {status} (last seen {minutes_ago}m ago)")
            
            for client_id, info in clients.items():
                minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
                
                if minutes_ago >= ALERT_THRESHOLD_MINUTES:
                    if client_id not in alerted_clients:
                        log_warn(f"⚠️ Client {client_id} exceeded threshold ({minutes_ago}m > {ALERT_THRESHOLD_MINUTES}m) - sending alert")
                        
                        # Get stored location and DNS data
                        client_location = info.get('location', {})
                        client_dns = info.get('dns_test', {})
                        
                        country = client_location.get('country', 'Unknown')
                        city = client_location.get('city', 'Unknown')
                        region = client_location.get('region', 'Unknown')
                        org = client_location.get('org', 'Unknown')
                        vpn_timezone = client_location.get('timezone', 'Unknown')
                        dns_location = client_dns.get('location', 'Unknown')
                        dns_colo = client_dns.get('colo', 'Unknown')
                        
                        # Use client_id for display name
                        
                        message = f"❌ <b>VPN Connection Lost!</b>\n\n"
                        message += f"Client: <code>{client_id}</code>\n"
                        message += f"Last IP: <code>{info['public_ip']}</code>\n"
                        message += f"📍 Last Location: <b>{city}, {region}, {country}</b>\n"
                        message += f"🏢 Provider: <code>{org}</code>\n"
                        message += f"🕒 VPN Timezone: <code>{vpn_timezone}</code>\n"
                        message += f"⏰ Last seen: {minutes_ago} minutes ago\n"
                        message += f"🕐 Last contact: {info['last_seen'].strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                        message += f"⚠️ Lost at: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
                        message += f"🔒 <b>Last DNS Status:</b>\n"
                        message += f"DNS Location: <code>{dns_location}</code>\n"
                        message += f"DNS Server: <code>{dns_colo}</code>\n"
                        
                        if dns_location != 'Unknown' and country != 'Unknown':
                            if dns_location.upper() == country.upper():
                                message += f"✅ <b>No DNS leak was detected</b>"
                            else:
                                message += f"⚠️ <b>DNS leak was detected:</b> DNS in {dns_location}, VPN in {country}"
                        else:
                            message += f"❓ <b>DNS leak status was inconclusive</b>"
                        
                        if send_telegram_message(message):
                            log_info(f"✅ Failure alert sent for {client_id}")
                            alerted_clients.add(client_id)
                            announced_clients.discard(client_id)
                        else:
                            log_error(f"❌ Failed to send failure alert for {client_id}")
                    else:
                        log_info(f"   └── {client_id} still offline ({minutes_ago}m) - alert already sent")
                else:
                    alerted_clients.discard(client_id)
            
        except Exception as e:
            log_error(f"Error in check_clients: {e}")
        
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

def handle_telegram_commands():
    """Poll Telegram for incoming commands"""
    if not TELEGRAM_BOT_TOKEN:
        return
    
    last_update_id = 0
    
    while True:
        try:
            # Get updates from Telegram
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                data = response.json()
                
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message.get("text", "")
                        
                        # Only respond to messages from the configured chat
                        if str(chat_id) != TELEGRAM_CHAT_ID:
                            continue
                        
                        log_info(f"📥 Telegram command received: {text}")
                        
                        # Handle commands
                        if text.startswith('/ping'):
                            handle_ping_command()
                        elif text.startswith('/status'):
                            handle_status_command()
                        elif text.startswith('/help'):
                            handle_help_command()
                        else:
                            # Handle unknown commands and regular text
                            handle_unknown_command(text)
            
        except Exception as e:
            log_error(f"❌ Telegram polling error: {e}")
            time.sleep(10)  # Wait before retrying

def handle_ping_command():
    """Handle /ping command"""
    now = get_current_time()
    
    message = f"🏓 <b>Pong!</b>\n\n"
    message += f"Server time: <code>{now.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>\n"
    message += f"Active clients: <code>{len(clients)}</code>\n"
    message += f"Alert threshold: <code>{ALERT_THRESHOLD_MINUTES} minutes</code>\n"
    message += f"Check interval: <code>{CHECK_INTERVAL_MINUTES} minutes</code>"
    
    if send_telegram_message(message):
        log_info("✅ Pong response sent")

def handle_status_command():
    """Handle /status command"""
    now = get_current_time()
    
    if len(clients) == 0:
        message = f"📊 <b>VPN Status</b>\n\n"
        message += f"❌ No VPN clients connected\n\n"
        message += f"Server time: <code>{now.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>"
    else:
        message = f"📊 <b>VPN Status</b>\n\n"
        for client_id, info in clients.items():
            minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
            
            if minutes_ago < ALERT_THRESHOLD_MINUTES:
                status_icon = "🟢"
                status_text = "Online"
            else:
                status_icon = "🔴"
                status_text = "Offline"
            
            message += f"{status_icon} <b>{client_id}</b> - {status_text}\n"
            message += f"   IP: <code>{info['public_ip']}</code>\n"
            message += f"   Last seen: <code>{minutes_ago} minutes ago</code>\n"
            message += f"   Time: <code>{info['last_seen'].strftime('%H:%M:%S %Z')}</code>\n\n"
        
        message += f"Server time: <code>{now.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>"
    
    if send_telegram_message(message):
        log_info("✅ Status response sent")

def handle_help_command():
    """Handle /help command"""
    message = f"❓ <b>VPN Keepalive Bot Help</b>\n\n"
    message += f"Available commands:\n"
    message += f"🏓 <code>/ping</code> - Test bot connectivity and get server info\n"
    message += f"📊 <code>/status</code> - Get detailed VPN client status\n"
    message += f"❓ <code>/help</code> - Show this help message\n\n"
    message += f"<b>Automatic notifications:</b>\n"
    message += f"✅ VPN connection established\n"
    message += f"🔄 VPN IP address changes\n"
    message += f"❌ VPN connection lost (after {ALERT_THRESHOLD_MINUTES} minutes)\n"
    message += f"🔒 DNS leak test results\n\n"
    message += f"Monitoring every <code>{CHECK_INTERVAL_MINUTES} minutes</code>"
    
    if send_telegram_message(message):
        log_info("✅ Help response sent")

def handle_unknown_command(text):
    """Handle unknown commands and regular text messages"""
    message = f"👋 <b>Hello!</b> I'm your VPN monitoring bot.\n\n"
    message += f"I received: <code>{text}</code>\n\n"
    message += f"Use <code>/help</code> to see available commands.\n\n"
    message += f"Available commands:\n"
    message += f"🏓 <code>/ping</code> - Test connectivity\n"
    message += f"📊 <code>/status</code> - Get VPN status\n"
    message += f"❓ <code>/help</code> - Show help"
    
    if send_telegram_message(message):
        log_info(f"✅ Unknown command response sent for: {text}")

if __name__ == '__main__':
    server_start_time = get_current_time()
    
    # SECURITY: Require API key for server to start
    if not API_KEY:
        log_error("❌ SECURITY ERROR: VPN_SENTINEL_API_KEY environment variable is required!")
        log_error("The server will not start without proper API key configuration.")
        log_error("Set VPN_SENTINEL_API_KEY in your .env file or environment variables.")
        exit(1)
    
    log_info("🚀 Starting VPN Sentinel Server...")
    log_info(f"API path: {API_PATH}")
    log_info(f"Alert threshold: {ALERT_THRESHOLD_MINUTES} minutes")
    log_info(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    log_info(f"Rate limiting: {RATE_LIMIT_REQUESTS} req/min")
    log_info(f"API key auth: {'Enabled' if API_KEY else 'Disabled'}")
    log_info(f"IP whitelist: {'Enabled' if ALLOWED_IPS and ALLOWED_IPS != [''] else 'Disabled'}")
    
    startup_message = f"🚀 <b>VPN Keepalive Server Started</b>\n\n"
    startup_message += f"Server is now monitoring VPN connections.\n"
    startup_message += f"Alert threshold: {ALERT_THRESHOLD_MINUTES} minutes\n"
    startup_message += f"Check interval: {CHECK_INTERVAL_MINUTES} minutes\n"
    startup_message += f"🛡️ Security: Rate limiting ({RATE_LIMIT_REQUESTS} req/min)\n"
    startup_message += f"🔐 API Auth: Required and Enabled\n"
    startup_message += f"Started at: {server_start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
    startup_message += f"💡 Send /ping to test the connection!\n"
    startup_message += f"📊 Send /status for detailed VPN status\n"
    startup_message += f"❓ Send /help for all commands"
    
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        if send_telegram_message(startup_message):
            log_info("Startup notification sent successfully")
        else:
            log_warn("Failed to send startup notification")
    
    checker_thread = threading.Thread(target=check_clients, daemon=True)
    checker_thread.start()
    
    # Start Telegram bot polling thread
    telegram_thread = threading.Thread(target=handle_telegram_commands, daemon=True)
    telegram_thread.start()
    log_info("Telegram bot polling started")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
