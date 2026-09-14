"""
OAuth 2.0 User Authentication Module for Google Play Vitals MCP.
Enables browser-based one-click login without requiring service_account.json files.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# Scopes required for Google Play Developer Reporting API
SCOPES = ["https://www.googleapis.com/auth/playdeveloperreporting"]

# Storage location for user OAuth credentials
USER_CONFIG_DIR = os.path.expanduser("~/.config/google-play-vitals")
USER_CREDENTIALS_FILE = os.path.join(USER_CONFIG_DIR, "user_credentials.json")

# Default public desktop client credentials (compatible with Google Cloud Shell & CLI tools)
DEFAULT_CLIENT_ID = os.environ.get(
    "GOOGLE_OAUTH_CLIENT_ID",
    "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com",
)
DEFAULT_CLIENT_SECRET = os.environ.get(
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "d-FL95Q19q7MQmFpd7hHD0Ty",
)


def get_client_config(
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict[str, Any]:
    """Construct OAuth 2.0 client configuration dictionary."""
    cid = client_id or DEFAULT_CLIENT_ID
    sec = client_secret or DEFAULT_CLIENT_SECRET
    return {
        "installed": {
            "client_id": cid,
            "client_secret": sec,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def load_user_credentials() -> Credentials | None:
    """
    Load saved OAuth2 user credentials from ~/.config/google-play-vitals/user_credentials.json.
    Automatically refreshes the token if expired and writes the fresh token back.
    """
    if not os.path.exists(USER_CREDENTIALS_FILE):
        return None

    try:
        with open(USER_CREDENTIALS_FILE, encoding="utf-8") as f:
            data = json.load(f)

        creds = Credentials.from_authorized_user_info(data, scopes=SCOPES)
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Google OAuth2 credentials...")
            creds.refresh(Request())
            save_user_credentials(creds)
        return creds
    except Exception as e:
        logger.warning("Failed to load or refresh user OAuth2 credentials: %s", e)
        return None


def save_user_credentials(creds: Credentials) -> str:
    """Save OAuth2 credentials securely to disk (chmod 600)."""
    os.makedirs(USER_CONFIG_DIR, mode=0o700, exist_ok=True)
    payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    with open(USER_CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Restrict file permissions to owner read/write only
    with contextlib.suppress(OSError):
        os.chmod(USER_CREDENTIALS_FILE, 0o600)

    return USER_CREDENTIALS_FILE


def login_via_browser(
    client_id: str | None = None,
    client_secret: str | None = None,
    port: int = 0,
) -> str:
    """
    Launch a local HTTP server and open the system browser for Google OAuth 2.0 authorization.
    Returns the path to the saved credentials file upon success.
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise ImportError(
            "Missing 'google-auth-oauthlib'. Install via: pip install google-auth-oauthlib"
        ) from e

    config = get_client_config(client_id, client_secret)
    flow = InstalledAppFlow.from_client_config(config, scopes=SCOPES)

    print("🌐 Launching local browser for Google authorization...")
    print("👉 Please log in to your Google Account and grant permission.")

    creds = flow.run_local_server(
        port=port,
        prompt="consent",
        success_message="Authentication successful! You may now close this window and return to your terminal.",
    )

    path = save_user_credentials(creds)
    return path


def logout() -> bool:
    """Remove locally cached OAuth 2.0 credentials."""
    if os.path.exists(USER_CREDENTIALS_FILE):
        try:
            os.remove(USER_CREDENTIALS_FILE)
            return True
        except OSError as e:
            logger.error("Failed to delete user credentials file: %s", e)
            return False
    return False
