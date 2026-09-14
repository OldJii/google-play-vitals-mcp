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
