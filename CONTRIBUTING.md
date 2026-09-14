# Contributing to Google Play Vitals MCP

Thank you for your interest in contributing to **Google Play Vitals MCP**! We welcome contributions from developers worldwide to improve Android performance monitoring with AI.

## Code of Conduct

Please be respectful, collaborative, and constructive when reporting issues, suggesting features, or submitting pull requests.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/OldJii/google-play-vitals-mcp.git
   cd google-play-vitals-mcp
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies in editable mode**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests**:
   ```bash
   pytest -v
   ```

5. **Lint and format**:
   ```bash
   ruff check .
   ruff format .
   ```

## Pull Request Guidelines

- Ensure all new features or bug fixes are accompanied by unit tests in the `tests/` directory.
- Keep the code strictly decoupled from any proprietary organization or project dependencies.
- Maintain high Token economy standards: any new data fetching tool must filter and clean upstream Protobuf schemas to keep responses compact for LLMs.
- Adhere to the Model Context Protocol (MCP) specifications.
