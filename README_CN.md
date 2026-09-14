# Google Play Vitals MCP 服务端

[![PyPI version](https://img.shields.io/pypi/v/google-play-vitals-mcp.svg)](https://pypi.org/project/google-play-vitals-mcp/)
[![Python Version](https://img.shields.io/pypi/pyversions/google-play-vitals-mcp.svg)](https://pypi.org/project/google-play-vitals-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-blue.svg)](https://modelcontextprotocol.io/)
[![CI](https://github.com/your-username/google-play-vitals-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/google-play-vitals-mcp/actions/workflows/ci.yml)

> [English](README.md) | 简体中文

**Google Play Vitals MCP** 是一款专为 **Google Play Developer Reporting API (Android Vitals)** 打造的高性能、Token 极致优化的 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 服务端。

专为 AI 编码助手与智能体（**Cursor**、**Claude Desktop**、**Claude Code**、**Codex**、**Windsurf** 和 **Cline**）设计。让 AI 在消耗极少上下文 Token 的前提下，能够高效分析 Android 生产环境稳定性、诊断 ANR（应用无响应）、监控 Crash 崩溃趋势，并量化验证启动性能优化（例如 **AndroidX Baseline Profiles** 基准配置文件）的实际收益。

---

## 🌟 核心特性

- **极致的 Token 经济学设计 (Token Saver)**：Google 官方 Reporting API 返回极度冗长、多层嵌套的 Protobuf 数据。本服务内置数据提炼清洗引擎，自动剥离 80%+ 的冗余元数据，并将原生散落的堆栈帧拼接重塑为人类与 LLM 最易读的单行标准 Java 调用栈（`at com.example.Foo.bar(Foo.java:42)`）。
- **一站式聚合诊断 (`play_get_top_anr_summary`)**：彻底终结多次往返调用的低效痛点。单次 Tool 调用即可同时返回 Top ANR 错误簇名称、受影响人数、发生次数以及最具代表性的主线程真实调用栈。
- **双版本横评对比 (`play_compare_versions`)**：专为发版验收设计。传入发版前后两个版本号（如基线 `100` vs 目标 `101`），自动计算 ANR 率或冷启动耗时的升降百分比，直接输出治理成果判定。
- **通用解耦与开箱即用**：零业务硬编码，无缝适配任意 Android 应用。支持动态参数传递、环境变量注入、本地 JSON 密钥文件、JSON 字符串以及 Google ADC（Application Default Credentials）自适应凭证。
- **零网络延迟内存热缓存**：内置 5 分钟 LRU 缓存，秒级响应并杜绝大模型在多步推理分析过程中因高频请求而触发 Google API 配额超限。
- **广泛的 Agent 兼容性**：完美适配 Cursor、Claude Desktop、Claude Code、Windsurf 等任意支持标准 MCP JSON-RPC 2.0 stdio 的客户端。

---

## 🛠️ MCP 工具清单

| 工具名称 | 类型 | 功能定位 |
| :--- | :---: | :--- |
| **`play_check_status`** | 环境诊断 | 自检 Python 依赖完整性、GCP 密钥路径有效性及配置状态。 |
| **`play_get_top_anr_summary`** | **核心诊断** | 一键聚合获取当前线上 Top ANR 错误簇及其代表性主线程调用栈。 |
| **`play_get_metric_trends`** | 指标透视 | 查询 **`ANR`**、**`STARTUP`**（冷启动慢启动率，验证 Baseline Profile）或 **`CRASH`** 的精简历史趋势与平均值。 |
| **`play_compare_versions`** | 对比决策 | 传入两个版本号，自动横评计算指标升降百分比，直接输出优化或恶化结论。 |
| **`play_get_raw_error_reports`** | 样本下钻 | 查询特定 Issue 下多台设备的现场硬件参数与长堆栈详情。 |

---

## 🚀 快速上手

### 1. 安装

通过 `pip` 或 `uv` 一键安装：

```bash
pip install google-play-vitals-mcp
# 或
uv pip install google-play-vitals-mcp
```

### 2. Google Cloud 与 Play Console 准备

1. 打开 **[Google Play Console](https://play.google.com/console)** -> **设置** -> **API 访问权限**；
2. 关联已有或新建一个 **Google Cloud 项目**；
3. 在“服务账号 (Service Accounts)”栏，点击**创建新服务账号**；
4. 为该服务账号授予 **“查看应用质量数据（只读）”** 权限；
5. 前往 **Google Cloud Console** -> **IAM 和管理** -> **服务账号**，选择刚创建的账号，进入 **“密钥”** 标签页，创建并下载 **JSON 格式密钥**；
6. 将下载的 JSON 文件妥善放置于本地（例如 `~/.config/gcp/play_service_account.json`）。

---

## 🤖 AI 客户端集成指南

### 1. Cursor 集成

在项目的 `.cursor/mcp.json` 或全局 Cursor MCP 配置中添加：

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

### 2. Claude Desktop 集成

编辑 `claude_desktop_config.json`：
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

### 3. Claude Code CLI 集成

直接通过终端命令添加：

```bash
claude mcp add google-play-vitals -- \
  google-play-vitals-mcp \
  --package-name com.yourcompany.app \
  --credentials /path/to/play_service_account.json
```

### 4. Windsurf 集成

在 `~/.codeium/windsurf/mcp_config.json` 中添加：

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

## 💡 对话提示词示例

接入完成后，您只需直接与 AI 助手对话：

- *“检查一下 Google Play Vitals 的连接状态。”*
- *“帮我分析当前线上的 Top ANR 簇，并展示具体卡死的主线程堆栈。”*
- *“查询过去 14 天的每日 ANR 率和冷启动慢速启动率走势。”*
- *“对比版本 204000 和 203000，量化验证我们上线的 Baseline Profile 和 ANR 治理是否带来了启动加速和稳定性提升。”*
- *“下钻查看 issue apps/com.example/errorIssues/123456 的多台设备样本堆栈。”*

---

## 💻 CLI 命令行支持

本工具同时提供独立的自检和运行命令：

```bash
# 自检环境配置与凭证可用性
google-play-vitals-mcp check -p com.example.app -c /path/to/key.json

# 手动启动 stdio MCP 服务端
google-play-vitals-mcp run -p com.example.app

# 查看当前版本
google-play-vitals-mcp --version
```

---

## 🔧 环境变量一览

| 环境变量 | 作用说明 |
| :--- | :--- |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP Service Account JSON 密钥文件本地绝对路径。 |
| `GOOGLE_PLAY_CREDENTIALS_JSON` | 密钥 JSON 内容字符串（云端部署或 CI/CD 环境无需落地文件直接注入）。 |
| `GOOGLE_PLAY_PACKAGE_NAME` | 默认 Android 应用包名（如 `com.example.app`）。 |
| `GOOGLE_PLAY_CACHE_TTL` | 内存缓存时长，单位秒（默认 `300`）。 |

---

## 📄 开源许可证

本项目遵循 [MIT License](LICENSE) 开源许可证。
