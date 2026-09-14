# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-09-14

### Changed
- **Enterprise Service Account Focus**: Streamlined authentication to adhere strictly to Google Play Developer Reporting API enterprise requirements (GCP Service Account with "View app quality data" read-only access). Removed experimental personal OAuth2 browser flows that cannot bypass enterprise Quota Project and app-level permission gates.
- **Google AIP-160 Compliance**: Fixed `search_error_reports` parameter structuring to automatically separate `parent` (`apps/{app}`) and issue filters, preventing HTTP 400 Bad Request parameter mismatches.
- **Actionable Error Diagnostics**: Enhanced error payloads with clear, direct instructions for creating and linking Google Cloud Service Account JSON keys.

## [1.0.0] - 2026-09-14

### Added
- **LLM-Optimized MCP Server**: Full implementation conforming to the Model Context Protocol (JSON-RPC 2.0 stdio & Streamable HTTP compatible).
- **Token Saver Engine**: High-efficiency data cleaning module reducing Google Protobuf payload by 80%+ into clean Java single-line stack traces.
- **5 High-Level MCP Tools**:
  - `play_check_status`: Check dependency and GCP Service Account credential status with diagnostic guidance.
  - `play_get_top_anr_summary`: One-shot aggregation returning Top ANR clusters, affected users, counts, and representative main-thread call stacks.
  - `play_get_metric_trends`: Query historical trends and daily averages for ANR, CRASH, and STARTUP (Baseline Profile verification) metrics.
  - `play_compare_versions`: Two-version comparative analysis calculating percentage changes in ANRs and slow start rates.
  - `play_get_raw_error_reports`: Deep-dive retrieval of multi-device environments and full stack traces for specific issues.
- **Universal Google Play Client**: Supporting credentials via arguments, `GOOGLE_APPLICATION_CREDENTIALS`, raw JSON strings, and Google Application Default Credentials (ADC).
- **Resilient Caching**: In-memory LRU cache with configurable TTL (default: 5 minutes) preventing Google API rate limiting.
- **Modern CLI**: `google-play-vitals-mcp` command-line interface supporting `run`, `check`, and version inspection.
- **GitHub Actions**: Automated CI testing across Python 3.10-3.13 and automated PyPI Trusted Publishing.
