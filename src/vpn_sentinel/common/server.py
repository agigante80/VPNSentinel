"""Flask application factories for VPN Sentinel server.

Provides the multi-app Flask architecture with separate applications
for API, health, and dashboard endpoints.
"""
from flask import Flask

# Flask application instances
api_app = Flask(__name__)               # API server application
health_app = Flask(__name__)            # Health server application (public endpoints)
dashboard_app = Flask(__name__)         # Dashboard web application

__all__ = ["api_app", "health_app", "dashboard_app"]