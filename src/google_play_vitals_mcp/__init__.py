"""
Google Play Vitals MCP Server
Universal, token-efficient Model Context Protocol server for Google Play Android Vitals.
"""

__version__ = "1.0.0"
__author__ = "Google Play Vitals MCP Contributors"
__license__ = "MIT"

from .cleaner import clean_rate_metrics, clean_stack_trace
from .client import GooglePlayVitalsClient

__all__ = [
    "__version__",
    "clean_rate_metrics",
    "clean_stack_trace",
    "GooglePlayVitalsClient",
]
