@api_app.route(f'{API_PATH}/health', methods=['GET'])
def health():
    """Comprehensive health check - liveness probe with detailed status"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    log_access('health', client_ip, user_agent, None, "200_OK")
    
    import psutil
    
    # Get system resource information
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    health_status = {
        'status': 'healthy',
        'server_time': get_current_time().isoformat(),
        'active_clients': len(clients),
        'uptime_info': 'VPN Keepalive Server is running',
        'system': {
            'memory_usage_percent': round(memory.percent, 1),
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_usage_percent': round(disk.percent, 1),
            'disk_free_gb': round(disk.free / (1024**3), 2)
        },
        'dependencies': {
            'telegram_bot': 'not_configured'
        }
    }
    
    # Check for critical resource issues
    if memory.percent > 95:  # Critical memory usage
        health_status['status'] = 'unhealthy'
        health_status['issues'] = ['Critical memory usage']
        
    if disk.percent > 95:  # Critical disk usage
        health_status['status'] = 'unhealthy'
        health_status['issues'] = health_status.get('issues', []) + ['Critical disk usage']
    
    # Check Telegram bot status (lighter check than readiness probe)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        health_status['dependencies']['telegram_bot'] = 'configured'
    else:
        health_status['dependencies']['telegram_bot'] = 'not_configured'
    
    # Return appropriate HTTP status
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code