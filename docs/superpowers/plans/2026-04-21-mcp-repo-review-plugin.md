# MCP Repo Review Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a shared Claude Code plugin at `.claude/plugins/mcp-repo-review/` that provides PR review, server audits, and cross-repo consistency checks for the awslabs/mcp monorepo.

**Architecture:** A project-level Claude Code plugin using auto-discovery conventions. Commands orchestrate agents and compose with official plugins (pr-review-toolkit, code-review). Skills provide repo-specific knowledge that auto-activates based on context. Hooks enforce lightweight structural guards. Helper scripts provide reusable validation logic.

**Tech Stack:** Claude Code plugin system (markdown frontmatter for commands/agents/skills, JSON for hooks/MCP config), Bash scripts, Python 3.10+ for convention checking.

**Working directory:** All file paths are relative to the worktree root at `.worktrees/mcp-repo-review-plugin/`. All file creation happens there.

**Spec:** `docs/superpowers/specs/2026-04-21-mcp-repo-review-plugin-design.md`

---

## File Map

### Plugin Scaffold (Task 1)
- Create: `.claude/plugins/mcp-repo-review/.claude-plugin/plugin.json`
- Create: `.claude/plugins/mcp-repo-review/.mcp.json`
- Create: `.claude/settings.json`

### Helper Scripts (Task 2)
- Create: `.claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh`
- Create: `.claude/plugins/mcp-repo-review/scripts/check-all-servers.sh`
- Create: `.claude/plugins/mcp-repo-review/scripts/server-conventions.py`

### Skills + References (Task 3)
- Create: `.claude/plugins/mcp-repo-review/skills/pr-review/SKILL.md`
- Create: `.claude/plugins/mcp-repo-review/skills/pr-review/references/review-checklist.md`
- Create: `.claude/plugins/mcp-repo-review/skills/server-audit/SKILL.md`
- Create: `.claude/plugins/mcp-repo-review/skills/server-audit/references/audit-criteria.md`
- Create: `.claude/plugins/mcp-repo-review/skills/consistency-check/SKILL.md`
- Create: `.claude/plugins/mcp-repo-review/skills/consistency-check/references/conventions.md`
- Create: `.claude/plugins/mcp-repo-review/skills/no-wrapper/SKILL.md`

### Agents (Task 4)
- Create: `.claude/plugins/mcp-repo-review/agents/guidelines-reviewer.md`
- Create: `.claude/plugins/mcp-repo-review/agents/security-auditor.md`
- Create: `.claude/plugins/mcp-repo-review/agents/consistency-checker.md`

### Commands (Task 5)
- Create: `.claude/plugins/mcp-repo-review/commands/repo-review-pr.md`
- Create: `.claude/plugins/mcp-repo-review/commands/audit-server.md`
- Create: `.claude/plugins/mcp-repo-review/commands/check-consistency.md`

### Hooks (Task 6)
- Create: `.claude/plugins/mcp-repo-review/hooks/hooks.json`

---

## Task 1: Plugin Scaffold + Configuration

**Files:**
- Create: `.claude/plugins/mcp-repo-review/.claude-plugin/plugin.json`
- Create: `.claude/plugins/mcp-repo-review/.mcp.json`
- Create: `.claude/settings.json`

- [ ] **Step 1: Create plugin manifest**

Create `.claude/plugins/mcp-repo-review/.claude-plugin/plugin.json`:

```json
{
  "name": "mcp-repo-review",
  "version": "0.1.0",
  "description": "Review tooling for the awslabs/mcp monorepo — PR review, server audits, and cross-repo consistency checks",
  "license": "Apache-2.0"
}
```

- [ ] **Step 2: Create MCP server config**

Create `.claude/plugins/mcp-repo-review/.mcp.json`:

```json
{
  "mcpServers": {
    "semgrep": {
      "command": "semgrep",
      "args": ["--config", "auto"],
      "env": {}
    }
  }
}
```

- [ ] **Step 3: Create shared settings.json**

Create `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run --frozen pytest:*)",
      "Bash(ruff check:*)",
      "Bash(ruff format --check:*)"
    ]
  },
  "enabledPlugins": {
    ".claude/plugins/mcp-repo-review": true
  }
}
```

- [ ] **Step 4: Verify directory structure**

Run: `find .claude/ -type f | sort`

Expected output:
```
.claude/plugins/mcp-repo-review/.claude-plugin/plugin.json
.claude/plugins/mcp-repo-review/.mcp.json
.claude/settings.json
```

- [ ] **Step 5: Commit**

```bash
git add .claude/
git commit -m "feat(mcp-repo-review): scaffold plugin manifest, MCP config, and shared settings"
```

---

## Task 2: Helper Scripts

**Files:**
- Create: `.claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh`
- Create: `.claude/plugins/mcp-repo-review/scripts/check-all-servers.sh`
- Create: `.claude/plugins/mcp-repo-review/scripts/server-conventions.py`

- [ ] **Step 1: Create validate-server-structure.sh**

Create `.claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh`:

```bash
#!/bin/bash
# Validates basic MCP server directory structure.
# Usage: validate-server-structure.sh <server-dir>
# Exit code = number of errors found.

set -euo pipefail

SERVER_DIR="${1:?Usage: validate-server-structure.sh <server-dir>}"
ERRORS=0

check_exists() {
    local path="$1"
    local label="$2"
    if [ ! -e "$path" ]; then
        echo "MISSING: $label ($path)"
        ERRORS=$((ERRORS + 1))
    fi
}

check_exists "$SERVER_DIR/pyproject.toml" "pyproject.toml"
check_exists "$SERVER_DIR/README.md" "README.md"
check_exists "$SERVER_DIR/LICENSE" "LICENSE"
check_exists "$SERVER_DIR/awslabs" "awslabs/ package directory"
check_exists "$SERVER_DIR/tests" "tests/ directory"

if [ "$ERRORS" -eq 0 ]; then
    echo "OK: $SERVER_DIR"
fi

exit "$ERRORS"
```

- [ ] **Step 2: Make it executable and test against a known-good server**

Run:
```bash
chmod +x .claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh
.claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh src/aws-documentation-mcp-server
```

Expected: `OK: src/aws-documentation-mcp-server` with exit code 0.

- [ ] **Step 3: Create check-all-servers.sh**

Create `.claude/plugins/mcp-repo-review/scripts/check-all-servers.sh`:

```bash
#!/bin/bash
# Iterates all src/*-mcp-server/ directories and validates structure.
# Usage: check-all-servers.sh [repo-root]
# Prints a summary table of pass/fail per server.

set -uo pipefail

REPO_ROOT="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATOR="$SCRIPT_DIR/../hooks/scripts/validate-server-structure.sh"

PASS=0
FAIL=0
FAILURES=""

for server_dir in "$REPO_ROOT"/src/*-mcp-server; do
    [ -d "$server_dir" ] || continue
    name="$(basename "$server_dir")"

    output=$("$VALIDATOR" "$server_dir" 2>&1) && {
        PASS=$((PASS + 1))
    } || {
        FAIL=$((FAIL + 1))
        FAILURES="${FAILURES}\n  ${name}: ${output}"
    }
done

echo "=== Server Structure Check ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"

if [ "$FAIL" -gt 0 ]; then
    echo -e "\nFailures:$FAILURES"
    exit 1
fi

exit 0
```

- [ ] **Step 4: Make it executable and test**

Run:
```bash
chmod +x .claude/plugins/mcp-repo-review/scripts/check-all-servers.sh
.claude/plugins/mcp-repo-review/scripts/check-all-servers.sh
```

Expected: prints pass/fail counts for all servers. Some may fail if they are stubs.

- [ ] **Step 5: Create server-conventions.py**

Create `.claude/plugins/mcp-repo-review/scripts/server-conventions.py`:

```python
#!/usr/bin/env python3
"""Convention checker for awslabs/mcp monorepo servers.

Validates that all src/*-mcp-server/ packages follow repo conventions:
- pyproject.toml structure (name, version, entry points, commitizen)
- Version sync between pyproject.toml and __init__.py
- License headers on .py files
- Entry point conventions (server.py with main())
"""

import glob
import os
import re
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

LICENSE_HEADER = "# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved."

REQUIRED_PYPROJECT_FIELDS = ["name", "version", "description", "readme", "requires-python", "license"]


def find_servers(repo_root: str) -> list[str]:
    pattern = os.path.join(repo_root, "src", "*-mcp-server")
    return sorted(glob.glob(pattern))


def check_pyproject(server_dir: str) -> list[str]:
    errors = []
    path = os.path.join(server_dir, "pyproject.toml")
    if not os.path.exists(path):
        return ["pyproject.toml missing"]

    with open(path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    for field in REQUIRED_PYPROJECT_FIELDS:
        if field not in project:
            errors.append(f"pyproject.toml missing [project].{field}")

    name = project.get("name", "")
    if name and not name.startswith("awslabs."):
        errors.append(f"pyproject.toml name '{name}' must start with 'awslabs.'")

    scripts = project.get("scripts", {})
    if not scripts:
        errors.append("pyproject.toml missing [project.scripts] entry point")
    else:
        for entry_name, entry_path in scripts.items():
            if not entry_path.endswith(":main"):
                errors.append(f"entry point '{entry_name}' should end with ':main'")
            if "server:main" not in entry_path:
                errors.append(f"entry point '{entry_name}' should reference 'server:main'")

    commitizen = data.get("tool", {}).get("commitizen", {})
    if not commitizen:
        errors.append("pyproject.toml missing [tool.commitizen] config")

    return errors


def check_version_sync(server_dir: str) -> list[str]:
    errors = []
    pyproject_path = os.path.join(server_dir, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        return []

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    pyproject_version = data.get("project", {}).get("version", "")

    awslabs_dir = os.path.join(server_dir, "awslabs")
    if not os.path.isdir(awslabs_dir):
        return []

    init_files = glob.glob(os.path.join(awslabs_dir, "*", "__init__.py"))
    for init_file in init_files:
        with open(init_file) as f:
            content = f.read()
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            init_version = match.group(1)
            if init_version != pyproject_version:
                errors.append(
                    f"version mismatch: pyproject.toml={pyproject_version} "
                    f"vs __init__.py={init_version}"
                )

    return errors


def check_license_headers(server_dir: str) -> list[str]:
    errors = []
    for py_file in glob.glob(os.path.join(server_dir, "awslabs", "**", "*.py"), recursive=True):
        with open(py_file) as f:
            first_line = f.readline().strip()
        if first_line and not first_line.startswith("#!") and first_line != LICENSE_HEADER:
            rel = os.path.relpath(py_file, server_dir)
            errors.append(f"{rel}: missing license header")
        elif first_line.startswith("#!"):
            second_line = f.readline().strip()
            if second_line != LICENSE_HEADER and second_line != "":
                rel = os.path.relpath(py_file, server_dir)
                errors.append(f"{rel}: missing license header after shebang")

    return errors


def check_server(server_dir: str) -> dict:
    name = os.path.basename(server_dir)
    all_errors = []
    all_errors.extend(check_pyproject(server_dir))
    all_errors.extend(check_version_sync(server_dir))
    all_errors.extend(check_license_headers(server_dir))
    return {"name": name, "errors": all_errors}


def main():
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    servers = find_servers(repo_root)

    if not servers:
        print(f"No servers found under {repo_root}/src/*-mcp-server")
        sys.exit(1)

    results = [check_server(s) for s in servers]

    passed = [r for r in results if not r["errors"]]
    failed = [r for r in results if r["errors"]]

    print(f"=== Convention Check: {len(passed)} passed, {len(failed)} failed ===\n")

    if failed:
        for r in failed:
            print(f"FAIL: {r['name']}")
            for e in r["errors"]:
                print(f"  - {e}")
            print()

    if not failed:
        print("All servers follow conventions.")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Test server-conventions.py against the repo**

Run: `python3 .claude/plugins/mcp-repo-review/scripts/server-conventions.py .`

Expected: prints pass/fail table for all servers. Review output for reasonableness.

- [ ] **Step 7: Commit**

```bash
chmod +x .claude/plugins/mcp-repo-review/scripts/check-all-servers.sh
chmod +x .claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh
git add .claude/plugins/mcp-repo-review/hooks/scripts/ .claude/plugins/mcp-repo-review/scripts/
git commit -m "feat(mcp-repo-review): add validation scripts for server structure and conventions"
```

---

## Task 3: Skills + Reference Documents

**Files:**
- Create: `.claude/plugins/mcp-repo-review/skills/pr-review/SKILL.md`
- Create: `.claude/plugins/mcp-repo-review/skills/pr-review/references/review-checklist.md`
- Create: `.claude/plugins/mcp-repo-review/skills/server-audit/SKILL.md`
- Create: `.claude/plugins/mcp-repo-review/skills/server-audit/references/audit-criteria.md`
- Create: `.claude/plugins/mcp-repo-review/skills/consistency-check/SKILL.md`
- Create: `.claude/plugins/mcp-repo-review/skills/consistency-check/references/conventions.md`
- Create: `.claude/plugins/mcp-repo-review/skills/no-wrapper/SKILL.md`

- [ ] **Step 1: Create pr-review/SKILL.md**

Create `.claude/plugins/mcp-repo-review/skills/pr-review/SKILL.md`:

```markdown
---
name: mcp-repo-pr-review
description: Use when reviewing pull requests in the awslabs/mcp repository. Provides repo-specific review criteria from DESIGN_GUIDELINES.md and DEVELOPER_GUIDE.md that complement the general-purpose pr-review-toolkit.
---

# MCP Repo PR Review

When reviewing PRs in this repository, apply the repo-specific checklist in addition to general code quality checks.

## Workflow

1. First, invoke the official `pr-review-toolkit:review-pr` skill for general code review
2. Then apply the repo-specific checklist below

## Repo-Specific Checks

Load the full checklist from [references/review-checklist.md](references/review-checklist.md) for detailed criteria.

**Quick summary of what to check:**

- License header present on all new/modified `.py` files
- `pyproject.toml` name starts with `awslabs.`
- Entry point is `server.py:main` — no separate `main.py`
- Tool names follow conventions: snake_case recommended, max 64 chars, consistent within server
- Field descriptions on all MCP tool parameters
- Async/await patterns used for all MCP tool and resource functions
- `loguru` used for logging (not stdlib `logging`)
- Error handling uses `ctx.error()` for MCP context reporting

## Reference Files

### [review-checklist.md](references/review-checklist.md)
**When:** ALWAYS load when reviewing a PR
**Contains:** Full review criteria organized by category
```

- [ ] **Step 2: Create pr-review/references/review-checklist.md**

Create `.claude/plugins/mcp-repo-review/skills/pr-review/references/review-checklist.md`:

```markdown
# PR Review Checklist for awslabs/mcp

## Project Structure
- [ ] Server code is under `src/<name>-mcp-server/`
- [ ] Source code is in `awslabs/<module_name>/` (underscores, not hyphens)
- [ ] `tests/` directory exists
- [ ] `pyproject.toml`, `README.md`, `LICENSE`, `NOTICE` present

## Package Naming and Versioning
- [ ] `pyproject.toml` name follows `awslabs.<name>-mcp-server` pattern
- [ ] Version in `__init__.py` matches `pyproject.toml` version
- [ ] `[tool.commitizen]` section present in `pyproject.toml`
- [ ] `version_files` in commitizen references both `pyproject.toml:version` and `__init__.py:__version__`

## License and Copyright
- [ ] All `.py` files start with Apache 2.0 license header
- [ ] Header text matches: `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`

## Entry Points
- [ ] Single entry point in `server.py` (no separate `main.py`)
- [ ] `main()` function defined in `server.py`
- [ ] `[project.scripts]` entry ends with `server:main`

## Tool Definitions
- [ ] Tool names: max 64 characters, start with letter, alphanumeric + underscores/hyphens only
- [ ] Consistent naming style within server (snake_case recommended)
- [ ] All parameters use `Field()` with descriptions
- [ ] Required parameters use `...` as default
- [ ] Optional parameters have sensible defaults and `Optional` type hint
- [ ] `Context` parameter included for error reporting

## Code Quality
- [ ] Async/await used for all MCP tool and resource functions
- [ ] `loguru` logger used (not stdlib `logging`)
- [ ] Log level configurable via `FASTMCP_LOG_LEVEL` env var
- [ ] Error handling uses try/except with `ctx.error()` reporting
- [ ] Constants in dedicated `consts.py` file

## Security
- [ ] AWS auth supports both `AWS_PROFILE` and default credentials
- [ ] Region configurable via `AWS_REGION` env var
- [ ] No hardcoded credentials or secrets
- [ ] User-provided code execution uses controlled namespaces
- [ ] Timeouts on long-running operations
- [ ] Explicit allowlists for permitted operations

## Documentation
- [ ] Comprehensive docstrings on all MCP tools
- [ ] `README.md` includes setup instructions and usage examples
- [ ] All environment variables documented in README
- [ ] `FastMCP` constructor includes `instructions` parameter

## Testing
- [ ] Unit tests exist in `tests/`
- [ ] Integration tests follow `integ_<test-name>.py` or `test_integ_*.py` naming
- [ ] `pytest-asyncio` used for async test functions
- [ ] AWS services mocked (moto or similar)
```

- [ ] **Step 3: Create server-audit/SKILL.md**

Create `.claude/plugins/mcp-repo-review/skills/server-audit/SKILL.md`:

```markdown
---
name: mcp-server-audit
description: Use when auditing or working within a specific src/*-mcp-server/ directory in the awslabs/mcp repository. Provides expected file layout, quality criteria, and audit steps.
---

# MCP Server Audit

When auditing or working within a specific MCP server package, use these criteria to evaluate quality and compliance.

## Audit Steps

1. **Structure check:** Run `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-server-structure.sh <server-dir>`
2. **Convention check:** Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/server-conventions.py .` and filter for the target server
3. **Test coverage:** Run `cd <server-dir> && uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
4. **Lint check:** Run `cd <server-dir> && uv run ruff check .`
5. **Code review:** Invoke `code-review:code-review` skill for general quality
6. **Security scan:** Use semgrep MCP server for security-specific checks

## Reference Files

### [audit-criteria.md](references/audit-criteria.md)
**When:** ALWAYS load when auditing a server
**Contains:** Detailed quality criteria and expected patterns
```

- [ ] **Step 4: Create server-audit/references/audit-criteria.md**

Create `.claude/plugins/mcp-repo-review/skills/server-audit/references/audit-criteria.md`:

```markdown
# Server Audit Criteria

## Expected Directory Layout

```
<name>-mcp-server/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── NOTICE
├── Dockerfile (optional)
├── .pre-commit-config.yaml (optional)
├── awslabs/
│   ├── __init__.py
│   └── <module_name>/
│       ├── __init__.py      # Contains __version__
│       ├── server.py        # Entry point with main()
│       ├── models.py        # Pydantic models (optional)
│       ├── consts.py        # Constants (optional)
│       └── ...              # Additional modules
└── tests/
    ├── test_*.py            # Unit tests
    └── test_integ_*.py      # Integration tests (optional)
```

## Code Quality Criteria

### Entry Point (server.py)
- Defines `main()` function
- Handles command-line arguments
- Sets up environment and logging
- Initializes FastMCP server with `instructions` parameter
- `if __name__ == '__main__': main()` guard present

### Models (models.py)
- Pydantic BaseModel used for all data models
- Comprehensive type hints
- Field validation with `Field()` constraints
- Enums for constrained values
- Model validators where appropriate

### Constants (consts.py)
- UPPER_CASE naming
- Grouped by category
- Documented with docstrings

### Async Patterns
- All MCP tool/resource functions are `async`
- `asyncio.gather` for concurrent operations
- Non-blocking I/O for external API calls

### Security Patterns
- boto3 auth: supports AWS_PROFILE and default credentials
- Region via AWS_REGION env var
- Controlled execution: isolated namespace, timeout handlers
- Allowlists for permitted operations/modules
- Input validation for all tool parameters

### Logging
- Uses `loguru` (not stdlib logging)
- Configurable via FASTMCP_LOG_LEVEL env var
- Appropriate log levels (debug/info/warning/error)
- Context included in log messages

### Error Handling
- try/except with ctx.error() for MCP context
- Meaningful error messages
- Exceptions logged with context
```

- [ ] **Step 5: Create consistency-check/SKILL.md**

Create `.claude/plugins/mcp-repo-review/skills/consistency-check/SKILL.md`:

```markdown
---
name: mcp-consistency-check
description: Use when doing cross-repo analysis, checking conventions across servers, or asking about monorepo consistency in the awslabs/mcp repository.
---

# MCP Cross-Repo Consistency Check

When checking consistency across the 55 MCP servers in this monorepo, use these conventions and tools.

## Quick Check

Run the automated checks:

```bash
# Structure check (all servers)
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-all-servers.sh

# Convention check (all servers)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/server-conventions.py .
```

## Reference Files

### [conventions.md](references/conventions.md)
**When:** ALWAYS load when checking conventions
**Contains:** Full list of conventions that must be uniform across all servers
```

- [ ] **Step 6: Create consistency-check/references/conventions.md**

Create `.claude/plugins/mcp-repo-review/skills/consistency-check/references/conventions.md`:

```markdown
# Monorepo Conventions

All 55 servers under `src/*-mcp-server/` must follow these conventions uniformly.

## pyproject.toml

Every server must have:

| Field | Convention | Example |
|---|---|---|
| `[project].name` | `awslabs.<name>-mcp-server` | `awslabs.aws-documentation-mcp-server` |
| `[project].version` | Semver string | `1.1.21` |
| `[project].description` | Starts with "An AWS Labs Model Context Protocol (MCP) server" | - |
| `[project].readme` | `"README.md"` | - |
| `[project].requires-python` | `">=3.10"` | - |
| `[project].license` | `{text = "Apache-2.0"}` | - |
| `[project].license-files` | `["LICENSE", "NOTICE"]` | - |
| `[project.scripts]` | Entry name matches project name, value ends in `server:main` | `"awslabs.aws-documentation-mcp-server" = "awslabs.aws_documentation_mcp_server.server:main"` |
| `[tool.commitizen]` | Present with `version_files` referencing pyproject.toml and __init__.py | - |

## Version Sync

- `__version__` in `awslabs/<module>/__init__.py` must match `[project].version` in `pyproject.toml`
- `[tool.commitizen].version` must also match

## License Headers

All `.py` files under `awslabs/` must start with the Apache 2.0 license header (13 lines starting with `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`).

## Directory Structure

Every server must have:
- `awslabs/` directory with `__init__.py`
- `awslabs/<module>/` with `__init__.py`, `server.py`
- `tests/` directory
- `pyproject.toml`, `README.md`, `LICENSE` at root

## Entry Points

- Single entry point in `server.py` (no `main.py`)
- `main()` function with `if __name__ == '__main__': main()` guard
- `[project.scripts]` in pyproject.toml references `server:main`

## Dependencies

Common required dependencies:
- `mcp[cli]>=1.23.0`
- `pydantic>=2.10.6`
- `loguru>=0.7.0`

## Code Style

- `ruff` for formatting and linting (config in root `.ruff.toml`)
- `pre-commit` hooks configured
- Line length: 99 characters
- Quote style: single quotes
```

- [ ] **Step 7: Create no-wrapper/SKILL.md placeholder**

Create `.claude/plugins/mcp-repo-review/skills/no-wrapper/SKILL.md`:

```markdown
---
name: mcp-no-wrapper
description: Placeholder for future "no wrapper" requirement. Content to be defined.
---

# No Wrapper

This skill is a placeholder. Content will be added when the "no wrapper" requirement is defined.
```

- [ ] **Step 8: Verify all skill files exist**

Run: `find .claude/plugins/mcp-repo-review/skills -type f | sort`

Expected:
```
.claude/plugins/mcp-repo-review/skills/consistency-check/SKILL.md
.claude/plugins/mcp-repo-review/skills/consistency-check/references/conventions.md
.claude/plugins/mcp-repo-review/skills/no-wrapper/SKILL.md
.claude/plugins/mcp-repo-review/skills/pr-review/SKILL.md
.claude/plugins/mcp-repo-review/skills/pr-review/references/review-checklist.md
.claude/plugins/mcp-repo-review/skills/server-audit/SKILL.md
.claude/plugins/mcp-repo-review/skills/server-audit/references/audit-criteria.md
```

- [ ] **Step 9: Commit**

```bash
git add .claude/plugins/mcp-repo-review/skills/
git commit -m "feat(mcp-repo-review): add skills with reference documents for PR review, server audit, consistency check"
```

---

## Task 4: Agents

**Files:**
- Create: `.claude/plugins/mcp-repo-review/agents/guidelines-reviewer.md`
- Create: `.claude/plugins/mcp-repo-review/agents/security-auditor.md`
- Create: `.claude/plugins/mcp-repo-review/agents/consistency-checker.md`

- [ ] **Step 1: Create guidelines-reviewer.md**

Create `.claude/plugins/mcp-repo-review/agents/guidelines-reviewer.md`:

```markdown
---
description: >
  Reviews code against awslabs/mcp repository conventions defined in
  DESIGN_GUIDELINES.md and DEVELOPER_GUIDE.md. Use for PR reviews and
  server audits that need convention compliance checking.
tools:
  - Read
  - Grep
  - Glob
  - Bash
---

You are a code reviewer specialized in the awslabs/mcp monorepo conventions.

## Your Knowledge

You enforce the conventions from two key documents:

1. **DESIGN_GUIDELINES.md** — Project structure, code organization, package naming, license headers, type definitions, Field guidelines, tool naming, async patterns, response formatting, security practices, logging, auth, env vars, error handling, documentation, testing.

2. **DEVELOPER_GUIDE.md** — Build setup, testing workflow, PR process, pre-commit hooks.

## How to Review

When asked to review code:

1. Read `DESIGN_GUIDELINES.md` and `DEVELOPER_GUIDE.md` from the repo root
2. Identify which server package the code belongs to
3. Check each item against the conventions
4. Report findings organized by severity:
   - **MUST FIX:** Violations of required conventions (license headers, naming, entry points)
   - **SHOULD FIX:** Deviations from recommended patterns (logging, Field descriptions)
   - **CONSIDER:** Style suggestions and improvements

## Key Conventions to Check

- **Project structure:** `awslabs/<module>/server.py` as sole entry point
- **Package naming:** `awslabs.<name>-mcp-server` in pyproject.toml
- **License headers:** Apache 2.0 on all `.py` files
- **Tool naming:** snake_case, max 64 chars, consistent within server
- **Field parameters:** All tool params use `Field()` with descriptions
- **Async:** All MCP tools/resources are async
- **Logging:** loguru, configurable via FASTMCP_LOG_LEVEL
- **Error handling:** try/except with ctx.error()
- **Auth:** boto3 with AWS_PROFILE + default credential support
- **Testing:** pytest with coverage, integration tests in tests/
```

- [ ] **Step 2: Create security-auditor.md**

Create `.claude/plugins/mcp-repo-review/agents/security-auditor.md`:

```markdown
---
description: >
  Audits MCP server code for AWS-specific security patterns: IAM authentication,
  credential handling, boto3 patterns, controlled execution environments, and
  input validation. Complements general security review plugins.
tools:
  - Read
  - Grep
  - Glob
  - Bash
---

You are a security auditor specialized in AWS MCP server patterns.

## Your Focus

You check for security patterns **specific to this repo** that general security tools miss. You complement (not duplicate) the `code-review:code-review` plugin.

## Security Checklist

### Authentication
- boto3 sessions support both `AWS_PROFILE` and default credentials
- Region is configurable via `AWS_REGION` env var
- No hardcoded credentials, access keys, or secrets in source code
- IAM permissions documented in README

### Credential Handling
- No secrets in environment variable defaults
- No credentials logged (even at debug level)
- Auth tokens generated fresh, not cached long-term

### Controlled Execution
- User-provided code runs in isolated namespaces
- Explicit module allowlists for exec() environments
- Timeout handlers on all long-running operations (`signal.SIGALRM`)
- Resources cleaned up even on failure (context managers)

### Input Validation
- All MCP tool parameters validated via Field() constraints
- SQL inputs sanitized with allowlists/regex (no parameterized queries in DSQL)
- File paths validated and sandboxed
- No eval() or exec() on raw user input

### Dependencies
- No known-vulnerable dependency versions pinned
- Security-relevant deps (cryptography, boto3) kept current
- `detect-secrets` baseline maintained (`.secrets.baseline`)

## How to Audit

1. Grep for security-sensitive patterns: `exec(`, `eval(`, `os.system`, `subprocess`, hardcoded credentials
2. Check boto3 session creation for proper auth pattern
3. Verify timeout handlers exist on operations that call external services
4. Review Field() constraints on all tool parameters
5. Check that README documents required IAM permissions
```

- [ ] **Step 3: Create consistency-checker.md**

Create `.claude/plugins/mcp-repo-review/agents/consistency-checker.md`:

```markdown
---
description: >
  Validates that all 55 MCP server packages in the awslabs/mcp monorepo follow
  the same conventions. Checks pyproject.toml fields, version sync, license
  headers, entry points, and directory structure across all servers.
tools:
  - Read
  - Grep
  - Glob
  - Bash
---

You are a consistency checker for the awslabs/mcp monorepo.

## Your Job

Ensure all 55 servers under `src/*-mcp-server/` follow identical conventions. Drift between servers creates maintenance burden and confuses contributors.

## Available Tools

Run the automated scripts first, then investigate any failures:

```bash
# Structure check
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-all-servers.sh

# Convention check
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/server-conventions.py .
```

## What to Check

### Uniform pyproject.toml Fields
- All servers have `[project].name` starting with `awslabs.`
- All servers have `[project].license = {text = "Apache-2.0"}`
- All servers have `[project].requires-python = ">=3.10"`
- All servers have `[project.scripts]` ending in `server:main`
- All servers have `[tool.commitizen]` config

### Version Synchronization
- `__version__` in `__init__.py` matches `[project].version` in pyproject.toml
- `[tool.commitizen].version` matches as well

### Directory Structure
- Every server has: `awslabs/`, `tests/`, `pyproject.toml`, `README.md`, `LICENSE`
- Source module uses underscores (not hyphens)
- Entry point is `server.py` (not `main.py`)

### Code Patterns
- All servers use loguru (not stdlib logging)
- All servers configure log level via FASTMCP_LOG_LEVEL
- All servers use async for MCP tools/resources

## Reporting

Present findings as a table:

| Server | Status | Issues |
|--------|--------|--------|
| aws-documentation-mcp-server | PASS | - |
| some-other-mcp-server | FAIL | missing commitizen config, version mismatch |
```

- [ ] **Step 4: Verify all agent files exist**

Run: `find .claude/plugins/mcp-repo-review/agents -type f | sort`

Expected:
```
.claude/plugins/mcp-repo-review/agents/consistency-checker.md
.claude/plugins/mcp-repo-review/agents/guidelines-reviewer.md
.claude/plugins/mcp-repo-review/agents/security-auditor.md
```

- [ ] **Step 5: Commit**

```bash
git add .claude/plugins/mcp-repo-review/agents/
git commit -m "feat(mcp-repo-review): add guidelines-reviewer, security-auditor, and consistency-checker agents"
```

---

## Task 5: Commands

**Files:**
- Create: `.claude/plugins/mcp-repo-review/commands/repo-review-pr.md`
- Create: `.claude/plugins/mcp-repo-review/commands/audit-server.md`
- Create: `.claude/plugins/mcp-repo-review/commands/check-consistency.md`

- [ ] **Step 1: Create repo-review-pr.md**

Create `.claude/plugins/mcp-repo-review/commands/repo-review-pr.md`:

```markdown
---
name: repo-review-pr
description: Review a PR against awslabs/mcp repo conventions, composing with the official pr-review-toolkit
---

# Repo PR Review

You are reviewing a pull request in the awslabs/mcp repository.

## Step 1: Run Official Review

First, invoke the `pr-review-toolkit:review-pr` skill to run the general-purpose review suite (code-reviewer, silent-failure-hunter, type-design-analyzer, etc.).

## Step 2: Identify Changed Servers

Determine which `src/*-mcp-server/` directories have changes in this PR:

```bash
git diff --name-only main...HEAD | grep "^src/" | cut -d/ -f2 | sort -u
```

## Step 3: Repo-Specific Checks

For each changed server, check:

### Structure
- Run `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-server-structure.sh src/<server>`
- Verify new files follow expected directory layout

### License Headers
- All new/modified `.py` files must start with the Apache 2.0 license header
- Check: `head -1 <file>` should be `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`

### pyproject.toml
- Name follows `awslabs.*` pattern
- Entry point references `server:main`
- Commitizen config present
- Version synced with `__init__.py`

### Tool Naming
- All tool names: max 64 chars, start with letter, alphanumeric + underscores/hyphens
- Consistent naming style within the server (don't mix snake_case and PascalCase)

### Code Patterns
- MCP tools/resources are async
- Field() with descriptions on all parameters
- loguru for logging (not stdlib)
- Error handling uses ctx.error()

## Step 4: Report

Present findings organized as:
1. **Official review results** (from pr-review-toolkit)
2. **Repo-specific findings** (from the checks above)
   - MUST FIX: Convention violations
   - SHOULD FIX: Recommended pattern deviations
   - PASS: What looks good
```

- [ ] **Step 2: Create audit-server.md**

Create `.claude/plugins/mcp-repo-review/commands/audit-server.md`:

```markdown
---
name: audit-server
description: Deep audit of a single MCP server package
arguments:
  - name: server
    description: "Server directory name (e.g., aws-documentation-mcp-server)"
    required: true
---

# Server Audit: {{server}}

You are running a deep audit of `src/{{server}}/`.

## Step 1: Verify Server Exists

```bash
ls src/{{server}}/pyproject.toml
```

If it doesn't exist, list available servers with `ls src/*-mcp-server/` and ask the user which one.

## Step 2: Structure Validation

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-server-structure.sh src/{{server}}
```

## Step 3: Convention Check

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/server-conventions.py . 2>&1 | grep -A 10 "{{server}}"
```

## Step 4: Test Coverage

```bash
cd src/{{server}} && uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

Report coverage percentage and any uncovered lines.

## Step 5: Lint Check

```bash
cd src/{{server}} && uv run ruff check .
```

## Step 6: Security Review

Use the `security-auditor` agent to check:
- boto3 auth patterns
- Credential handling
- Input validation on tool parameters
- Timeout handlers
- Controlled execution patterns (if applicable)

## Step 7: Code Quality Review

Invoke `code-review:code-review` for general quality review of the server code.

## Step 8: Report

Present a comprehensive audit report:

| Category | Status | Details |
|----------|--------|---------|
| Structure | PASS/FAIL | ... |
| Conventions | PASS/FAIL | ... |
| Test Coverage | XX% | ... |
| Lint | PASS/FAIL | ... |
| Security | PASS/FAIL | ... |
| Code Quality | PASS/FAIL | ... |
```

- [ ] **Step 3: Create check-consistency.md**

Create `.claude/plugins/mcp-repo-review/commands/check-consistency.md`:

```markdown
---
name: check-consistency
description: Check convention consistency across all MCP servers in the monorepo
---

# Cross-Repo Consistency Check

You are checking that all MCP servers in the monorepo follow the same conventions.

## Step 1: Run Automated Checks

```bash
# Structure check across all servers
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-all-servers.sh

# Convention check across all servers
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/server-conventions.py .
```

## Step 2: Analyze Results

Use the `consistency-checker` agent to analyze the output and investigate any failures.

## Step 3: Report

Present results as a summary table:

| Server | Structure | pyproject.toml | Version Sync | License Headers | Entry Point |
|--------|-----------|----------------|--------------|-----------------|-------------|
| server-a | PASS | PASS | PASS | PASS | PASS |
| server-b | PASS | FAIL | PASS | FAIL | PASS |

Then list specific issues for each failing server.

## Step 4: Recommendations

For any systemic issues (same problem across many servers), recommend a batch fix approach rather than per-server fixes.
```

- [ ] **Step 4: Verify all command files exist**

Run: `find .claude/plugins/mcp-repo-review/commands -type f | sort`

Expected:
```
.claude/plugins/mcp-repo-review/commands/audit-server.md
.claude/plugins/mcp-repo-review/commands/check-consistency.md
.claude/plugins/mcp-repo-review/commands/repo-review-pr.md
```

- [ ] **Step 5: Commit**

```bash
git add .claude/plugins/mcp-repo-review/commands/
git commit -m "feat(mcp-repo-review): add repo-review-pr, audit-server, and check-consistency commands"
```

---

## Task 6: Hooks

**Files:**
- Create: `.claude/plugins/mcp-repo-review/hooks/hooks.json`

- [ ] **Step 1: Create hooks.json**

Create `.claude/plugins/mcp-repo-review/hooks/hooks.json`:

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "If the file being written is inside src/*-mcp-server/, verify it follows the expected project structure from DESIGN_GUIDELINES.md (license header, correct package nesting under awslabs/). Only FAIL if the structure is clearly wrong. Pass silently otherwise.",
          "timeout": 10
        }
      ]
    }
  ],
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Before finishing: if any files were modified inside src/*-mcp-server/ during this session, remind the user to run tests with 'uv run --frozen pytest --cov --cov-branch' in the affected server directory. Do NOT block — just add a reminder.",
          "timeout": 5
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Verify complete plugin structure**

Run: `find .claude/ -type f | sort`

Expected:
```
.claude/plugins/mcp-repo-review/.claude-plugin/plugin.json
.claude/plugins/mcp-repo-review/.mcp.json
.claude/plugins/mcp-repo-review/agents/consistency-checker.md
.claude/plugins/mcp-repo-review/agents/guidelines-reviewer.md
.claude/plugins/mcp-repo-review/agents/security-auditor.md
.claude/plugins/mcp-repo-review/commands/audit-server.md
.claude/plugins/mcp-repo-review/commands/check-consistency.md
.claude/plugins/mcp-repo-review/commands/repo-review-pr.md
.claude/plugins/mcp-repo-review/hooks/hooks.json
.claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh
.claude/plugins/mcp-repo-review/scripts/check-all-servers.sh
.claude/plugins/mcp-repo-review/scripts/server-conventions.py
.claude/plugins/mcp-repo-review/skills/consistency-check/SKILL.md
.claude/plugins/mcp-repo-review/skills/consistency-check/references/conventions.md
.claude/plugins/mcp-repo-review/skills/no-wrapper/SKILL.md
.claude/plugins/mcp-repo-review/skills/pr-review/SKILL.md
.claude/plugins/mcp-repo-review/skills/pr-review/references/review-checklist.md
.claude/plugins/mcp-repo-review/skills/server-audit/SKILL.md
.claude/plugins/mcp-repo-review/skills/server-audit/references/audit-criteria.md
.claude/settings.json
```

- [ ] **Step 3: Commit**

```bash
git add .claude/plugins/mcp-repo-review/hooks/hooks.json
git commit -m "feat(mcp-repo-review): add hooks for structure validation and test reminders"
```

---

## Task 7: Final Verification + Push

- [ ] **Step 1: Verify full file count**

Run: `find .claude/ -type f | sort | wc -l`

Expected: 20 files.

- [ ] **Step 2: Run structure validator against a known-good server**

Run: `.claude/plugins/mcp-repo-review/hooks/scripts/validate-server-structure.sh src/aws-documentation-mcp-server`

Expected: `OK: src/aws-documentation-mcp-server`

- [ ] **Step 3: Run convention checker**

Run: `python3 .claude/plugins/mcp-repo-review/scripts/server-conventions.py .`

Expected: completes without crashing, reports findings for all servers.

- [ ] **Step 4: Run full server structure check**

Run: `.claude/plugins/mcp-repo-review/scripts/check-all-servers.sh`

Expected: reports pass/fail for all 55 servers.

- [ ] **Step 5: Push and update PR**

Run: `git push`

The branch already tracks `origin/feature/mcp-repo-review-plugin`, so this pushes all commits to the existing draft PR #3198.

- [ ] **Step 6: Verify PR shows all commits**

Run: `gh pr view 3198 --json commits --jq '.commits | length'`

Expected: 8 commits total (1 spec + 6 implementation + 1 plan).
