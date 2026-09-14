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
                    "No valid Google Cloud Service Account credentials found.\n"
                    "Please set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json\n"
                    "or provide credentials_json / GOOGLE_PLAY_CREDENTIALS_JSON."
                ) from e

        quota_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GOOGLE_QUOTA_PROJECT"
        )
        if quota_project and hasattr(creds, "with_quota_project"):
            try:
                creds = creds.with_quota_project(quota_project)
            except Exception as e:
                logger.debug("Failed to set quota project %s: %s", quota_project, e)

        self._service = build(
            "playdeveloperreporting",
            "v1beta1",
            credentials=creds,
            cache_discovery=False,
        )
        return self._service

    def build_timeline_spec(self, days: int) -> dict[str, Any]:
        """
        Construct a timeline spec for daily aggregation over the past N days.
        Note: Google Play Vitals API has a 1-2 day freshness lag, so end_date is set to T-2 days.
        """
        end_date = datetime.utcnow().date() - timedelta(days=2)
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
        dimensions = ["startType"]
        filters = ['startType = "COLD"']
        if version_code:
            dimensions.append("versionCode")
            filters.append(f"versionCode = {version_code}")

        body: dict[str, Any] = {
            "timelineSpec": self.build_timeline_spec(days),
            "dimensions": dimensions,
            "filter": " AND ".join(filters),
            "metrics": [
                "slowStartRate",
                "slowStartRate7dUserWeighted",
                "distinctUsers",
            ],
        }

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

    def fetch_release_tracks(self, package_name: str | None = None) -> dict[str, Any]:
        """Fetch release tracks and active serving releases from Google Play."""
        pkg = self.resolve_package_name(package_name)
        cache_key = f"tracks_{pkg}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        resp = service.apps().fetchReleaseFilterOptions(name=f"apps/{pkg}").execute()
        self.cache.set(cache_key, resp)
        return resp

    def search_error_issues(
        self,
        package_name: str | None = None,
        error_type: str = "ANR",
        version_code: int | None = None,
        is_user_perceived: bool | None = None,
        app_process_state: str | None = None,
        custom_filter: str | None = None,
        page_size: int = 10,
        page_token: str | None = None,
        raw_response: bool = False,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """
        Search error issue clusters with full AIP-160 filter support (versionCode, processState, etc.).
        """
        pkg = self.resolve_package_name(package_name)
        cache_key = (
            f"issues_{pkg}_{error_type}_{version_code}_{is_user_perceived}_"
            f"{app_process_state}_{custom_filter}_{page_size}_{page_token}_{raw_response}"
        )
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        clauses: list[str] = []
        if error_type:
            clauses.append(f"errorIssueType = {error_type.upper()}")
        if version_code is not None:
            clauses.append(f"versionCode = {version_code}")
        if is_user_perceived is True:
            clauses.append("isUserPerceived")
        if app_process_state:
            clauses.append(f"appProcessState = {app_process_state.upper()}")
        if custom_filter:
            clauses.append(f"({custom_filter.strip()})")

        filter_expr = " AND ".join(clauses) if clauses else None

        service = self.get_service()
        kwargs: dict[str, Any] = {
            "parent": f"apps/{pkg}",
            "pageSize": page_size,
        }
        if filter_expr:
            kwargs["filter"] = filter_expr
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.vitals().errors().issues().search(**kwargs).execute()

        result = resp if raw_response else resp.get("errorIssues", [])
        self.cache.set(cache_key, result)
        return result

    def search_error_reports(
        self,
        issue_name: str,
        page_size: int = 3,
        page_token: str | None = None,
        package_name: str | None = None,
        raw_response: bool = False,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Search individual raw error reports and stack traces for a given issue."""
        cache_key = f"reports_{issue_name}_{page_size}_{page_token}_{raw_response}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Derive parent 'apps/{app}' format required by Google Play Reporting API
        parent_app = None
        if issue_name.startswith("apps/"):
            parts = issue_name.split("/")
            if len(parts) >= 2:
                parent_app = f"apps/{parts[1]}"

        if not parent_app:
            pkg = self.resolve_package_name(package_name)
            parent_app = f"apps/{pkg}"

        # Extract issue ID for filter: AIP-160 requires errorIssueId = "..."
        issue_id = issue_name.split("/")[-1]

        service = self.get_service()
        kwargs: dict[str, Any] = {
            "parent": parent_app,
            "filter": f'errorIssueId = "{issue_id}"',
            "pageSize": page_size,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.vitals().errors().reports().search(**kwargs).execute()

        result = resp if raw_response else resp.get("errorReports", [])
        self.cache.set(cache_key, result)
        return result

    def list_anomalies(
        self,
        package_name: str | None = None,
        page_size: int = 10,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List metric anomalies detected by Google Play."""
        pkg = self.resolve_package_name(package_name)
        cache_key = f"anomalies_{pkg}_{page_size}_{page_token}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        kwargs: dict[str, Any] = {
            "parent": f"apps/{pkg}",
            "pageSize": page_size,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.anomalies().list(**kwargs).execute()
        self.cache.set(cache_key, resp)
        return resp

    def list_accessible_apps(
        self,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List accessible applications for the authenticated service account."""
        cache_key = f"apps_{page_size}_{page_token}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        service = self.get_service()
        kwargs: dict[str, Any] = {"pageSize": page_size}
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.apps().search(**kwargs).execute()
        self.cache.set(cache_key, resp)
        return resp

