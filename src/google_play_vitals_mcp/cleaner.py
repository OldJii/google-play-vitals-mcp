"""
Token Compression and Data Cleaning Engine (Token Saver)
Transforms raw, deeply nested Google Play Developer Reporting Protobuf responses
into compact, flat structures and standard Java stack traces for LLMs.
"""

from typing import Any


def clean_rate_metrics(
    raw_data: dict[str, Any],
    rate_key: str,
    perceived_rate_key: str,
) -> dict[str, Any]:
    """
    Compress verbose Google Play metric rows into a compact daily timeline and averages.

    Filters out ~80% redundant protobuf metadata (e.g., empty dimensions, nested type descriptors).
    """
    rows = raw_data.get("rows", [])
    timeline: list[dict[str, Any]] = []
    total_rate = 0.0
    total_perceived = 0.0
    valid_count = 0

    for r in rows:
        st = r.get("startTime", {})
        year = st.get("year")
        month = st.get("month", 1)
        day = st.get("day", 1)
        if not year:
            continue

        date_str = f"{year}-{month:02d}-{day:02d}"
        metrics_raw = r.get("metrics", [])
        metrics_dict: dict[str, Any] = {}
        if isinstance(metrics_raw, list):
            for m in metrics_raw:
                if isinstance(m, dict):
                    m_name = m.get("metric")
                    if m_name:
                        metrics_dict[m_name] = m
        elif isinstance(metrics_raw, dict):
            metrics_dict = metrics_raw

        rate_entry = metrics_dict.get(rate_key, {})
        rate_val = (
            rate_entry.get("decimalValue", {}).get("value")
            if isinstance(rate_entry.get("decimalValue"), dict)
            else rate_entry.get("decimalValue") or rate_entry.get("value") or 0.0
        )

        perceived_entry = metrics_dict.get(perceived_rate_key, {})
        perceived_val = (
            perceived_entry.get("decimalValue", {}).get("value")
            if isinstance(perceived_entry.get("decimalValue"), dict)
            else perceived_entry.get("decimalValue") or perceived_entry.get("value") or 0.0
        )

        users_entry = metrics_dict.get("distinctUsers", {})
        users_val = (
            users_entry.get("decimalValue", {}).get("value")
            if isinstance(users_entry.get("decimalValue"), dict)
            else users_entry.get("count") or users_entry.get("value") or 0
        )

        try:
            rate_float = float(rate_val)
            perceived_float = float(perceived_val)
            users_int = int(users_val)
        except (ValueError, TypeError):
            continue

        timeline.append(
            {
                "date": date_str,
                "overall_rate": f"{rate_float * 100:.2f}%",
                "user_perceived_rate": f"{perceived_float * 100:.2f}%",
                "daily_active_users": users_int,
            }
        )
        total_rate += rate_float
        total_perceived += perceived_float
        valid_count += 1

    avg_overall = (total_rate / valid_count * 100) if valid_count > 0 else 0.0
    avg_perceived = (total_perceived / valid_count * 100) if valid_count > 0 else 0.0

    return {
        "days_counted": valid_count,
        "avg_overall_rate": f"{avg_overall:.2f}%",
        "avg_user_perceived_rate": f"{avg_perceived:.2f}%",
        "timeline": timeline,
    }


def clean_stack_trace(raw_report: dict[str, Any], max_frames: int = 30) -> dict[str, Any]:
    """
    Extract and reassemble raw error report into standard, readable Java stack trace.

    Drastically compresses context tokens by removing repetitive JSON nesting and keeping
    only relevant application and framework frames.
    """
    device = raw_report.get("deviceModel", {}).get("name") or "Unknown Device"
    os_ver = raw_report.get("osVersion", {}).get("apiLevel") or "Unknown API"
    time_str = raw_report.get("eventTime", "")

    st_obj = raw_report.get("stackTrace") or {}
    raw_lines: list[str] = []

    # Title / Exception line
    exc_class = (
        st_obj.get("exceptionClass") or st_obj.get("title") or "ANR / Application Not Responding"
    )
    msg = st_obj.get("message", "")
    raw_lines.append(f"{exc_class}: {msg}".strip())

    # Stack frames
    frames = st_obj.get("frames", [])
    for f in frames:
        cls_name = f.get("className", "")
        method_name = f.get("methodName", "")
        file_name = f.get("fileName", "")
        line_num = f.get("lineNumber", -1)

        if cls_name and method_name:
            location = (
                f"{file_name}:{line_num}" if line_num > 0 else (file_name or "Unknown Source")
            )
            raw_lines.append(f"    at {cls_name}.{method_name}({location})")
        elif f.get("rawText"):
            raw_lines.append(f"    {f.get('rawText').strip()}")

    truncated_trace = "\n".join(raw_lines[:max_frames])
    if len(raw_lines) > max_frames:
        truncated_trace += f"\n    ... {len(raw_lines) - max_frames} frames omitted"

    return {
        "event_time": time_str,
        "device": device,
        "android_api": os_ver,
        "stack_trace": truncated_trace,
    }
