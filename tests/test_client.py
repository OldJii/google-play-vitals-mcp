"""
Unit tests for Universal Google Play Vitals Client and Cache.
"""

import time

import pytest

from google_play_vitals_mcp.client import GooglePlayVitalsClient, VitalsCache


def test_vitals_cache():
    cache = VitalsCache(default_ttl_seconds=1)
    cache.set("key1", "val1")
    assert cache.get("key1") == "val1"

    # Test expiration
    time.sleep(1.1)
    assert cache.get("key1") is None

    # Test clear
    cache.set("key2", "val2")
    cache.clear()
    assert cache.get("key2") is None


def test_resolve_package_name():
    # 1. Given explicit param
    client = GooglePlayVitalsClient()
    assert client.resolve_package_name("com.demo.app") == "com.demo.app"

    # 2. Given default package name in init
    client_default = GooglePlayVitalsClient(default_package_name="com.default.app")
    assert client_default.resolve_package_name(None) == "com.default.app"

    # 3. Missing package name raises ValueError
    client_empty = GooglePlayVitalsClient()
    with pytest.raises(ValueError) as exc_info:
        client_empty.resolve_package_name(None)
    assert "Package name is required" in str(exc_info.value)


def test_missing_credentials_path_is_redacted(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLAY_CREDENTIALS_JSON", raising=False)
    private_path = "/private/example/service-account.json"
    client = GooglePlayVitalsClient(credentials_path=private_path)

    with pytest.raises(FileNotFoundError) as exc_info:
        client.get_service()

    assert private_path not in str(exc_info.value)


def test_build_timeline_spec():
    client = GooglePlayVitalsClient()
    spec = client.build_timeline_spec(days=7)
    assert spec["aggregationPeriod"] == "DAILY"
    assert "startTime" in spec
    assert "endTime" in spec
    assert spec["startTime"]["year"] > 2000


def test_search_error_issues_filter_composition():
    from unittest.mock import MagicMock

    client = GooglePlayVitalsClient(default_package_name="com.example.app")
    mock_service = MagicMock()
    mock_search = MagicMock()
    mock_execute = MagicMock(
        return_value={"errorIssues": [{"name": "apps/com.example.app/errorIssues/test1"}]}
    )

    mock_service.vitals().errors().issues().search = mock_search
    mock_search.return_value.execute = mock_execute
    client._service = mock_service

    # Test full filters: error_type, version_code, is_user_perceived, app_process_state
    client.search_error_issues(
        package_name="com.example.app",
        error_type="CRASH",
        version_code=100200,
        is_user_perceived=True,
        app_process_state="FOREGROUND",
        custom_filter='deviceModel = "google/pixel"',
        page_size=10,
    )

    mock_search.assert_called_once()
    _, kwargs = mock_search.call_args
    assert kwargs["parent"] == "apps/com.example.app"
    assert kwargs["pageSize"] == 10
    filter_arg = kwargs["filter"]
    assert "errorIssueType = CRASH" in filter_arg
    assert "versionCode = 100200" in filter_arg
    assert "isUserPerceived" in filter_arg
    assert "appProcessState = FOREGROUND" in filter_arg
    assert '(deviceModel = "google/pixel")' in filter_arg
