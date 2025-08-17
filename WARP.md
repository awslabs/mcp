# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

- Scope: Python monorepo of multiple MCP servers under src/<server> with per-package isolation
- Tooling: uv for env/deps/build, pytest, ruff, pyright; optional Bandit; GitHub Actions mirrors these flows

1) Common development workflows (copy/paste commands)

Per-package setup (example: src/core-mcp-server)
- Install deps (dev + locked):
  cd src/core-mcp-server && uv sync --frozen --all-extras --dev
- Run the server locally (after sync):
  uv run awslabs.core-mcp-server
- Alternative: run latest published version (no local checkout required):
  uvx awslabs.core-mcp-server@latest

Testing
- Run all tests (if tests/ exists):
  uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
- Run a single test by pattern:
  uv run --frozen pytest -k "pattern_here"
- Run a specific test function:
  uv run --frozen pytest tests/path/to/test_file.py::TestClass::test_method

Linting and formatting
- Format (ruff):
  uv run --frozen ruff format .
- Lint (ruff):
  uv run --frozen ruff check .

Type checking
- Pyright:
  uv run --frozen pyright

Build
- Build wheel/sdist for a package:
  uv build

Pre-commit hooks (optional but recommended locally)
- Install hooks in your repo clone (once):
  pre-commit install
- Run all hooks on all files:
  pre-commit run -a

Security scan (optional)
- Bandit is run in CI using a pinned requirements file; locally you can:
  pip install --require-hashes --requirement .github/workflows/bandit-requirements.txt
  bandit -r --severity-level medium --confidence-level medium -f html -o bandit-report.html -c pyproject.toml .

Running other servers locally (examples)
- AWS API MCP Server (from its package dir):
  cd src/aws-api-mcp-server && uv sync --frozen --all-extras --dev && uv run awslabs.aws-api-mcp-server
- Or run latest published build without cloning:
  uvx awslabs.aws-api-mcp-server@latest
- Embeddings utilities (only for aws-api-mcp-server):
  uv run download-latest-embeddings
  uv run generate-embeddings

2) Architecture overview (big picture)

- Monorepo of independent MCP servers
  - Each server lives under src/<server-name> as its own Python package with pyproject.toml, optional tests/, and often a Dockerfile.
  - Packages expose console scripts via project.scripts (e.g., awslabs.core-mcp-server, awslabs.aws-api-mcp-server) for STDIO execution with MCP clients.

- Core orchestration vs. service-specific servers
  - core-mcp-server: entry point “awslabs.core-mcp-server”; provides planning/orchestration capabilities and is a typical starting server to coordinate others.
  - aws-api-mcp-server: exposes validated AWS CLI execution and suggestions (notable tools: call_aws, suggest_aws_commands) and includes embedding-related scripts used by CI.
  - Numerous service-focused servers (e.g., cdk-mcp-server, terraform-mcp-server, cloudwatch-mcp-server, dynamodb-mcp-server, etc.) follow a common pattern: Python package, uv-driven workflows, STDIO run mode, and readme-driven configuration.

- Standard tooling and conventions
  - Python 3.10+ across packages (some target/test 3.12+). uv is the canonical env/dependency/build tool.
  - Linting/formatting with ruff, type checking with pyright, tests with pytest.
  - Optional security scanning with Bandit; runs centrally in CI.

- CI/CD behavior (GitHub Actions reference)
  - Matrices detect changed packages and build/test each package independently.
  - Steps include: uv sync → (optional) embeddings maintenance for aws-api-mcp-server → pytest coverage → upload to Codecov → pyright → ruff format/check → uv build → SBOM generation.

- Execution modes
  - Local development: uv sync then uv run <console-script> from the package directory.
  - "Latest" execution: uvx <package>@latest for quick validation without local setup.
  - Some servers document container-based runs via their README Dockerfile instructions; primary mode is STDIO.

3) Repo rules and references to be aware of

- Root README highlights the catalog of servers and client install links; consult per-server README under src/<server>/ for configuration env vars and usage.
- CLAUDE PR review guidance (.github/workflows/CLAUDE_PR_REVIEW_GUIDE.md)
  - Prefer the GitHub MCP server over plain gh where possible, paginate long results, and always submit a final review decision (APPROVE or REQUEST_CHANGES).
  - Do not wait for this workflow’s check to finish when issuing a decision; rely on other required checks’ outcomes.
- SSE deprecation note is documented in the root README; servers are aligned with current MCP transports.

4) Environment notes

- macOS and Linux are well supported; CI pins Python via .python-version in each package.
- Ensure a recent uv is installed for best compatibility with pyproject settings.
- For servers interacting with AWS, set AWS credentials/region per their README (e.g., AWS_REGION, profiles). Some servers expose read-only/mutation-consent controls in env.

