"""
Unit tests for OAuth 2.0 User Authentication and Browser Login module.
"""

import os
from unittest.mock import MagicMock, patch

from google_play_vitals_mcp import auth
from google_play_vitals_mcp.client import GooglePlayVitalsClient


def test_get_client_config():
    config = auth.get_client_config("custom-client-id", "custom-client-secret")
    assert config["installed"]["client_id"] == "custom-client-id"
    assert config["installed"]["client_secret"] == "custom-client-secret"
    assert "https://accounts.google.com/o/oauth2/auth" in config["installed"]["auth_uri"]


def test_save_and_load_user_credentials(tmp_path):
    mock_file = str(tmp_path / "user_credentials.json")
    with (
        patch.object(auth, "USER_CREDENTIALS_FILE", mock_file),
        patch.object(auth, "USER_CONFIG_DIR", str(tmp_path)),
    ):
        mock_creds = MagicMock()
        mock_creds.token = "fake-token"
        mock_creds.refresh_token = "fake-refresh"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "fake-id"
        mock_creds.client_secret = "fake-secret"
        mock_creds.scopes = ["https://www.googleapis.com/auth/playdeveloperreporting"]
        mock_creds.expired = False

        saved_path = auth.save_user_credentials(mock_creds)
        assert saved_path == mock_file
        assert os.path.exists(mock_file)

        # Test loading
        with patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_info"
        ) as mock_from_info:
            mock_from_info.return_value = mock_creds
            loaded = auth.load_user_credentials()
            assert loaded is not None
            assert loaded.token == "fake-token"

        # Test logout
        assert auth.logout() is True
        assert not os.path.exists(mock_file)
        assert auth.logout() is False


def test_load_user_credentials_missing(tmp_path):
    non_existent = str(tmp_path / "absent.json")
    with patch.object(auth, "USER_CREDENTIALS_FILE", non_existent):
        assert auth.load_user_credentials() is None


def test_client_picks_oauth2_credentials():
    mock_creds = MagicMock()
    mock_build = MagicMock()
    mock_discovery = MagicMock(build=mock_build)

    with (
        patch.dict(
            "sys.modules",
            {
                "googleapiclient": MagicMock(discovery=mock_discovery),
                "googleapiclient.discovery": mock_discovery,
            },
        ),
        patch("google_play_vitals_mcp.auth.load_user_credentials", return_value=mock_creds),
    ):
        client = GooglePlayVitalsClient()
        service = client.get_service()

        assert service is not None
        mock_build.assert_called_once_with(
            "playdeveloperreporting",
            "v1beta1",
            credentials=mock_creds,
            cache_discovery=False,
        )
