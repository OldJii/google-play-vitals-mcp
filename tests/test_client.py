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


def test_build_timeline_spec():
    client = GooglePlayVitalsClient()
    spec = client.build_timeline_spec(days=7)
    assert spec["aggregationPeriod"] == "DAILY"
    assert "startTime" in spec
    assert "endTime" in spec
    assert spec["startTime"]["year"] > 2000
