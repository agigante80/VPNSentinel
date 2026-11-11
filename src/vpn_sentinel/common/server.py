"""Flask application factories for VPN Sentinel server.

Provides the multi-app Flask architecture with separate applications
for API, health, and dashboard endpoints.
"""

from flask import Flask

# Flask application instances
# common/static/ holds the dashboard icon only. Flask's default /static route would serve it on every
# app, so it is disabled on all three; the dashboard serves the icon through explicit /favicon.* routes.
api_app = Flask(__name__, static_folder=None)  # API server application
health_app = Flask(__name__, static_folder=None)  # Health server application (public endpoints)
dashboard_app = Flask(__name__, static_folder=None)  # Dashboard web application

__all__ = ["api_app", "health_app", "dashboard_app"]
