# Google Play Vitals MCP Server

[![PyPI version](https://img.shields.io/pypi/v/google-play-vitals-mcp.svg)](https://pypi.org/project/google-play-vitals-mcp/)
[![Python Version](https://img.shields.io/pypi/pyversions/google-play-vitals-mcp.svg)](https://pypi.org/project/google-play-vitals-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-blue.svg)](https://modelcontextprotocol.io/)
[![CI](https://github.com/OldJii/google-play-vitals-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/OldJii/google-play-vitals-mcp/actions/workflows/ci.yml)

> English | [简体中文](README_CN.md)

**Google Play Vitals MCP** is a high-performance, token-efficient [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for the **Google Play Developer Reporting API (Android Vitals)**.

Designed specifically for AI coding assistants and autonomous agents (**Cursor**, **Claude Desktop**, **Claude Code**, **Codex**, **Windsurf**, and **Cline**), it empowers AI to analyze Android production stability, diagnose ANRs (Application Not Responding), track crash trends, and verify startup optimizations (such as **AndroidX Baseline Profiles**) with minimal context token consumption.

---

## 🌟 Key Highlights

- **Token Economy by Design (Token Saver)**: Upstream Google Developer Reporting APIs return deeply nested, verbose Protobuf responses. Our built-in compression engine strips 80%+ redundant metadata and automatically reassembles raw frame data into clean, single-line standard Java stack traces (`at com.example.Foo.bar(Foo.java:42)`).
- **One-Shot Comprehensive Diagnosis (`play_get_top_anr_summary`)**: Eliminates the frustration of multi-turn tool roundtrips. A single tool call aggregates Top ANR clusters, affected user counts, occurrence numbers, and their representative de-obfuscated main thread stack traces.
- **Version Comparative Analysis (`play_compare_versions`)**: Specifically designed for quantifying release optimizations. Compare before-and-after versions (e.g., verifying ANR governance or Baseline Profile cold-start acceleration) with automated delta calculation and percentage improvement reporting.
- **Universal & Production Decoupled**: Zero proprietary hardcoding. Supports any Android package, dynamic runtime parameters, environment variables, Service Account JSON files, JSON strings, or Google Application Default Credentials (ADC).
- **Zero-Latency In-Memory Hot Cache**: Built-in 5-minute LRU cache prevents accidental quota exhaustion during multi-step AI reasoning.
- **Broad Agent Compatibility**: Works out of the box with Cursor, Claude Desktop, Claude Code, Windsurf, Codex, and standard MCP JSON-RPC 2.0 stdio clients.

---

## 🛠️ MCP Tools Overview

| Tool Name | Type | Description |
| :--- | :---: | :--- |
| **`play_check_status`** | Diagnostics | Self-tests Python dependencies, GCP Service Account key presence, and environment readiness. |
| **`play_get_top_anr_summary`** | **Core Diagnosis** | Aggregates Top ANR clusters, user volume, impact count, and representative main-thread call stacks in a single invocation. |
| **`play_get_metric_trends`** | Metrics | Queries historical daily trends and overall averages for **`ANR`**, **`STARTUP`** (slow cold starts), or **`CRASH`** with optional version code filters. |
| **`play_compare_versions`** | Analytics | Compares metrics between two app versions (e.g. baseline `100` vs target `101`) and computes net percentage improvement. |
| **`play_get_raw_error_reports`** | Deep Drilldown | Retrieves detailed device environment metadata (OS version, device model, timestamp) and long stack traces for an issue. |

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

### 2. Google Cloud & Play Console Setup

To connect to your Android app's Play Vitals data:

1. Go to the **[Google Play Console](https://play.google.com/console)** -> **Setup** -> **API access**.
2. Link an existing **Google Cloud Project** or create a new one.
3. In the Service Accounts section, click **Create new service account** (or select an existing one).
4. Grant the Service Account the **"View app quality data (read-only)"** permission.
5. In the **Google Cloud Console**, navigate to **IAM & Admin** -> **Service Accounts**, select the account, go to the **Keys** tab, and generate a new **JSON key**.
6. Save the downloaded JSON key file securely (e.g., `~/.config/gcp/play_service_account.json`).

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
