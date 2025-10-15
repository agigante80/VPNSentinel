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
- Interactive web dashboard for client monitoring
- Interactive Telegram commands (/ping, /status, /help)

Architecture:
- Flask web server for HTTP API endpoints
- Threading for concurrent client monitoring
- In-memory storage for client status (production: consider Redis/DB)
- Telegram Bot API integration for notifications
- Security features: rate limiting, IP whitelisting, API key auth

Environment Variables:
- TELEGRAM_BOT_TOKEN: Telegram bot token for notifications (optional)
- TELEGRAM_CHAT_ID: Target chat ID for notifications (optional)
- VPN_SENTINEL_API_KEY: API key for client authentication (required)
- VPN_SENTINEL_SERVER_ALLOWED_IPS: Comma-separated IP whitelist (optional)
- API_PATH: API path prefix for endpoints (default: /api/v1)
- TZ: Timezone for timestamps (default: UTC)
- VPN_SENTINEL_SERVER_RATE_LIMIT_REQUESTS: Rate limit per IP (default: 30)

API Endpoints:
- POST {API_PATH}/keepalive: Receive client status updates
- GET {API_PATH}/status: Get server and client status
- POST {API_PATH}/fake-heartbeat: Simulate keepalive for testing
- GET {API_PATH}/health: Health check endpoint

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
        -e VPN_SENTINEL_API_KEY=your_api_key \
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
from flask import Flask, request, jsonify, render_template_string # Web framework and HTTP utilities
from collections import defaultdict, deque # Data structures for rate limiting
import requests          # HTTP client for Telegram API communication
import pytz             # Timezone handling for accurate timestamps

# =============================================================================
# Application Configuration and Constants
# =============================================================================

# Initialize Flask applications
api_app = Flask(__name__)               # API server application
dashboard_app = Flask(__name__)         # Dashboard web application

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
ALERT_THRESHOLD_MINUTES = int(os.getenv("VPN_SENTINEL_SERVER_ALERT_THRESHOLD_MINUTES", "15"))    # Minutes before considering a client offline
CHECK_INTERVAL_MINUTES = int(os.getenv("VPN_SENTINEL_SERVER_CHECK_INTERVAL_MINUTES", "5"))      # How often to check client status (background thread)

# Server Port Configuration  
API_PORT = int(os.getenv("VPN_SENTINEL_SERVER_API_PORT", "5000"))                               # API server port for client connections
DASHBOARD_PORT = int(os.getenv("VPN_SENTINEL_SERVER_DASHBOARD_PORT", "8080"))                   # Web dashboard port

# Web Dashboard Configuration
WEB_DASHBOARD_ENABLED = os.getenv("VPN_SENTINEL_SERVER_DASHBOARD_ENABLED", "true").lower() == "true"  # Enable/disable web dashboard

# Timezone Configuration
# Ensures consistent timestamp formatting across different deployment environments
TIMEZONE = pytz.timezone(os.getenv("TZ", "UTC"))

# TLS/SSL Configuration
TLS_CERT_PATH = os.getenv("VPN_SENTINEL_TLS_CERT_PATH")
TLS_KEY_PATH = os.getenv("VPN_SENTINEL_TLS_KEY_PATH")

# =============================================================================
# Global State Management
# =============================================================================

# Client Status Storage
# Dictionary storing active client information and status
# Key: client_id, Value: dict with client details
clients = {}                    # Dict[str, Dict]: Active client information and status

# Announced Clients Set
# Tracks clients that have already been announced to prevent spam notifications
announced_clients = set()       # Set[str]: Clients that have been announced

# Alert Flag
# Prevents repeated "no clients" notifications when no clients are connected
no_clients_alert_sent = False   # Bool: Flag to prevent repeated alerts

# Rate Limiting Storage
# Maps IP addresses to deque of recent request timestamps for sliding window rate limiting
rate_limit_storage = defaultdict(deque)  # Dict[str, deque]: IP -> request timestamps

# Server IP Cache
# Cached server public IP to avoid repeated API calls and enable VPN bypass detection
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

def log_message(level, component, message):
    """
    Log a message with structured format: timestamp level [component] message
    
    Args:
        level (str): Log level (INFO, ERROR, WARN)
        component (str): Component name (server, api, security, telegram, monitor, config)
        message (str): Message to log
    """
    timestamp = datetime.now(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"{timestamp} {level} [{component}] {message}", flush=True)

def log_info(component, message):
    """Log an info message with component tag"""
    log_message("INFO", component, message)

def log_error(component, message):
    """Log an error message with component tag"""
    log_message("ERROR", component, message)

def log_warn(component, message):
    """Log a warning message with component tag"""
    log_message("WARN", component, message)

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
        response = requests.get('https://ipinfo.io/json', timeout=10, verify=True)
        if response.status_code == 200:
            data = response.json()
            return data.get('ip', 'Unknown')
    except Exception:
        pass

    # Fallback to alternative service
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10, verify=True)
        if response.status_code == 200:
            data = response.json()
            return data.get('ip', 'Unknown')
    except Exception:
        pass

    return 'Unknown'

def get_server_info():
    """
    Get comprehensive server information including location, provider, and DNS status.
    
    Returns:
        dict: Server information with IP, location, provider, and DNS details
        
    Note:
        Uses ipinfo.io to get detailed server information for dashboard display.
        Caches key information to avoid repeated API calls during server operation.
    """
    server_info = {
        'public_ip': 'Unknown',
        'location': 'Unknown',
        'provider': 'Unknown', 
        'dns_status': 'Unknown'
    }
    
    try:
        # Get detailed server information from ipinfo.io
        response = requests.get('https://ipinfo.io/json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Extract server information
            server_info['public_ip'] = data.get('ip', 'Unknown')
            
            # Format location information
            city = data.get('city', '')
            region = data.get('region', '')
            country = data.get('country', 'Unknown')
            
            if city and region:
                server_info['location'] = f"{city}, {region}, {country}"
            elif city:
                server_info['location'] = f"{city}, {country}"
            else:
                server_info['location'] = country
            
            # Provider information
            server_info['provider'] = data.get('org', 'Unknown Provider')
            
            # DNS status - check if we can resolve DNS properly
            try:
                import socket
                socket.gethostbyname('google.com')
                server_info['dns_status'] = 'Operational'
            except Exception:
                server_info['dns_status'] = 'Issues Detected'
                
    except Exception as e:
        log_error("server_info", f"Failed to get server information: {str(e)}")
    
    return server_info

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
        response = requests.post(url, json=data, timeout=10, verify=True)
        success = response.status_code == 200

        # Log operation result with structured format
        if success:
            log_info("telegram", "✅ Message sent successfully")
        else:
            log_error("telegram", f"❌ Failed to send message: HTTP {response.status_code}")

        return success
    except Exception as e:
        # Handle network errors, timeouts, and other exceptions
        log_error("telegram", f"❌ Error: {e}")
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

def validate_client_id(client_id):
    """
    Validate and sanitize client_id input.
    
    Args:
        client_id: Raw client identifier from request
        
    Returns:
        str: Sanitized client_id or 'unknown' if invalid
        
    Validation Rules:
        - Must be string type
        - Maximum 100 characters
        - Only alphanumeric, hyphens, underscores, and dots allowed
        - No leading/trailing whitespace
    """
    if not isinstance(client_id, str):
        return 'unknown'
    
    # Remove leading/trailing whitespace
    client_id = client_id.strip()
    
    # Check length
    if len(client_id) > 100 or len(client_id) == 0:
        return 'unknown'
    
    # Check allowed characters (alphanumeric, hyphens, underscores, dots)
    import re
    if not re.match(r'^[a-zA-Z0-9._-]+$', client_id):
        return 'unknown'
    
    return client_id

def validate_public_ip(public_ip):
    """
    Validate public IP address format.
    
    Args:
        public_ip: Raw IP address string from request
        
    Returns:
        str: Validated IP address or 'unknown' if invalid
        
    Validation Rules:
        - Must be valid IPv4 or IPv6 address format
        - No leading/trailing whitespace
        - Maximum 45 characters (IPv6 with brackets)
    """
    if not isinstance(public_ip, str):
        return 'unknown'
    
    # Remove leading/trailing whitespace
    public_ip = public_ip.strip()
    
    # Check length
    if len(public_ip) > 45 or len(public_ip) == 0:
        return 'unknown'
    
    # Basic IP validation using socket
    import socket
    try:
        socket.inet_pton(socket.AF_INET, public_ip)
        return public_ip  # Valid IPv4
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, public_ip)
            return public_ip  # Valid IPv6
        except socket.error:
            return 'unknown'  # Invalid IP

def validate_location_string(value, field_name):
    """
    Validate and sanitize location string fields.
    
    Args:
        value: Raw string value from location data
        field_name: Name of the field for logging
        
    Returns:
        str: Sanitized string or 'Unknown' if invalid
        
    Validation Rules:
        - Must be string type
        - Maximum 100 characters
        - Basic sanitization (remove dangerous characters)
        - No leading/trailing whitespace
    """
    if not isinstance(value, str):
        return 'Unknown'
    
    # Remove leading/trailing whitespace
    value = value.strip()
    
    # Check length
    if len(value) > 100:
        return 'Unknown'
    
    # Basic sanitization - remove potentially dangerous characters
    # Allow only printable ASCII characters, spaces, and basic punctuation
    import re
    if not re.match(r'^[a-zA-Z0-9\s.,\'"-]+$', value):
        log_warn("security", f"Potentially dangerous characters in {field_name}: {value}")
        return 'Unknown'
    
    return value

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
        - Periodically cleans up IPs with no recent activity
    """
    now = time.time()
    
    # Periodic cleanup: remove IPs that haven't been active in the last window
    # This prevents memory leaks from accumulating old IP entries
    global last_cleanup_time
    if now - getattr(check_rate_limit, 'last_cleanup_time', 0) > RATE_LIMIT_WINDOW:
        check_rate_limit.last_cleanup_time = now
        # Remove IPs that have no timestamps or all timestamps are expired
        expired_ips = [ip for ip, timestamps in rate_limit_storage.items() 
                      if not timestamps or all(ts < now - RATE_LIMIT_WINDOW for ts in timestamps)]
        for expired_ip in expired_ips:
            del rate_limit_storage[expired_ip]
    
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
    log_info("api", f"🌐 Access: {endpoint} | IP: {ip} | Auth: {auth_info} | Status: {status} | UA: {user_agent[:50]}...")

def security_middleware():
    """
    Apply comprehensive security checks to incoming requests.
    
    Performs three layers of security validation:
    1. IP Whitelist Validation - Block non-whitelisted IPs
    2. Rate Limiting - Prevent abuse via request frequency limits  
    3. API Key Authentication - Verify Bearer token in Authorization header
    
    Returns:
        tuple: (error_response, status_code) if request blocked, None if allowed
        
    Response Codes:
        - 403: IP address not in whitelist
        - 429: Rate limit exceeded
        - 401: Missing or invalid API key
        - 500: Server configuration error (API key not set)
        
    Security Notes:
        - All blocked requests are logged with full details
        - API key is required for server operation (returns 500 if not configured)
        - Rate limiting uses sliding window algorithm
        - IP whitelist is optional (allows all if not configured)
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
    
    # API Key Authentication Check (OPTIONAL for server operation)
    # Only enforce authentication if API key is explicitly configured
    if API_KEY:
        # API key is configured - require authentication
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

@api_app.before_request
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
        - /dashboard endpoint bypasses security when web dashboard is enabled
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
    # Exempt public endpoints from authentication
    if request.path == f'{API_PATH}/health':
        return None  # Health check endpoint for monitoring systems
    
    if request.path == '/dashboard' and WEB_DASHBOARD_ENABLED:
        return None  # Web dashboard endpoint (public access when enabled)
        
    # Apply comprehensive security middleware to all other endpoints
    security_result = security_middleware()
    if security_result:
        return security_result

# =============================================================================
# API Route Handlers
# =============================================================================

@api_app.route(f'{API_PATH}/keepalive', methods=['POST'])
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
            
        # Validate and sanitize client_id
        client_id = validate_client_id(data.get('client_id', 'unknown'))
        
        # Validate and sanitize public_ip
        public_ip = validate_public_ip(data.get('public_ip', 'unknown'))
        
        # Determine if this is a new connection or IP change event
        is_new_connection = client_id not in clients
        previous_ip = clients.get(client_id, {}).get('public_ip', None)
        ip_changed = previous_ip is not None and previous_ip != public_ip
        
        # Extract and validate location and DNS test data
        location = data.get('location', {})
        dns_test = data.get('dns_test', {})
        
        # Validate location fields
        country = validate_location_string(location.get('country', 'Unknown'), 'country')
        city = validate_location_string(location.get('city', 'Unknown'), 'city')
        region = validate_location_string(location.get('region', 'Unknown'), 'region')
        org = validate_location_string(location.get('org', 'Unknown'), 'org')
        timezone = validate_location_string(location.get('timezone', 'Unknown'), 'timezone')
        
        # Validate DNS test fields
        dns_location = validate_location_string(dns_test.get('location', 'Unknown'), 'dns_location')
        dns_colo = validate_location_string(dns_test.get('colo', 'Unknown'), 'dns_colo')
        
        # Update client registry with comprehensive status information
        clients[client_id] = {
            'last_seen': get_current_time(),
            'client_name': client_id,  # Using client_id for display name
            'public_ip': public_ip,
            'status': 'alive',
            'location': {
                'country': country,
                'city': city,
                'region': region,
                'org': org,
                'timezone': timezone
            },
            'dns_test': {
                'location': dns_location,
                'colo': dns_colo
            }
        }
        
        if is_new_connection or ip_changed:
            
            # Use the already validated location data
            # country, city, region, org, timezone, dns_location, dns_colo are already validated
            
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
                log_info("config", f"Server public IP detected: {server_public_ip}")
            
            if public_ip != 'unknown' and server_public_ip != 'Unknown' and public_ip == server_public_ip:
                log_warn("security", f"⚠️ VPN BYPASS WARNING: Client {client_id} has same IP as server: {public_ip}")
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
            
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                send_telegram_message(message)
            announced_clients.add(client_id)
        
        log_info("api", f"Keepalive received from {client_id} - IP: {public_ip}")
        
        return jsonify({
            'status': 'ok',
            'message': 'Keepalive received',
            'server_time': get_current_time().isoformat()
        })
        
    except Exception as e:
        log_error("api", f"Error processing keepalive: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@api_app.route(f'{API_PATH}/status', methods=['GET'])
def status():
    """
    Get comprehensive status information for all registered VPN clients.
    
    HTTP Method: GET
    Authentication: Bearer token (if VPN_SENTINEL_API_KEY is configured)
    
    Returns:
        dict: Status information for each client containing:
            - last_seen: ISO timestamp of last keepalive
            - minutes_ago: Minutes since last contact
            - public_ip: Client's current public IP
            - status: 'alive' or 'dead' based on ALERT_THRESHOLD_MINUTES
            
    Response Format:
        {
            "client-1": {
                "last_seen": "2025-10-14T19:30:45+00:00",
                "minutes_ago": 2,
                "public_ip": "89.40.181.202", 
                "status": "alive"
            }
        }
        
    Status Logic:
        - 'alive': Client contacted within ALERT_THRESHOLD_MINUTES (default: 15)
        - 'dead': Client hasn't contacted beyond threshold
        
    Use Cases:
        - Monitoring dashboards
        - Health check systems
        - Administrative status queries
    """
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

@api_app.route(f'{API_PATH}/fake-heartbeat', methods=['POST'])
def fake_heartbeat():
    """
    Testing endpoint to simulate client heartbeats without real VPN clients.
    
    HTTP Method: POST
    Content-Type: application/json
    Authentication: Bearer token (if VPN_SENTINEL_API_KEY is configured)
    
    This endpoint mimics the behavior of /keepalive but:
    - Uses "TEST" prefixes in Telegram notifications
    - Provides default test data if fields are missing
    - Includes additional response fields for testing
    - Helps validate server logic without real VPN clients
    
    Request Payload (all fields optional with defaults):
        {
            "client_id": "test-client-123",
            "public_ip": "192.168.1.100",
            "country": "Spain",
            "city": "Madrid",
            "org": "Test VPN Provider",
            "dns_location": "Spain",
            "dns_colo": "MAD"
        }
        
    Response includes testing metadata:
        - is_new_connection: Whether this created a new client entry
        - ip_changed: Whether the IP changed from previous value
        
    Use Cases:
        - Development and testing
        - CI/CD pipeline validation
        - Server functionality verification
    """
    try:
        # Get data from request or use defaults for testing
        data = request.get_json() or {}
        
        client_id = data.get('client_id', f'test-client-{int(time.time())}')
        # Use client_id for both identification and display purposes
        public_ip = data.get('public_ip', '192.168.1.100')
        
        # Sanitize and validate inputs
        client_id = validate_client_id(client_id)
        public_ip = validate_public_ip(public_ip)
        
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
            # Use the already validated location data
            # country, city, region, org, timezone, dns_location, dns_colo are already validated
            
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
                log_info("config", f"Server public IP detected: {server_public_ip}")
            
            if public_ip != 'unknown' and server_public_ip != 'Unknown' and public_ip == server_public_ip:
                log_warn("security", f"⚠️ TEST VPN BYPASS WARNING: Client {client_id} has same IP as server: {public_ip}")
                message += f"\n\n🚨 <b>TEST VPN BYPASS WARNING!</b>\n"
                message += f"⚠️ Client IP matches server IP: <code>{public_ip}</code>\n"
                message += f"🔴 This indicates VPN is not working properly!"
            
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                send_telegram_message(message)
            announced_clients.add(client_id)
        
        log_info("api", f"FAKE heartbeat received from {client_id} - IP: {public_ip}")
        
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
        log_error("api", f"Error processing fake heartbeat: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@api_app.route(f'{API_PATH}/health', methods=['GET'])
def health():
    """Health check endpoint - public endpoint for monitoring systems (no authentication required)"""
    # Log health check access (this endpoint bypasses authentication)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    log_access('health', client_ip, user_agent, None, "200_OK")
    
    return jsonify({
        'status': 'healthy',
        'server_time': get_current_time().isoformat(),
        'active_clients': len(clients),
        'uptime_info': 'VPN Keepalive Server is running'
    })

# =============================================================================
# Web Dashboard - Client Status Viewer
# =============================================================================

# HTML template for the web dashboard
DASHBOARD_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Sentinel Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
            position: relative;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .header .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .server-info {
            position: absolute;
            top: 20px;
            right: 30px;
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            font-size: 0.9em;
            text-align: right;
            backdrop-filter: blur(10px);
        }
        
        .server-info h4 {
            margin: 0 0 8px 0;
            font-size: 1em;
            opacity: 0.9;
        }
        
        .server-info .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            min-width: 250px;
        }
        
        .server-info .info-label {
            opacity: 0.8;
        }
        
        .server-info .info-value {
            font-weight: bold;
            color: #ecf0f1;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.2);
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            display: block;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        
        .content {
            padding: 30px;
        }
        
        .refresh-info {
            text-align: center;
            margin-bottom: 25px;
            color: #666;
            font-size: 0.95em;
        }
        
        .auto-refresh {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .table-container {
            overflow-x: auto;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            min-width: 800px;
        }
        
        thead {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
        }
        
        th, td {
            padding: 15px 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        th {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }
        
        tbody tr:hover {
            background: #f8f9fa;
            transform: translateY(-1px);
            transition: all 0.2s ease;
        }
        
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .status-online {
            background: #2ecc71;
            color: white;
        }
        
        .status-offline {
            background: #e74c3c;
            color: white;
        }
        
        .status-warning {
            background: #f39c12;
            color: white;
        }
        
        .ip-address {
            font-family: 'Courier New', monospace;
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
        }
        
        .location {
            font-size: 0.9em;
            color: #666;
        }
        
        .time-info {
            font-size: 0.85em;
            color: #888;
        }
        
        .no-clients {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        
        .no-clients-icon {
            font-size: 4em;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #eee;
        }
        
        @media (max-width: 768px) {
            .header {
                padding: 20px 15px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .stats {
                gap: 15px;
            }
            
            .stat-card {
                padding: 10px 15px;
            }
            
            .content {
                padding: 20px 15px;
            }
            
            .server-info {
                position: static;
                margin: 0 auto 20px auto;
                max-width: 300px;
                right: auto;
                top: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="server-info">
                <h4>🖥️ Server Details</h4>
                <div class="info-row">
                    <span class="info-label">Public IP:</span>
                    <span class="info-value">{{ server_info.public_ip }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Location:</span>
                    <span class="info-value">{{ server_info.location }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Provider:</span>
                    <span class="info-value">{{ server_info.provider }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">DNS Status:</span>
                    <span class="info-value">{{ server_info.dns_status }}</span>
                </div>
            </div>
            
            <h1>🔒 VPN Sentinel Dashboard</h1>
            <div class="subtitle">Real-time VPN Client Monitoring</div>
            <div class="stats">
                <div class="stat-card">
                    <span class="stat-number">{{ total_clients }}</span>
                    <span class="stat-label">Total Clients</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{{ online_clients }}</span>
                    <span class="stat-label">Online</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{{ offline_clients }}</span>
                    <span class="stat-label">Offline</span>
                </div>
            </div>
        </div>
        
        <div class="content">
            <div class="refresh-info">
                <span class="auto-refresh">🔄 Auto-refresh: 30s</span> | Last updated: {{ current_time }}
            </div>
            
            {% if clients %}
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Client ID</th>
                            <th>Status</th>
                            <th>Public IP</th>
                            <th>Location</th>
                            <th>Provider</th>
                            <th>DNS Status</th>
                            <th>Last Seen</th>
                            <th>Last Contact</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for client in clients %}
                        <tr>
                            <td><strong>{{ client.id }}</strong></td>
                            <td>
                                <span class="status-badge {{ client.status_class }}">
                                    {{ client.status_icon }} {{ client.status_text }}
                                </span>
                            </td>
                            <td><code class="ip-address">{{ client.public_ip }}</code></td>
                            <td class="location">
                                🌍 {{ client.location_display }}<br>
                                <small>🕒 {{ client.timezone }}</small>
                            </td>
                            <td>{{ client.provider }}</td>
                            <td>
                                {{ client.dns_status_icon }} {{ client.dns_location }}<br>
                                <small>{{ client.dns_server }}</small>
                            </td>
                            <td class="time-info">
                                <strong>{{ client.minutes_ago }}m ago</strong><br>
                                <small>{{ client.last_seen_relative }}</small>
                            </td>
                            <td class="time-info">{{ client.last_seen_formatted }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="no-clients">
                <div class="no-clients-icon">🔌</div>
                <h3>No VPN Clients Connected</h3>
                <p>Waiting for VPN clients to connect and report their status...</p>
            </div>
            {% endif %}
        </div>
        
        <div class="footer">
            <p>VPN Sentinel Server | Server Time: {{ server_time }} | Dashboard Port: {{ dashboard_port }}</p>
        </div>
    </div>
    
    <script>
        // Auto-refresh the page every 30 seconds
        setTimeout(function() {
            window.location.reload();
        }, 30000);
        
        // Add real-time clock
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleString();
            // Update any existing clock elements
        }
        setInterval(updateClock, 1000);
    </script>
</body>
</html>
'''

@dashboard_app.route('/dashboard', methods=['GET'])
def web_dashboard():
    """
    Render the web-based dashboard showing VPN client status and server information.
    
    HTTP Method: GET
    Authentication: None (public access when dashboard is enabled)
    
    Features:
        - Real-time client status display with online/offline indicators
        - Detailed client information (IP, location, provider, DNS status)
        - Server information and configuration display
        - Responsive HTML table layout with modern styling
        - Automatic refresh capability (client-side)
        
    Dashboard Content:
        - Client status table with connection details
        - Online/offline counts and statistics
        - Server location and network information
        - Last seen timestamps and connection status
        - DNS leak detection results
        
    Security:
        - Public access (no authentication required)
        - Can be disabled via WEB_DASHBOARD_ENABLED setting
        - Access is logged for monitoring purposes
        
    Response:
        - HTML page with embedded CSS and JavaScript
        - 404 error if dashboard is disabled
        - Includes comprehensive client and server data
    """
    if not WEB_DASHBOARD_ENABLED:
        return jsonify({
            'error': 'Web dashboard is disabled',
            'message': 'Set VPN_SENTINEL_SERVER_DASHBOARD_ENABLED=true to enable'
        }), 404
    
    # Log dashboard access
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    log_info("dashboard", f"🌐 Dashboard access from {client_ip} | UA: {user_agent[:50]}...")
    
    now = get_current_time()
    client_data = []
    online_count = 0
    offline_count = 0
    
    # Get server information for dashboard display
    server_info = get_server_info()
    
    # Get server IP for same-IP detection
    global server_public_ip
    if server_public_ip is None:
        server_public_ip = get_server_public_ip()
    
    for client_id, info in clients.items():
        minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
        client_ip = info['public_ip']
        
        # Determine status with same-IP warning logic
        if minutes_ago < ALERT_THRESHOLD_MINUTES:
            # Check if client is using same IP as server (VPN not active)
            if client_ip != 'unknown' and server_public_ip != 'Unknown' and client_ip == server_public_ip:
                status_text = "Online"
                status_icon = "⚠️"
                status_class = "status-warning"  # Yellow warning for same-IP clients
            else:
                status_text = "Online"
                status_icon = "🟢"
                status_class = "status-online"
            online_count += 1
        else:
            status_text = "Offline"
            status_icon = "🔴"
            status_class = "status-offline"
            offline_count += 1
        
        # Format location information
        location_info = info.get('location', {})
        city = location_info.get('city', 'Unknown')
        region = location_info.get('region', '')
        country = location_info.get('country', 'Unknown')
        timezone = location_info.get('timezone', 'Unknown')
        org = location_info.get('org', 'Unknown Provider')
        
        if city != 'Unknown' and region:
            location_display = f"{city}, {region}, {country}"
        elif city != 'Unknown':
            location_display = f"{city}, {country}"
        else:
            location_display = country
            
        # Format DNS information
        dns_info = info.get('dns_test', {})
        dns_location = dns_info.get('location', 'Unknown')
        dns_colo = dns_info.get('colo', 'Unknown')
        
        # DNS leak detection
        if dns_location != 'Unknown' and country != 'Unknown':
            if dns_location.upper() == country.upper():
                dns_status_icon = "✅"
            else:
                dns_status_icon = "⚠️"
        else:
            dns_status_icon = "❓"
            
        # Time formatting
        last_seen_formatted = info['last_seen'].strftime('%Y-%m-%d %H:%M:%S %Z')
        if minutes_ago < 60:
            last_seen_relative = f"{minutes_ago} minute(s) ago"
        elif minutes_ago < 1440:  # Less than 24 hours
            hours_ago = minutes_ago // 60
            last_seen_relative = f"{hours_ago} hour(s) ago"
        else:
            days_ago = minutes_ago // 1440
            last_seen_relative = f"{days_ago} day(s) ago"
        
        client_data.append({
            'id': client_id,
            'status_text': status_text,
            'status_icon': status_icon,
            'status_class': status_class,
            'public_ip': info['public_ip'],
            'location_display': location_display,
            'timezone': timezone,
            'provider': org,
            'dns_location': dns_location,
            'dns_server': dns_colo,
            'dns_status_icon': dns_status_icon,
            'minutes_ago': minutes_ago,
            'last_seen_relative': last_seen_relative,
            'last_seen_formatted': last_seen_formatted
        })
    
    # Sort clients by status (online first) then by client_id
    client_data.sort(key=lambda x: (x['status_text'] != 'Online', x['id']))
    
    template_data = {
        'clients': client_data,
        'total_clients': len(clients),
        'online_clients': online_count,
        'offline_clients': offline_count,
        'current_time': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'server_time': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'dashboard_port': DASHBOARD_PORT,
        'server_info': server_info
    };
    
    return render_template_string(DASHBOARD_HTML_TEMPLATE, **template_data)

# =============================================================================
# Error Handlers for Structured Logging
# =============================================================================

@api_app.errorhandler(404)
def handle_not_found(error):
    """Handle 404 Not Found errors with structured logging"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    auth_header = request.headers.get('Authorization')
    endpoint = request.path or 'unknown'
    log_access(endpoint, client_ip, user_agent, auth_header, "404_NOT_FOUND")
    return jsonify({'error': 'Endpoint not found'}), 404

@api_app.errorhandler(405)
def handle_method_not_allowed(error):
    """Handle 405 Method Not Allowed errors with structured logging"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    auth_header = request.headers.get('Authorization')
    endpoint = request.path or 'unknown'
    log_access(endpoint, client_ip, user_agent, auth_header, "405_METHOD_NOT_ALLOWED")
    return jsonify({'error': 'Method not allowed'}), 405

@api_app.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 Internal Server errors with structured logging"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    auth_header = request.headers.get('Authorization')
    endpoint = request.path or 'unknown'
    log_access(endpoint, client_ip, user_agent, auth_header, "500_INTERNAL_ERROR")
    return jsonify({'error': 'Internal server error'}), 500

# Dashboard App Error Handlers
@dashboard_app.errorhandler(404)
def dashboard_not_found(error):
    """Handle 404 errors for the dashboard app with user-friendly HTML response."""
    return "<h1>404 - Page Not Found</h1><p>The dashboard is only available at <a href='/dashboard'>/dashboard</a></p>", 404

@dashboard_app.errorhandler(500)
def dashboard_internal_error(error):
    """Handle 500 errors for the dashboard app with user-friendly HTML response."""
    return "<h1>500 - Internal Server Error</h1><p>Please try again later or contact support.</p>", 500

def check_clients():
    """
    Background monitoring thread that periodically checks client status.
    
    This function runs in a daemon thread and performs the following tasks:
    1. Monitors client connectivity and detects offline clients
    2. Sends Telegram alerts for client disconnections
    3. Logs comprehensive status information for all clients
    4. Manages alert state to prevent spam notifications
    
    Monitoring Logic:
        - Runs every CHECK_INTERVAL_MINUTES (default: 5 minutes)
        - Compares last_seen time against ALERT_THRESHOLD_MINUTES (default: 15)
        - Sends alerts only once per disconnection event
        - Resets alert flags when clients reconnect
        
    Alert Types:
        - No clients connected (sent once until clients return)
        - Individual client disconnections with full details
        - Includes location, DNS status, and connection history
        
    State Management:
        - alerted_clients: Set of clients already alerted for disconnection
        - announced_clients: Reset when clients go offline
        - no_clients_alert_sent: Prevents repeated "no clients" alerts
        
    Threading:
        - Runs as daemon thread (terminates automatically on shutdown)
        - Uses time.sleep() for periodic checking
        - Handles exceptions gracefully to prevent thread crashes
    """
    global no_clients_alert_sent
    alerted_clients = set()
    
    while True:
        try:
            now = get_current_time()
            
            if len(clients) == 0:
                log_info("monitor", "🔍 Check: No clients registered")
                
                # Send Telegram alert for no clients (only once)
                if not no_clients_alert_sent and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                    message = f"⚠️ <b>No VPN Clients Connected</b>\n\n"
                    message += f"No active VPN connections detected.\n"
                    message += f"Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
                    message += f"💡 This alert will not repeat until a client connects and disconnects again."
                    
                    if send_telegram_message(message):
                        log_info("telegram", "📤 No clients alert sent")
                        no_clients_alert_sent = True
                    else:
                        log_error("telegram", "❌ Failed to send no clients alert")
            else:
                log_info("monitor", f"🔍 Check: {len(clients)} client(s) registered")
                
                # Reset the no_clients_alert flag when we have clients again
                if no_clients_alert_sent:
                    no_clients_alert_sent = False
                    log_info("monitor", "🔄 Reset no-clients alert flag (clients are back)")
                
                for client_id, info in clients.items():
                    minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
                    status = '🟢 Online' if minutes_ago < ALERT_THRESHOLD_MINUTES else '🔴 Offline'
                    log_info("monitor", f"   └── {client_id}: {status} (last seen {minutes_ago}m ago)")
            
            for client_id, info in clients.items():
                minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
                
                if minutes_ago >= ALERT_THRESHOLD_MINUTES:
                    if client_id not in alerted_clients:
                        log_warn("monitor", f"⚠️ Client {client_id} exceeded threshold ({minutes_ago}m > {ALERT_THRESHOLD_MINUTES}m) - sending alert")
                        
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
                            log_info("telegram", f"✅ Failure alert sent for {client_id}")
                            alerted_clients.add(client_id)
                            announced_clients.discard(client_id)
                        else:
                            log_error("telegram", f"❌ Failed to send failure alert for {client_id}")
                    else:
                        log_info("monitor", f"   └── {client_id} still offline ({minutes_ago}m) - alert already sent")
                else:
                    alerted_clients.discard(client_id)
            
        except Exception as e:
            log_error("monitor", f"Error in check_clients: {e}")
        
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

def handle_telegram_commands():
    """
    Background thread that polls Telegram Bot API for incoming commands.
    
    This function runs continuously when Telegram credentials are configured,
    checking for new messages and processing supported commands.
    
    Supported Commands:
        - /ping: Test bot responsiveness
        - /status: Get server and client status summary
        - /help: Display available commands
        
    Polling Mechanism:
        - Uses long polling with update IDs to avoid duplicates
        - Processes only messages (ignores other update types)
        - Handles commands from any chat (not restricted to TELEGRAM_CHAT_ID)
        
    Error Handling:
        - Graceful handling of network errors and API failures
        - Continues polling even if individual commands fail
        - Logs errors for debugging while maintaining operation
        
    Threading:
        - Runs as daemon thread (terminates on shutdown)
        - Independent of main server operation
        - Can be disabled by not setting Telegram credentials
    """
    if not TELEGRAM_BOT_TOKEN:
        return
    
    last_update_id = 0
    
    while True:
        try:
            # Get updates from Telegram
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params, timeout=35, verify=True)
            log_info("telegram", f"Polling Telegram getUpdates: status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                log_info("telegram", f"Received {len(data.get('result', []))} updates from Telegram.")
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    log_info("telegram", f"Processing update_id={last_update_id}")
                    if "message" in update:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message.get("text", "")
                        log_info("telegram", f"Received message from chat_id={chat_id}: {text}")
                        # Only respond to messages from the configured chat
                        if str(chat_id) != TELEGRAM_CHAT_ID:
                            log_info("telegram", f"Ignoring message from chat_id={chat_id} (not configured chat)")
                            continue
                        
                        log_info("telegram", f"📥 Command received: {text}")
                        
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
            log_error("telegram", f"❌ Telegram polling error: {e}")
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
        log_info("telegram", "✅ Pong response sent")

def handle_status_command():
    """Handle /status command"""
    now = get_current_time()
    
    # Get server IP for same-IP detection
    global server_public_ip
    if server_public_ip is None:
        server_public_ip = get_server_public_ip()
    
    if len(clients) == 0:
        message = f"📊 <b>VPN Status</b>\n\n"
        message += f"❌ No VPN clients connected\n\n"
        message += f"Server time: <code>{now.strftime('%Y-%m-%d %H:%M:%S %Z')}</code>"
    else:
        message = f"📊 <b>VPN Status</b>\n\n"
        for client_id, info in clients.items():
            minutes_ago = int((now - info['last_seen']).total_seconds() / 60)
            client_ip = info['public_ip']
            
            if minutes_ago < ALERT_THRESHOLD_MINUTES:
                # Check if client is using same IP as server (VPN not active)
                if client_ip != 'unknown' and server_public_ip != 'Unknown' and client_ip == server_public_ip:
                    status_icon = "⚠️"
                    status_text = "Online (Same IP as server)"
                else:
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
        log_info("telegram", "✅ Status response sent")

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
        log_info("telegram", "✅ Help response sent")

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
        log_info("telegram", f"✅ Unknown command response sent for: {text}")

# =============================================================================
# Server Initialization and Startup
# =============================================================================

if __name__ == "__main__":
    """
    Main server entry point - initializes and starts the VPN Sentinel server.
    
    Startup Sequence:
    1. Validate configuration and log startup information
    2. Send Telegram startup notification (if configured)
    3. Start background client monitoring thread
    4. Start Telegram bot polling thread (if configured)
    5. Configure Flask logging (suppress access logs)
    6. Start web servers (API + Dashboard)
    
    Server Modes:
        - Single Port: API and Dashboard on same port (default API_PORT)
        - Dual Port: API on API_PORT, Dashboard on DASHBOARD_PORT
        
    Threading:
        - Client checker runs as daemon thread
        - Telegram polling runs as daemon thread (if enabled)
        - API server runs in background thread (dual port mode)
        - Dashboard server runs in main thread
        
    Shutdown:
        - Graceful shutdown on SIGTERM/SIGINT
        - Daemon threads automatically terminate

    """
    
    # Validate configuration and prepare startup
    log_info("server", "🚀 Starting VPN Sentinel Server...")
    log_info("config", f"API path: {API_PATH}")
    log_info("config", f"Alert threshold: {ALERT_THRESHOLD_MINUTES} minutes")
    log_info("config", f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    log_info("security", f"Rate limiting: {RATE_LIMIT_REQUESTS} req/min")
    log_info("security", f"API key auth: {'Enabled' if API_KEY else 'Disabled'}")
    log_info("security", f"IP whitelist: {'Disabled' if not ALLOWED_IPS or ALLOWED_IPS == [''] else 'Enabled'}")
    log_info("dashboard", f"Web dashboard: {'Enabled' if WEB_DASHBOARD_ENABLED else 'Disabled'}")
    log_info("dashboard", f"Dashboard URL: http://localhost:{DASHBOARD_PORT}/dashboard")
    
    if not TLS_CERT_PATH or not TLS_KEY_PATH:
        log_warn("config", "⚠️ No TLS certificate/key provided; HTTPS disabled (using HTTP only)")
    
    # Check for registered clients on startup
    log_info("monitor", f"🔍 Check: {len(clients)} clients registered")
    
    # Send startup notification
    startup_message = f"🚀 <b>VPN Sentinel Server Started</b>\n\n"
    startup_message += f"📊 <b>Configuration:</b>\n"
    startup_message += f"• API Port: <code>{API_PORT}</code>\n"
    startup_message += f"• Dashboard Port: <code>{DASHBOARD_PORT}</code>\n"
    startup_message += f"• Alert Threshold: <code>{ALERT_THRESHOLD_MINUTES} minutes</code>\n"
    startup_message += f"• Check Interval: <code>{CHECK_INTERVAL_MINUTES} minutes</code>\n"
    startup_message += f"• Rate Limit: <code>{RATE_LIMIT_REQUESTS} req/min</code>\n"
    startup_message += f"• TLS: <code>{'Enabled' if TLS_CERT_PATH and TLS_KEY_PATH else 'Disabled'}</code>\n\n"
    startup_message += f"🌐 <b>Access URLs:</b>\n"
    startup_message += f"• API: <code>http://your-server:{API_PORT}{API_PATH}</code>\n"
    startup_message += f"• Dashboard: <code>http://your-server:{DASHBOARD_PORT}/dashboard</code>\n"
    startup_message += f"• Health: <code>http://your-server:{API_PORT}{API_PATH}/health</code>\n\n"
    startup_message += f"✅ <b>Server is ready to receive VPN client connections!</b>"
    
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        if send_telegram_message(startup_message):
            log_info("telegram", "Startup notification sent successfully")
        else:
            log_warn("telegram", "Failed to send startup notification")
    
    # Start background monitoring thread
    checker_thread = threading.Thread(target=check_clients, daemon=True)
    checker_thread.start()
    
    # Start Telegram bot polling thread only if credentials are provided
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        telegram_thread = threading.Thread(target=handle_telegram_commands, daemon=True)
        telegram_thread.start()
        log_info("telegram", "Bot polling started")
    else:
        log_info("telegram", "Telegram integration disabled - no bot token or chat ID provided")
    
    # Suppress Flask's built-in access logging since we have structured logging
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # Only show errors, suppress access logs
    
    # Start web servers based on configuration
    if WEB_DASHBOARD_ENABLED and API_PORT != DASHBOARD_PORT:
        # Dual port mode: API and Dashboard on separate ports
        def run_api_server():
            ssl_ctx = None
            if TLS_CERT_PATH and TLS_KEY_PATH:
                               ssl_ctx = (TLS_CERT_PATH, TLS_KEY_PATH)
            api_app.run(host='0.0.0.0', port=API_PORT, debug=False, use_reloader=False, ssl_context=ssl_ctx)
        
        def run_dashboard_server():
            ssl_ctx = None
            if TLS_CERT_PATH and TLS_KEY_PATH:
                ssl_ctx = (TLS_CERT_PATH, TLS_KEY_PATH)
            dashboard_app.run(host='0.0.0.0', port=DASHBOARD_PORT, debug=False, use_reloader=False, ssl_context=ssl_ctx)
        
        # Start API server in background thread
        api_thread = threading.Thread(target=run_api_server, daemon=True)
        api_thread.start()
        log_info("server", f"🚀 API Server started on port {API_PORT}")
        
        # Start dashboard server in main thread
        log_info("server", f"🌐 Dashboard Server starting on port {DASHBOARD_PORT}")
        run_dashboard_server()
    else:
        # Single port mode: API and Dashboard on same port
        @api_app.route('/dashboard', methods=['GET'])
        def dashboard_single_port():
            return web_dashboard()
        
        log_info("server", f"🚀 Server starting on port {API_PORT} (API + Dashboard)")
        ssl_ctx = None
        if TLS_CERT_PATH and TLS_KEY_PATH:
            ssl_ctx = (TLS_CERT_PATH, TLS_KEY_PATH)
        api_app.run(host='0.0.0.0', port=API_PORT, debug=False, ssl_context=ssl_ctx)
