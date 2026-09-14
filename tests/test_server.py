"""
Unit tests for GooglePlayVitalsMCPServer tools dispatch and status check.
"""

from unittest.mock import patch

import pytest

from google_play_vitals_mcp.server import GooglePlayVitalsMCPServer


def test_tool_definitions():
    server = GooglePlayVitalsMCPServer()
    tools = server.get_tool_definitions()
    tool_names = [t["name"] for t in tools]

    expected = [
        "play_check_status",
        "play_get_top_anr_summary",
        "play_get_metric_trends",
        "play_compare_versions",
        "play_get_raw_error_reports",
    ]
    for exp in expected:
        assert exp in tool_names

    # Check schema valid
    for t in tools:
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"


def test_handle_check_status():
    server = GooglePlayVitalsMCPServer()
    status = server.handle_check_status({"package_name": "com.test.app"})

    assert "server_version" in status
    assert "dependencies_installed" in status
    assert "status" in status
    assert status["configured_package_name"] == "com.test.app"


def test_compare_versions_logic():
    server = GooglePlayVitalsMCPServer()

    mock_summary_a = {
        "summary": {
            "avg_user_perceived_rate": "1.20%",
        }
    }
    mock_summary_b = {
        "summary": {
            "avg_user_perceived_rate": "0.80%",
        }
    }

    with patch.object(server, "handle_get_metric_trends") as mock_trends:
        mock_trends.side_effect = [mock_summary_a, mock_summary_b]

        result = server.handle_compare_versions(
            {
                "package_name": "com.test.app",
                "baseline_version": 100,
                "target_version": 200,
                "metric_type": "ANR",
            }
        )

        assert result["baseline_version"]["user_perceived_rate"] == "1.20%"
        assert result["target_version"]["user_perceived_rate"] == "0.80%"
        assert result["delta"] == "-0.40%"
        assert "IMPROVEMENT" in result["relative_improvement"]
        assert "33.3%" in result["relative_improvement"]


def test_dispatch_unknown_tool():
    server = GooglePlayVitalsMCPServer()
    with pytest.raises(ValueError) as exc:
        server.dispatch_tool("unknown_tool", {})
    assert "Unknown tool" in str(exc.value)


def test_prompt_definitions_and_dispatch():
    server = GooglePlayVitalsMCPServer(default_package_name="com.test.app")
    prompts = server.get_prompt_definitions()
    prompt_names = [p["name"] for p in prompts]

    assert "analyze-anr-incident" in prompt_names
    assert "verify-baseline-profile" in prompt_names
    assert "vitals-weekly-report" in prompt_names

    # Test dispatch analyze-anr-incident
    res1 = server.dispatch_prompt("analyze-anr-incident", {"package_name": "com.test.app"})
    assert "com.test.app" in res1["messages"][0]["content"]["text"]
    assert "play_get_top_anr_summary" in res1["messages"][0]["content"]["text"]

    # Test dispatch verify-baseline-profile
    res2 = server.dispatch_prompt(
        "verify-baseline-profile",
        {"baseline_version": 100, "target_version": 101, "package_name": "com.test.app"},
    )
    assert "100" in res2["messages"][0]["content"]["text"]
    assert "101" in res2["messages"][0]["content"]["text"]

    # Test dispatch unknown prompt
    with pytest.raises(ValueError) as exc:
        server.dispatch_prompt("unknown_prompt", {})
    assert "Unknown prompt template" in str(exc.value)


def test_resource_definitions_and_read():
    server = GooglePlayVitalsMCPServer(default_package_name="com.test.app")
    resources = server.get_resource_definitions()
    assert len(resources) >= 1
    assert resources[0]["uri"] == "vitals://status"

    content = server.read_resource("vitals://status")
    assert content["uri"] == "vitals://status"
    assert content["mimeType"] == "application/json"
    assert "capabilities_supported" in content["text"]

    with pytest.raises(ValueError) as exc:
        server.read_resource("vitals://unknown")
    assert "Resource URI not found" in str(exc.value)
