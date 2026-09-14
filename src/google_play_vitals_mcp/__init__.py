"""
Google Play Vitals MCP Server
Universal, token-efficient Model Context Protocol server for Google Play Android Vitals.
"""

__version__ = "1.1.0"
__author__ = "Oldjii"
__license__ = "MIT"

from .auth import load_user_credentials, login_via_browser, logout
from .cleaner import clean_rate_metrics, clean_stack_trace
from .client import GooglePlayVitalsClient

__all__ = [
    "__version__",
    "clean_rate_metrics",
    "clean_stack_trace",
    "GooglePlayVitalsClient",
    "load_user_credentials",
    "login_via_browser",
    "logout",
]
