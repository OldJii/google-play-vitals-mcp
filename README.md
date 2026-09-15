# Google Play Vitals MCP Server

[![PyPI version](https://badge.fury.io/py/google-play-vitals-mcp.svg)](https://pypi.org/project/google-play-vitals-mcp/)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/google-play-vitals-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-blue.svg)](https://modelcontextprotocol.io/)
[![CI](https://github.com/OldJii/google-play-vitals-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/OldJii/google-play-vitals-mcp/actions/workflows/ci.yml)

**Google Play Vitals MCP** is a high-performance, token-efficient [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for the **Google Play Developer Reporting API (Android Vitals)**.

Designed specifically for AI coding assistants and autonomous agents (**Cursor**, **Claude Desktop**, **Claude Code**, **Codex**, **Windsurf**, and **Cline**), it empowers AI to analyze Android production stability, diagnose ANRs (Application Not Responding), track crash trends, inspect de-obfuscated call stacks, and verify startup optimizations (such as **AndroidX Baseline Profiles**) with minimal context token consumption.

---

## 🌟 Key Highlights

- **Full-Spectrum Atomic Architecture**: Complete, orthogonal coverage of Google Play Developer Reporting API endpoints (Viewer scope) — release track discovery, AIP-160 error cluster search, stack drilldown, and anomaly monitoring.
- **Autonomous Chained Workflows**: Empowers AI agents to autonomously identify the active production release, retrieve top Crash/ANR issues, and drill down into de-obfuscated stack traces in a natural chain without hardcoded assumptions.
- **Token Economy by Design (Token Saver)**: Upstream Google Developer Reporting APIs return deeply nested, verbose Protobuf responses. Our built-in compression engine strips 80%+ redundant metadata and automatically reassembles raw frame data into clean, single-line standard Java stack traces (`at com.example.Foo.bar(Foo.java:42)`).
- **Version Comparative Analysis (`play_compare_versions`)**: Quantifies release optimizations. Compare before-and-after versions (e.g. verifying ANR governance or Baseline Profile cold-start acceleration) with automated delta calculation and percentage improvement reporting.
- **Universal & Production Decoupled**: Zero proprietary hardcoding. Supports any Android package, dynamic runtime parameters, environment variables, Service Account JSON files, JSON strings, or Google Application Default Credentials (ADC).
- **Zero-Latency In-Memory Hot Cache**: Built-in 5-minute LRU cache prevents accidental quota exhaustion during multi-step AI reasoning.
- **Broad Agent Compatibility**: Works out of the box with Cursor, Claude Desktop, Claude Code, Windsurf, Codex, and standard MCP JSON-RPC 2.0 stdio clients.

---

## 🛠️ MCP Tools Overview

### 1. Release & App Discovery

| Tool Name | Type | Description |
| :--- | :---: | :--- |
| **`play_get_release_tracks`** | Release Discovery | Fetches active release tracks (`PRODUCTION`, `BETA`, `ALPHA`, `INTERNAL`) and serving releases with their release names and `versionCodes`. Essential for discovering latest stable releases. |
| **`play_list_accessible_apps`** | App Discovery | Lists all Google Play applications accessible by the configured GCP Service Account. |

### 2. Error Issues & Stack Traces

| Tool Name | Type | Description |
| :--- | :---: | :--- |
| **`play_search_error_issues`** | Issue Search | Searches error clusters (`CRASH`, `ANR`, or `NON_FATAL`) with full AIP-160 filter support (`versionCode`, `isUserPerceived`, `appProcessState`, `custom_filter`). Sorted by user impact and occurrences. |
| **`play_get_error_reports`** | Deep Drilldown | Fetches multi-device environmental samples and cleaned, de-obfuscated stack traces for an issue ID or resource name. |
| **`play_get_top_anr_summary`** | Quick Triage | One-shot aggregator for top ANR clusters and sample main-thread stack traces. |
| **`play_get_raw_error_reports`** | Raw Reports | Retrieves raw error reports and multi-device environment samples for an issue. |

### 3. Vitals Metrics & Analytics

| Tool Name | Type | Description |
| :--- | :---: | :--- |
| **`play_get_metric_trends`** | Metrics | Queries historical daily trends and overall averages for **`ANR`**, **`STARTUP`** (slow cold starts), or **`CRASH`** with optional version code filters. |
| **`play_compare_versions`** | Analytics | Compares metrics between two app versions (e.g. baseline `100` vs target `101`) and computes net percentage improvement. |

### 4. Monitoring & Diagnostics

| Tool Name | Type | Description |
| :--- | :---: | :--- |
| **`play_list_anomalies`** | Anomaly Monitor | Retrieves sudden metric spikes and regression alerts detected by Google Play algorithms. |
| **`play_check_status`** | Diagnostics | Self-tests Python dependencies, GCP Service Account key presence, and environment readiness. |

---

### 📝 MCP Prompts & Resources

| Capability | Name / URI | Purpose |
| :--- | :--- | :--- |
| **Prompt** | `analyze-anr-incident` | Interactive prompt guiding AI to perform root-cause triage and generate architectural fixes. |
| **Prompt** | `verify-baseline-profile` | Automated audit prompt comparing release versions to quantify cold-start acceleration and ANR reductions. |
| **Prompt** | `vitals-weekly-report` | Executive prompt generating a weekly Android stability markdown dashboard. |
| **Resource** | `vitals://status` | Read-only JSON resource reporting connection health, credentials presence, and active configuration. |

---

## 🚀 Quick Start

### 1. Installation

**Option A: Install via pip or uv**
```bash
pip install google-play-vitals-mcp
# or
uv pip install google-play-vitals-mcp
```

**Option B: One-click Install via Smithery (Cursor / Windsurf / Claude)**
```bash
npx -y @smithery/cli install google-play-vitals-mcp --client cursor
```

**Option C: Docker Container**
```bash
docker run -i --rm -v ~/.config/gcp:/gcp -e GOOGLE_APPLICATION_CREDENTIALS=/gcp/key.json google-play-vitals-mcp
```

### 2. Authentication & Credentials

Google Play Developer Reporting API requires enterprise authentication via a **Google Cloud Service Account** authorized with "View app quality data" read-only permission:

**Option A: Google Cloud Service Account JSON Key (Standard)**
1. Ask your Google Play Console administrator (Account Owner) for a Service Account JSON key with "View app quality data" read-only permission.
2. Set the environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/play_service_account.json"
   ```

**Option B: CI/CD Plaintext JSON**
```bash
export GOOGLE_PLAY_CREDENTIALS_JSON='{"type": "service_account", "project_id": "..."}'
```

---

## 🤖 AI Client Integration Guides

### 1. Cursor

Add to your project's `.cursor/mcp.json` or global Cursor settings:

```json
{
  "mcpServers": {
    "google-play-vitals": {
      "command": "google-play-vitals-mcp",
      "args": [],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/play_service_account.json",
        "GOOGLE_PLAY_PACKAGE_NAME": "com.yourcompany.app"
      }
    }
  }
}
```

*Note: You can also run with `python -m google_play_vitals_mcp` if installed in a specific virtual environment.*

### 2. Claude Desktop

Add to your `claude_desktop_config.json`:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "google-play-vitals": {
      "command": "google-play-vitals-mcp",
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/play_service_account.json",
        "GOOGLE_PLAY_PACKAGE_NAME": "com.yourcompany.app"
      }
    }
  }
}
```

### 3. Claude Code CLI

Add the MCP server directly via CLI:

```bash
claude mcp add google-play-vitals -- \
  google-play-vitals-mcp \
  --package-name com.yourcompany.app \
  --credentials /path/to/play_service_account.json
```

### 4. Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "google-play-vitals": {
      "command": "google-play-vitals-mcp",
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/play_service_account.json",
        "GOOGLE_PLAY_PACKAGE_NAME": "com.yourcompany.app"
      }
    }
  }
}
```

---

## 💡 Prompt Examples

Once configured, simply talk to your AI assistant:

- *"Find the top 10 Crashes and ANRs for our latest production release, along with de-obfuscated stack traces."*
- *"Check Google Play Vitals connection status."*
- *"Analyze the top ANR clusters in production right now and show me the problematic stack traces."*
- *"Show me the daily ANR rate and slow startup rate for the last 14 days."*
- *"Compare version 204000 against version 203000 to verify if our Baseline Profile and ANR fixes improved cold startup and reduced ANRs."*
- *"Inspect issue apps/com.example/errorIssues/123456 and retrieve the raw device reports."*

---

## 💻 CLI Commands

The package includes a built-in CLI:

```bash
# Check configuration and credentials readiness
google-play-vitals-mcp check -p com.example.app -c /path/to/key.json

# Launch MCP stdio server manually
google-play-vitals-mcp run -p com.example.app

# Check version
google-play-vitals-mcp --version
```

---

## 🔧 Environment Variables

| Variable | Description |
| :--- | :--- |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Google Cloud Service Account JSON key file. |
| `GOOGLE_PLAY_CREDENTIALS_JSON` | Raw JSON string of Service Account credentials (useful for CI/CD or Cloud runtimes). |
| `GOOGLE_PLAY_PACKAGE_NAME` | Default Android application package name (e.g. `com.example.app`). |
| `GOOGLE_PLAY_CACHE_TTL` | Cache duration in seconds (default: `300`). |

---

## 🧪 Development & Testing

```bash
# Clone repository
git clone https://github.com/OldJii/google-play-vitals-mcp.git
cd google-play-vitals-mcp

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run unit tests
pytest -v

# Run linting
ruff check .
ruff format --check .
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
