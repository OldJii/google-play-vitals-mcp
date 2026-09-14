"""
Universal Google Play Developer Reporting API Client
Handles authentication via Service Account files, JSON strings, or Application Default Credentials (ADC).
Includes memory caching to prevent quota limits.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("google_play_vitals_mcp.client")

SCOPES = ["https://www.googleapis.com/auth/playdeveloperreporting"]


class VitalsCache:
    """Simple thread-safe in-memory cache with TTL."""

    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Any | None:
        now = time.time()
        if key in self._cache:
            val, expire_at = self._cache[key]
            if now < expire_at:
                return val
            del self._cache[key]
        return None

    def set(self, key: str, val: Any, ttl: int | None = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        self._cache[key] = (val, time.time() + duration)

    def clear(self) -> None:
        self._cache.clear()


class GooglePlayVitalsClient:
    """Universal client for Google Play Developer Reporting API."""

    def __init__(
        self,
        credentials_path: str | None = None,
        credentials_json: str | None = None,
        default_package_name: str | None = None,
        cache_ttl: int = 300,
    ):
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.default_package_name = default_package_name or os.environ.get(
            "GOOGLE_PLAY_PACKAGE_NAME"
        )
        self.cache = VitalsCache(default_ttl_seconds=cache_ttl)
        self._service: Any | None = None

    def resolve_package_name(self, package_name: str | None) -> str:
        target = package_name or self.default_package_name
        if not target:
            raise ValueError(
                "Package name is required. Specify 'package_name' parameter or set "
                "'GOOGLE_PLAY_PACKAGE_NAME' environment variable."
            )
        return target.strip()

    def get_service(self) -> Any:
        """Initialize or return the cached Google Developer Reporting API service."""
        if self._service is not None:
            return self._service

        try:
            import google.auth
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as e:
            raise ImportError(
                "Missing required Google client libraries. "
                "Install via: pip install 'google-play-vitals-mcp' or pip install google-api-python-client google-auth"
            ) from e

        creds = None

        # Priority 1: Raw JSON string from parameter or environment variable
        raw_json = self.credentials_json or os.environ.get("GOOGLE_PLAY_CREDENTIALS_JSON")
        if raw_json:
            try:
                info = json.loads(raw_json)
                creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            except Exception as e:
                raise ValueError(f"Failed to parse credentials from JSON string: {e}") from e

        # Priority 2: File path from parameter or GOOGLE_APPLICATION_CREDENTIALS
        if creds is None:
            file_path = self.credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if file_path:
                expanded_path = os.path.expanduser(file_path)
                if not os.path.exists(expanded_path):
                    raise FileNotFoundError(
                        f"GCP Service Account credential file not found at: {expanded_path}"
                    )
                try:
                    creds = service_account.Credentials.from_service_account_file(
                        expanded_path, scopes=SCOPES
                    )
                except Exception as e:
                    raise ValueError(
                        f"Failed to load credentials from file {expanded_path}: {e}"
                    ) from e

        # Priority 3: Google Application Default Credentials (ADC)
        if creds is None:
            try:
                creds, _ = google.auth.default(scopes=SCOPES)
            except Exception as e:
                raise ValueError(
                    "No valid Google Cloud credentials found. Please provide credentials_path, "
                    "credentials_json, or configure GOOGLE_APPLICATION_CREDENTIALS."
                ) from e

        self._service = build(
            "playdeveloperreporting",
            "v1beta1",
            credentials=creds,
            cache_discovery=False,
        )
        return self._service

    def build_timeline_spec(self, days: int) -> dict[str, Any]:
        """Construct a timeline spec for daily aggregation over the past N days."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        return {
            "aggregationPeriod": "DAILY",
            "startTime": {
                "year": start_date.year,
                "month": start_date.month,
                "day": start_date.day,
            },
            "endTime": {
                "year": end_date.year,
                "month": end_date.month,
                "day": end_date.day,
            },
        }

    def query_anr_rate(
        self,
        package_name: str | None = None,
        days: int = 7,
        version_code: int | None = None,
    ) -> dict[str, Any]:
        """Query ANR rate metrics."""
        pkg = self.resolve_package_name(package_name)
        cache_key = f"anr_rate_{pkg}_{days}_{version_code}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        body: dict[str, Any] = {
            "timelineSpec": self.build_timeline_spec(days),
            "metrics": ["anrRate", "userPerceivedAnrRate", "distinctUsers"],
        }
        if version_code:
            body["dimensions"] = ["versionCode"]
            body["filter"] = f"versionCode = {version_code}"

        result = (
            service.vitals()
            .anrrate()
            .query(name=f"apps/{pkg}/anrRateMetricSet", body=body)
            .execute()
        )
        self.cache.set(cache_key, result)
        return result

    def query_startup_rate(
        self,
        package_name: str | None = None,
        days: int = 7,
        version_code: int | None = None,
    ) -> dict[str, Any]:
        """Query slow cold start rate metrics (Baseline Profile verification)."""
        pkg = self.resolve_package_name(package_name)
        cache_key = f"startup_rate_{pkg}_{days}_{version_code}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        body: dict[str, Any] = {
            "timelineSpec": self.build_timeline_spec(days),
            "metrics": [
                "slowStartRate",
                "userPerceivedSlowStartRate",
                "distinctUsers",
            ],
        }
        if version_code:
            body["dimensions"] = ["versionCode"]
            body["filter"] = f"versionCode = {version_code}"

        result = (
            service.vitals()
            .slowstartrate()
            .query(name=f"apps/{pkg}/slowStartRateMetricSet", body=body)
            .execute()
        )
        self.cache.set(cache_key, result)
        return result

    def query_crash_rate(
        self,
        package_name: str | None = None,
        days: int = 7,
        version_code: int | None = None,
    ) -> dict[str, Any]:
        """Query crash rate metrics."""
        pkg = self.resolve_package_name(package_name)
        cache_key = f"crash_rate_{pkg}_{days}_{version_code}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        body: dict[str, Any] = {
            "timelineSpec": self.build_timeline_spec(days),
            "metrics": ["crashRate", "userPerceivedCrashRate", "distinctUsers"],
        }
        if version_code:
            body["dimensions"] = ["versionCode"]
            body["filter"] = f"versionCode = {version_code}"

        result = (
            service.vitals()
            .crashrate()
            .query(name=f"apps/{pkg}/crashRateMetricSet", body=body)
            .execute()
        )
        self.cache.set(cache_key, result)
        return result

    def search_error_issues(
        self,
        package_name: str | None = None,
        error_type: str = "ANR",
        page_size: int = 5,
    ) -> list[dict[str, Any]]:
        """Search top error issues clusters."""
        pkg = self.resolve_package_name(package_name)
        cache_key = f"issues_{pkg}_{error_type}_{page_size}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        resp = (
            service.vitals()
            .errors()
            .issues()
            .search(
                parent=f"apps/{pkg}",
                filter=f"errorReportType = {error_type.upper()}",
                pageSize=page_size,
            )
            .execute()
        )
        issues = resp.get("errorIssues", [])
        self.cache.set(cache_key, issues)
        return issues

    def search_error_reports(self, issue_name: str, page_size: int = 3) -> list[dict[str, Any]]:
        """Search individual raw error reports and stack traces for a given issue."""
        cache_key = f"reports_{issue_name}_{page_size}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        resp = (
            service.vitals()
            .errors()
            .reports()
            .search(parent=issue_name, pageSize=page_size)
            .execute()
        )
        reports = resp.get("errorReports", [])
        self.cache.set(cache_key, reports)
        return reports
