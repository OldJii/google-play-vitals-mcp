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
        "play_get_release_tracks",
        "play_search_error_issues",
        "play_get_error_reports",
        "play_list_anomalies",
        "play_list_accessible_apps",
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


def test_dispatch_atomic_tools():
    from unittest.mock import MagicMock

    server = GooglePlayVitalsMCPServer(default_package_name="com.example.app")
    server.client = MagicMock()
    server.client.resolve_package_name.return_value = "com.example.app"

    # 1. play_get_release_tracks
    server.client.fetch_release_tracks.return_value = {
        "tracks": [
            {
                "type": "PRODUCTION",
                "displayName": "Production",
                "servingReleases": [{"displayName": "2.0.0", "versionCodes": ["200"]}],
            }
        ]
    }
    tracks_res = server.dispatch_tool("play_get_release_tracks", {"package_name": "com.example.app"})
    assert tracks_res["package_name"] == "com.example.app"
    assert tracks_res["tracks"][0]["track_type"] == "PRODUCTION"

    # 2. play_search_error_issues
    server.client.search_error_issues.return_value = {
        "errorIssues": [
            {
                "name": "apps/com.example.app/errorIssues/crash_1",
                "type": "CRASH",
                "cause": "NullPointerException",
                "errorReportCount": "500",
                "distinctUsers": "300",
            }
        ],
        "nextPageToken": None,
    }
    issues_res = server.dispatch_tool(
        "play_search_error_issues",
        {
            "package_name": "com.example.app",
            "error_type": "CRASH",
            "version_code": 200,
            "page_size": 10,
        },
    )
    assert issues_res["error_type"] == "CRASH"
    assert issues_res["version_filter"] == 200
    assert issues_res["retrieved_issues_count"] == 1
    assert issues_res["error_issues"][0]["issue_id"] == "crash_1"

    # 3. play_get_error_reports
    server.client.search_error_reports.return_value = {
        "errorReports": [
            {
                "deviceModel": {"name": "Pixel 8"},
                "osVersion": {"apiLevel": 34},
                "eventTime": "2026-09-14T10:00:00Z",
                "stackTrace": {
                    "exceptionClass": "java.lang.NullPointerException",
                    "frames": [],
                },
            }
        ],
        "nextPageToken": None,
    }
    reports_res = server.dispatch_tool(
        "play_get_error_reports",
        {"issue_id": "crash_1", "package_name": "com.example.app"},
    )
    assert reports_res["issue_id"] == "crash_1"
    assert reports_res["reports_count"] == 1
    assert reports_res["sample_reports"][0]["device"] == "Pixel 8"



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
