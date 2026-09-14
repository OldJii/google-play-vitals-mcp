"""
Unit tests for Token Saver / Data Cleaning Engine.
"""

from google_play_vitals_mcp.cleaner import clean_rate_metrics, clean_stack_trace


def test_clean_rate_metrics_normal():
    raw_protobuf_mock = {
        "rows": [
            {
                "startTime": {"year": 2026, "month": 9, "day": 10},
                "metrics": {
                    "anrRate": {"decimalValue": "0.0035"},
                    "userPerceivedAnrRate": {"decimalValue": "0.0020"},
                    "distinctUsers": {"count": "150000"},
                },
            },
            {
                "startTime": {"year": 2026, "month": 9, "day": 11},
                "metrics": {
                    "anrRate": {"decimalValue": "0.0030"},
                    "userPerceivedAnrRate": {"decimalValue": "0.0018"},
                    "distinctUsers": {"count": "152000"},
                },
            },
        ]
    }

    cleaned = clean_rate_metrics(raw_protobuf_mock, "anrRate", "userPerceivedAnrRate")

    assert cleaned["days_counted"] == 2
    assert cleaned["avg_overall_rate"] == "0.33%"
    assert cleaned["avg_user_perceived_rate"] == "0.19%"
    assert len(cleaned["timeline"]) == 2
    assert cleaned["timeline"][0]["date"] == "2026-09-10"
    assert cleaned["timeline"][0]["overall_rate"] == "0.35%"
    assert cleaned["timeline"][0]["user_perceived_rate"] == "0.20%"
    assert cleaned["timeline"][0]["daily_active_users"] == 150000


def test_clean_rate_metrics_empty_and_corrupt():
    empty_data = {"rows": []}
    cleaned = clean_rate_metrics(empty_data, "anrRate", "userPerceivedAnrRate")
    assert cleaned["days_counted"] == 0
    assert cleaned["avg_overall_rate"] == "0.00%"
    assert cleaned["timeline"] == []

    corrupt_data = {
        "rows": [
            {"startTime": {}, "metrics": {}},
            {
                "startTime": {"year": 2026, "month": 9, "day": 1},
                "metrics": {"anrRate": {"decimalValue": "invalid"}},
            },
        ]
    }
    cleaned_corrupt = clean_rate_metrics(corrupt_data, "anrRate", "userPerceivedAnrRate")
    assert cleaned_corrupt["days_counted"] == 0


def test_clean_stack_trace_standard():
    raw_report = {
        "deviceModel": {"name": "Pixel 8"},
        "osVersion": {"apiLevel": 34},
        "eventTime": "2026-09-14T08:00:00Z",
        "stackTrace": {
            "exceptionClass": "android.app.anr.ApplicationNotResponding",
            "message": "Input dispatching timed out",
            "frames": [
                {
                    "className": "android.os.MessageQueue",
                    "methodName": "nativePollOnce",
                    "fileName": "MessageQueue.java",
                    "lineNumber": 0,
                },
                {
                    "className": "com.example.app.MainActivity",
                    "methodName": "onStart",
                    "fileName": "MainActivity.java",
                    "lineNumber": 42,
                },
            ],
        },
    }

    cleaned = clean_stack_trace(raw_report, max_frames=10)

    assert cleaned["device"] == "Pixel 8"
    assert cleaned["android_api"] == 34
    assert cleaned["event_time"] == "2026-09-14T08:00:00Z"
    assert (
        "android.app.anr.ApplicationNotResponding: Input dispatching timed out"
        in cleaned["stack_trace"]
    )
    assert "at com.example.app.MainActivity.onStart(MainActivity.java:42)" in cleaned["stack_trace"]


def test_clean_release_tracks():
    from google_play_vitals_mcp.cleaner import clean_release_tracks

    mock_tracks_raw = {
        "tracks": [
            {
                "type": "PRODUCTION",
                "displayName": "Production Track",
                "servingReleases": [
                    {"displayName": "1.0.0", "versionCodes": ["100", "101"]},
                    {"displayName": "0.9.9", "versionCodes": ["99"]},
                ],
            },
            {
                "type": "INTERNAL",
                "displayName": "Internal Track",
                "servingReleases": [
                    {"displayName": "1.0.1-alpha", "versionCodes": ["102"]},
                ],
            },
        ]
    }

    result = clean_release_tracks(mock_tracks_raw)
    assert len(result["tracks"]) == 2
    prod = result["tracks"][0]
    assert prod["track_type"] == "PRODUCTION"
    assert prod["display_name"] == "Production Track"
    assert len(prod["serving_releases"]) == 2
    assert prod["serving_releases"][0]["release_name"] == "1.0.0"
    assert prod["serving_releases"][0]["version_codes"] == [100, 101]


def test_clean_error_issue():
    from google_play_vitals_mcp.cleaner import clean_error_issue

    mock_issue = {
        "name": "apps/com.example.app/errorIssues/issue_12345",
        "type": "CRASH",
        "cause": "NullPointerException: Attempt to invoke virtual method",
        "location": "com.example.app.MainActivity:onCreate",
        "errorReportCount": "1250",
        "distinctUsers": "890",
    }

    cleaned = clean_error_issue(mock_issue)
    assert cleaned["issue_id"] == "issue_12345"
    assert cleaned["issue_resource_name"] == "apps/com.example.app/errorIssues/issue_12345"
    assert cleaned["error_type"] == "CRASH"
    assert cleaned["title"] == "NullPointerException: Attempt to invoke virtual method"
    assert cleaned["error_report_count"] == 1250
    assert cleaned["distinct_users"] == 890

