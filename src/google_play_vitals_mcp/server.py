"""
Google Play Vitals MCP Server Implementation
High-performance, LLM-optimized Model Context Protocol server.
Compatible with Cursor, Claude Desktop, Claude Code, Codex, Windsurf, and any MCP client.
Supports Tools, Prompts, and Resources per latest MCP specifications.
"""

import json
import logging
import os
import sys
from typing import Any

from . import __version__
from .cleaner import clean_rate_metrics, clean_stack_trace
from .client import GooglePlayVitalsClient

# Configure logger to stderr so stdout is strictly preserved for JSON-RPC
logger = logging.getLogger("google_play_vitals_mcp")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class GooglePlayVitalsMCPServer:
    """Universal MCP Server providing Google Play Android Vitals tools, prompts, and resources."""

    def __init__(
        self,
        default_package_name: str | None = None,
        default_credentials_path: str | None = None,
    ):
        self.client = GooglePlayVitalsClient(
            credentials_path=default_credentials_path,
            default_package_name=default_package_name,
        )
        self.server_name = "google-play-vitals-mcp"
        self.server_version = __version__

    # ==========================================================================
    # 1. MCP Tools Schema & Definitions
    # ==========================================================================

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool schemas adhering to Model Context Protocol specification."""
        return [
            {
                "name": "play_check_status",
                "description": (
                    "Verify Google Play API dependencies, GCP Service Account credentials, "
                    "and environment readiness."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "credentials_path": {
                            "type": "string",
                            "description": "Optional path to GCP service account JSON key file.",
                        },
                        "package_name": {
                            "type": "string",
                            "description": "Optional target Android package name to verify.",
                        },
                    },
                },
            },
            {
                "name": "play_get_top_anr_summary",
                "description": (
                    "[One-shot Diagnosis] Retrieve top ANR error clusters along with affected "
                    "user counts, occurrence rates, and representative cleaned main-thread stack traces. "
                    "Eliminates back-and-forth round trips."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "package_name": {
                            "type": "string",
                            "description": "Android package name (e.g., com.example.app). Optional if GOOGLE_PLAY_PACKAGE_NAME is set.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top ANR clusters to retrieve (default: 5).",
                        },
                        "credentials_path": {
                            "type": "string",
                            "description": "Optional path to GCP credentials JSON.",
                        },
                    },
                },
            },
            {
                "name": "play_get_metric_trends",
                "description": (
                    "[Token-efficient Metrics] Query trends and daily averages for ANR rate, "
                    "slow cold start rate (Baseline Profile verification), or Crash rate. "
                    "Redundant Protobuf metadata is stripped."
                ),
                "inputSchema": {
                    "type": "object",
                    "required": ["metric_type"],
                    "properties": {
                        "metric_type": {
                            "type": "string",
                            "enum": ["ANR", "STARTUP", "CRASH"],
                            "description": (
                                "Metric category: 'ANR' (Application Not Responding), "
                                "'STARTUP' (Slow cold start rate for Baseline Profile evaluation), "
                                "or 'CRASH' (Fatal crash rate)."
                            ),
                        },
                        "package_name": {
                            "type": "string",
                            "description": "Android package name. Optional if environment variable is set.",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of past days to query (default: 7).",
                        },
                        "version_code": {
                            "type": "integer",
                            "description": "Optional specific Android versionCode filter (e.g. 100200).",
                        },
                        "credentials_path": {
                            "type": "string",
                            "description": "Optional path to GCP credentials JSON.",
                        },
                    },
                },
            },
            {
                "name": "play_compare_versions",
                "description": (
                    "[Version Comparison] Compare metrics between two app versions (e.g., before and after "
                    "Baseline Profile / ANR fixes). Automatically calculates delta and percentage improvement."
                ),
                "inputSchema": {
                    "type": "object",
                    "required": ["baseline_version", "target_version"],
                    "properties": {
                        "baseline_version": {
                            "type": "integer",
                            "description": "Baseline/older version code (e.g. 200).",
                        },
                        "target_version": {
                            "type": "integer",
                            "description": "Target/newer version code (e.g. 201).",
                        },
                        "metric_type": {
                            "type": "string",
                            "enum": ["ANR", "STARTUP", "CRASH"],
                            "description": "Metric to compare (default: 'ANR').",
                        },
                        "package_name": {
                            "type": "string",
                            "description": "Android package name. Optional if environment variable is set.",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Days range to aggregate (default: 7).",
                        },
                        "credentials_path": {
                            "type": "string",
                            "description": "Optional path to GCP credentials JSON.",
                        },
                    },
                },
            },
            {
                "name": "play_get_raw_error_reports",
                "description": (
                    "[Deep-dive Drilldown] Fetch multi-device environmental samples and full stack traces "
                    "for a specific error issue ID."
                ),
                "inputSchema": {
                    "type": "object",
                    "required": ["issue_name"],
                    "properties": {
                        "issue_name": {
                            "type": "string",
                            "description": "Full issue resource name (e.g., 'apps/.../errorIssues/...').",
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of sample reports to retrieve (default: 3).",
                        },
                        "credentials_path": {
                            "type": "string",
                            "description": "Optional path to GCP credentials JSON.",
                        },
                    },
                },
            },
        ]

    # ==========================================================================
    # 2. MCP Prompts Schema & Definitions
    # ==========================================================================

    def get_prompt_definitions(self) -> list[dict[str, Any]]:
        """Return MCP prompt templates for AI workflow orchestration."""
        return [
            {
                "name": "analyze-anr-incident",
                "description": (
                    "Interactive diagnostic prompt to analyze top production ANR clusters, "
                    "interpret stack traces, and recommend concrete architectural fixes."
                ),
                "arguments": [
                    {
                        "name": "package_name",
                        "description": "Android package name to analyze (optional if set in env).",
                        "required": False,
                    },
                    {
                        "name": "top_n",
                        "description": "Number of top ANR clusters to inspect (default: 5).",
                        "required": False,
                    },
                ],
            },
            {
                "name": "verify-baseline-profile",
                "description": (
                    "Audit release performance comparing baseline vs. target version to verify "
                    "Baseline Profile cold-startup acceleration and ANR reductions."
                ),
                "arguments": [
                    {
                        "name": "baseline_version",
                        "description": "Older release versionCode before optimization.",
                        "required": True,
                    },
                    {
                        "name": "target_version",
                        "description": "Newer release versionCode with Baseline Profile enabled.",
                        "required": True,
                    },
                    {
                        "name": "package_name",
                        "description": "Android package name (optional if set in env).",
                        "required": False,
                    },
                ],
            },
            {
                "name": "vitals-weekly-report",
                "description": (
                    "Generate a comprehensive markdown report summarizing weekly Android Vitals trends "
                    "(ANR rate, crash rate, slow cold start rate)."
                ),
                "arguments": [
                    {
                        "name": "package_name",
                        "description": "Android package name (optional if set in env).",
                        "required": False,
                    },
                    {
                        "name": "days",
                        "description": "Days to analyze (default: 7).",
                        "required": False,
                    },
                ],
            },
        ]

    def dispatch_prompt(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Generate structured prompt messages based on prompt template."""
        pkg = (
            arguments.get("package_name") or self.client.default_package_name or "YOUR_PACKAGE_NAME"
        )
        if name == "analyze-anr-incident":
            top_n = arguments.get("top_n", 5)
            instruction = (
                f"Please conduct an in-depth ANR triage for package '{pkg}':\n"
                f"1. Use `play_get_top_anr_summary` with limit={top_n} to pull the highest impact ANR clusters and sample stack traces.\n"
                f"2. Categorize the root cause for each issue (e.g., Disk I/O, Lock Contention, Main-thread Crypto, Heavy Initialization).\n"
                f"3. Provide actionable code remediation proposals (e.g., Async pre-warming, Background Dispatch, Lazy Loading).\n"
                f"4. Format the final output into a clear, professional technical summary table."
            )
            return {
                "description": f"ANR Incident Analysis for {pkg}",
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": instruction},
                    }
                ],
            }
        elif name == "verify-baseline-profile":
            v_base = arguments.get("baseline_version")
            v_target = arguments.get("target_version")
            instruction = (
                f"Please verify Baseline Profile release performance for package '{pkg}':\n"
                f"1. Call `play_compare_versions` with metric_type='STARTUP', baseline_version={v_base}, target_version={v_target}.\n"
                f"2. Call `play_compare_versions` with metric_type='ANR', baseline_version={v_base}, target_version={v_target}.\n"
                f"3. Quantify the relative percentage improvements in slow cold start rates and user-perceived ANRs.\n"
                f"4. Conclude whether the Baseline Profile rules have successfully accelerated app cold startup in production."
            )
            return {
                "description": f"Baseline Profile Verification ({v_base} vs {v_target})",
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": instruction},
                    }
                ],
            }
        elif name == "vitals-weekly-report":
            days = arguments.get("days", 7)
            instruction = (
                f"Please generate a comprehensive Android Vitals weekly stability report for package '{pkg}':\n"
                f"1. Query `play_get_metric_trends` for 'ANR' over the past {days} days.\n"
                f"2. Query `play_get_metric_trends` for 'CRASH' over the past {days} days.\n"
                f"3. Query `play_get_metric_trends` for 'STARTUP' over the past {days} days.\n"
                f"4. Synthesize the findings into an executive markdown dashboard with daily trend analysis and health grades."
            )
            return {
                "description": f"Weekly Stability Report for {pkg}",
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": instruction},
                    }
                ],
            }
        else:
            raise ValueError(f"Unknown prompt template: '{name}'")

    # ==========================================================================
    # 3. MCP Resources Schema & Definitions
    # ==========================================================================

    def get_resource_definitions(self) -> list[dict[str, Any]]:
        """Return read-only MCP resources providing contextual metadata."""
        return [
            {
                "uri": "vitals://status",
                "name": "Google Play Vitals System & Environment Status",
                "description": "Real-time diagnostic overview of dependencies, active package configuration, and GCP credentials.",
                "mimeType": "application/json",
            }
        ]

    def read_resource(self, uri: str) -> dict[str, Any]:
        """Read and return contextual resource contents."""
        if uri == "vitals://status":
            status_data = self.handle_check_status({})
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(status_data, indent=2, ensure_ascii=False),
            }
        else:
            raise ValueError(f"Resource URI not found: '{uri}'")

    # ==========================================================================
    # 4. Tool Execution Handlers
    # ==========================================================================

    def handle_check_status(self, args: dict[str, Any]) -> dict[str, Any]:
        cred_path = args.get("credentials_path") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        pkg_name = args.get("package_name") or os.environ.get("GOOGLE_PLAY_PACKAGE_NAME")

        deps_ok = True
        try:
            import google.auth  # noqa: F401
            import googleapiclient  # noqa: F401
        except ImportError:
            deps_ok = False

        key_exists = bool(cred_path and os.path.exists(os.path.expanduser(cred_path)))
        has_env_json = bool(os.environ.get("GOOGLE_PLAY_CREDENTIALS_JSON"))
        has_gcloud_adc = os.path.exists(
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
        )

        creds_ok = key_exists or has_env_json or has_gcloud_adc
        ready = deps_ok and creds_ok

        auth_type = "none"
        if has_env_json:
            auth_type = "service_account_json_env"
        elif key_exists:
            auth_type = "service_account_file"
        elif has_gcloud_adc:
            auth_type = "gcloud_adc"

        return {
            "status": "ready" if ready else "action_required",
            "server_version": self.server_version,
            "dependencies_installed": deps_ok,
            "credentials_configured": creds_ok,
            "auth_type": auth_type,
            "credentials_path": cred_path or "(none specified)",
            "credentials_json_env_present": has_env_json,
            "configured_package_name": pkg_name or "(none specified)",
            "capabilities_supported": ["tools", "prompts", "resources"],
            "setup_guide": (
                "Authentication setup:\n"
                "  1. Obtain a Google Cloud Service Account JSON key from your Google Play Console Account Owner.\n"
                "  2. Set environment variable: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json\n"
                "  3. Or pass credentials_json / GOOGLE_PLAY_CREDENTIALS_JSON='{...}'"
            ),
        }

    def handle_get_top_anr_summary(self, args: dict[str, Any]) -> dict[str, Any]:
        pkg = args.get("package_name")
        limit = args.get("limit", 5)
        cred_path = args.get("credentials_path")
        if cred_path:
            self.client.credentials_path = cred_path

        issues = self.client.search_error_issues(
            package_name=pkg, error_type="ANR", page_size=limit
        )

        clusters = []
        for issue in issues:
            issue_name = issue.get("name", "")
            title = issue.get("cause") or issue.get("location") or issue_name
            users = issue.get("distinctUsers", "0")
            count = issue.get("errorReportCount", "0")

            sample_stack = "No sample available"
            device_info = {}
            try:
                reports = self.client.search_error_reports(issue_name=issue_name, page_size=1)
                if reports:
                    cleaned = clean_stack_trace(reports[0])
                    sample_stack = cleaned["stack_trace"]
                    device_info = {
                        "device": cleaned["device"],
                        "android_api": cleaned["android_api"],
                        "event_time": cleaned["event_time"],
                    }
            except Exception as e:
                logger.warning("Failed to fetch sample stack for %s: %s", issue_name, e)

            clusters.append(
                {
                    "issue_id": issue_name.split("/")[-1] if "/" in issue_name else issue_name,
                    "issue_resource_name": issue_name,
                    "title": title,
                    "impacted_users": users,
                    "total_occurrences": count,
                    "device_info": device_info,
                    "sample_stack_trace": sample_stack,
                }
            )

        return {
            "package_name": self.client.resolve_package_name(pkg),
            "retrieved_clusters_count": len(clusters),
            "top_anr_clusters": clusters,
        }

    def handle_get_metric_trends(self, args: dict[str, Any]) -> dict[str, Any]:
        pkg = args.get("package_name")
        metric_type = args.get("metric_type", "ANR").upper()
        days = args.get("days", 7)
        version_code = args.get("version_code")
        cred_path = args.get("credentials_path")
        if cred_path:
            self.client.credentials_path = cred_path

        if metric_type == "ANR":
            raw = self.client.query_anr_rate(package_name=pkg, days=days, version_code=version_code)
            data = clean_rate_metrics(raw, "anrRate", "userPerceivedAnrRate")
        elif metric_type == "STARTUP":
            raw = self.client.query_startup_rate(
                package_name=pkg, days=days, version_code=version_code
            )
            data = clean_rate_metrics(raw, "slowStartRate", "userPerceivedSlowStartRate")
        elif metric_type == "CRASH":
            raw = self.client.query_crash_rate(
                package_name=pkg, days=days, version_code=version_code
            )
            data = clean_rate_metrics(raw, "crashRate", "userPerceivedCrashRate")
        else:
            raise ValueError(
                f"Unsupported metric_type: '{metric_type}'. Expected ANR, STARTUP, or CRASH."
            )

        return {
            "metric_type": metric_type,
            "package_name": self.client.resolve_package_name(pkg),
            "version_filter": version_code or "ALL_VERSIONS",
            "summary": data,
        }

    def handle_compare_versions(self, args: dict[str, Any]) -> dict[str, Any]:
        pkg = args.get("package_name")
        ver_a = args.get("baseline_version")
        ver_b = args.get("target_version")
        metric_type = args.get("metric_type", "ANR").upper()
        days = args.get("days", 7)
        cred_path = args.get("credentials_path")
        if cred_path:
            self.client.credentials_path = cred_path

        if ver_a is None or ver_b is None:
            raise ValueError("Both baseline_version and target_version are required.")

        res_a = self.handle_get_metric_trends(
            {
                "package_name": pkg,
                "metric_type": metric_type,
                "days": days,
                "version_code": ver_a,
            }
        )
        res_b = self.handle_get_metric_trends(
            {
                "package_name": pkg,
                "metric_type": metric_type,
                "days": days,
                "version_code": ver_b,
            }
        )

        summary_a = res_a.get("summary", {})
        summary_b = res_b.get("summary", {})

        def parse_pct(val_str: str) -> float:
            try:
                return float(str(val_str).replace("%", "").strip())
            except (ValueError, TypeError):
                return 0.0

        rate_a = parse_pct(summary_a.get("avg_user_perceived_rate", "0"))
        rate_b = parse_pct(summary_b.get("avg_user_perceived_rate", "0"))

        delta = rate_b - rate_a
        pct_improvement = ((rate_a - rate_b) / rate_a * 100) if rate_a > 0 else 0.0

        return {
            "package_name": self.client.resolve_package_name(pkg),
            "metric_compared": metric_type,
            "baseline_version": {
                "version": ver_a,
                "user_perceived_rate": f"{rate_a:.2f}%",
            },
            "target_version": {
                "version": ver_b,
                "user_perceived_rate": f"{rate_b:.2f}%",
            },
            "delta": f"{delta:+.2f}%",
            "relative_improvement": (
                f"{pct_improvement:.1f}% ({'IMPROVEMENT' if pct_improvement > 0 else 'REGRESSION/NEUTRAL'})"
            ),
            "verdict": (
                f"Target version {ver_b} improved {metric_type} by {pct_improvement:.1f}% compared to {ver_a}."
                if pct_improvement > 0
                else f"Target version {ver_b} has {abs(pct_improvement):.1f}% neutral or increased {metric_type} rate."
            ),
        }

    def handle_get_raw_error_reports(self, args: dict[str, Any]) -> dict[str, Any]:
        issue_name = args.get("issue_name")
        if not issue_name:
            raise ValueError("Parameter 'issue_name' is required.")
        page_size = args.get("page_size", 3)
        cred_path = args.get("credentials_path")
        if cred_path:
            self.client.credentials_path = cred_path

        reports = self.client.search_error_reports(issue_name=issue_name, page_size=page_size)
        cleaned_list = [clean_stack_trace(r) for r in reports]

        return {
            "issue_name": issue_name,
            "reports_count": len(cleaned_list),
            "sample_reports": cleaned_list,
        }

    # ==========================================================================
    # 5. Dispatcher
    # ==========================================================================

    def dispatch_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return JSON-serializable dictionary."""
        if name == "play_check_status":
            return self.handle_check_status(arguments)
        elif name == "play_get_top_anr_summary":
            return self.handle_get_top_anr_summary(arguments)
        elif name == "play_get_metric_trends":
            return self.handle_get_metric_trends(arguments)
        elif name == "play_compare_versions":
            return self.handle_compare_versions(arguments)
        elif name == "play_get_raw_error_reports":
            return self.handle_get_raw_error_reports(arguments)
        else:
            raise ValueError(f"Unknown tool: '{name}'")

    def _format_error_payload(self, e: Exception) -> dict[str, Any]:
        """Convert runtime exceptions into actionable, diagnostic JSON payloads."""
        err_str = str(e)
        if (
            "requires a quota project" in err_str
            or "PERMISSION_DENIED" in err_str
            or "403" in err_str
        ):
            return {
                "error_code": "PERMISSION_OR_QUOTA_ERROR",
                "message": (
                    "Google Play Reporting API requires a valid GCP Service Account authorized with "
                    "'View app quality data' read-only permission."
                ),
                "guidance": (
                    "To resolve: Ask your Google Play Console Account Owner to create a Service Account, "
                    "grant 'View app quality data' permission in API access, and export the JSON key.\n"
                    "Then set: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json"
                ),
                "raw_error": err_str,
            }
        return {"error": err_str}

    # ==========================================================================
    # 6. Standard MCP JSON-RPC 2.0 stdio Loop
    # ==========================================================================

    def run_stdio(self) -> None:
        """Run the MCP server listening on stdin and responding on stdout."""
        logger.info(
            "Starting %s v%s (Model Context Protocol stdio transport)...",
            self.server_name,
            self.server_version,
        )

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
                continue

            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            # ------------------------------------------------------------------
            # Lifecycle: initialize & notifications
            # ------------------------------------------------------------------
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "prompts": {"listChanged": False},
                            "resources": {"listChanged": False},
                        },
                        "serverInfo": {
                            "name": self.server_name,
                            "version": self.server_version,
                        },
                    },
                }
            elif method == "notifications/initialized":
                continue
            elif method == "ping":
                response = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            # ------------------------------------------------------------------
            # Tools API
            # ------------------------------------------------------------------
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": self.get_tool_definitions(),
                    },
                }
            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                try:
                    tool_output = self.dispatch_tool(tool_name, tool_args)
                    formatted_text = json.dumps(tool_output, indent=2, ensure_ascii=False)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": formatted_text,
                                }
                            ]
                        },
                    }
                except Exception as e:
                    logger.exception("Error executing tool %s", tool_name)
                    err_payload = self._format_error_payload(e)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(err_payload, indent=2, ensure_ascii=False),
                                }
                            ],
                            "isError": True,
                        },
                    }

            # ------------------------------------------------------------------
            # Prompts API
            # ------------------------------------------------------------------
            elif method == "prompts/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "prompts": self.get_prompt_definitions(),
                    },
                }
            elif method == "prompts/get":
                prompt_name = params.get("name", "")
                prompt_args = params.get("arguments", {})
                try:
                    prompt_result = self.dispatch_prompt(prompt_name, prompt_args)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": prompt_result,
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32602,
                            "message": f"Prompt error: {str(e)}",
                        },
                    }

            # ------------------------------------------------------------------
            # Resources API
            # ------------------------------------------------------------------
            elif method == "resources/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "resources": self.get_resource_definitions(),
                    },
                }
            elif method == "resources/read":
                res_uri = params.get("uri", "")
                try:
                    res_content = self.read_resource(res_uri)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "contents": [res_content],
                        },
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32602,
                            "message": f"Resource error: {str(e)}",
                        },
                    }

            # ------------------------------------------------------------------
            # Fallback for Unknown Methods
            # ------------------------------------------------------------------
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found",
                    },
                }

            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def main() -> None:
    server = GooglePlayVitalsMCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()
