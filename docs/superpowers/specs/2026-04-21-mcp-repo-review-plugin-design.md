# MCP Repo Review Plugin — Design Spec

**Date:** 2026-04-21
**Status:** Approved
**Scope:** Claude Code project-level plugin for reviewing the awslabs/mcp monorepo

## Overview

A shared Claude Code plugin at `.claude/plugins/mcp-repo-review/` that provides PR review, individual server audits, and cross-repo consistency checks for the 55-server awslabs/mcp Python monorepo. The plugin composes with official Claude Code plugins (`pr-review-toolkit`, `code-review`) for general-purpose review machinery and adds repo-specific knowledge on top.

## Goals

1. Enforce repo conventions from `DESIGN_GUIDELINES.md` and `DEVELOPER_GUIDE.md` during development
2. Enable deep audits of individual MCP server packages
3. Detect consistency drift across the 55 servers in the monorepo
4. Provide an extensible structure for future skills (starting with a "no wrapper" requirement)
5. Separate shared config (committed) from per-user credentials (gitignored)

## Directory Structure

```
.claude/
├── settings.json                          # Shared config — enables plugin + shared permissions
├── settings.local.json                    # Per-user — credentials, personal preferences (gitignored)
└── plugins/
    └── mcp-repo-review/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── commands/
        │   ├── repo-review-pr.md
        │   ├── audit-server.md
        │   └── check-consistency.md
        ├── agents/
        │   ├── guidelines-reviewer.md
        │   ├── security-auditor.md
        │   └── consistency-checker.md
        ├── skills/
        │   ├── pr-review/
        │   │   ├── SKILL.md
        │   │   └── references/
        │   │       └── review-checklist.md
        │   ├── server-audit/
        │   │   ├── SKILL.md
        │   │   └── references/
        │   │       └── audit-criteria.md
        │   ├── consistency-check/
        │   │   ├── SKILL.md
        │   │   └── references/
        │   │       └── conventions.md
        │   └── no-wrapper/
        │       └── SKILL.md
        ├── hooks/
        │   ├── hooks.json
        │   └── scripts/
        │       └── validate-server-structure.sh
        ├── .mcp.json
        └── scripts/
            ├── check-all-servers.sh
            └── server-conventions.py
```

## Plugin Manifest

`.claude-plugin/plugin.json`:

```json
{
  "name": "mcp-repo-review",
  "version": "0.1.0",
  "description": "Review tooling for the awslabs/mcp monorepo — PR review, server audits, and cross-repo consistency checks",
  "license": "Apache-2.0"
}
```

## Composition with Official Plugins

The custom plugin provides repo-specific knowledge. Official plugins provide general-purpose review machinery.

| Concern | This plugin | Official plugin |
|---|---|---|
| PR review | Repo-specific checklist: DESIGN_GUIDELINES.md adherence, naming conventions, pyproject.toml structure, license headers | `pr-review-toolkit:review-pr` — general code review agents (code-reviewer, silent-failure-hunter, type-design-analyzer) |
| Security audit | AWS-specific patterns: IAM auth, credential handling, boto3 patterns, controlled execution environments | `code-review:code-review` — general security and quality review |
| Consistency | Cross-server convention validation (all 55 servers follow same structure) | No official equivalent — fully custom |

## Commands

### `/repo-review-pr`

Runs the official `pr-review-toolkit:review-pr` skill first, then layers repo-specific checks:
- DESIGN_GUIDELINES.md structure compliance
- License headers present on all source files
- pyproject.toml follows `awslabs.*` naming convention
- Tool names under 64 characters and consistently cased within server
- Entry point defined only in `server.py`

### `/audit-server`

Takes a server name argument. Runs a deep audit of a single `src/*-mcp-server/` package:
- Structure validation against DESIGN_GUIDELINES.md expected layout
- Test coverage check via `uv run --frozen pytest --cov --cov-branch`
- Security scan via semgrep MCP server
- Composes with `code-review:code-review` for general quality
- Checks docstrings, Field descriptions, async patterns

### `/check-consistency`

Fully custom — no official plugin equivalent. Iterates all `src/*-mcp-server/` directories and checks:
- pyproject.toml structure (name, version, entry points, commitizen config)
- `__init__.py` version sync with pyproject.toml
- License headers on all `.py` files
- README format consistency
- Entry point conventions (`server.py` with `main()`)
- Package directory structure (`awslabs/` namespace)

Reports deviations as a table.

## Agents

### `guidelines-reviewer`

Specialized knowledge of `DESIGN_GUIDELINES.md` and `DEVELOPER_GUIDE.md`. Understands:
- Expected project structure
- Package naming and versioning conventions
- Field guidelines for MCP tool parameters
- Tool naming conventions (snake_case recommended, 64-char limit)
- Response formatting, error handling, logging patterns

### `security-auditor`

Focuses on security patterns specific to this repo:
- boto3 authentication (AWS_PROFILE + default credentials)
- Controlled execution environments (namespace isolation, timeout handlers)
- Explicit allowlists for permitted operations
- Code security scanning patterns (AST + bandit)
- Input validation for MCP tool parameters

Complements official review plugins rather than duplicating them.

### `consistency-checker`

Knows the expected monorepo structure for all 55 servers. Validates:
- Uniform pyproject.toml fields across servers
- Consistent use of ruff, pre-commit, and pytest
- Version synchronization patterns
- Entry point conventions
- Documentation format

## Skills

### `pr-review/SKILL.md`

**Triggers when:** Reviewing PRs in this repository.
**Provides:** Repo-specific review checklist from `references/review-checklist.md` encoding criteria from DESIGN_GUIDELINES.md.

### `server-audit/SKILL.md`

**Triggers when:** Working within a specific `src/*-mcp-server/` directory.
**Provides:** Expected file layout, quality criteria, and audit steps from `references/audit-criteria.md`.

### `consistency-check/SKILL.md`

**Triggers when:** Doing cross-repo analysis or asking about conventions across servers.
**Provides:** Convention rules from `references/conventions.md` covering all 55 servers.

### `no-wrapper/SKILL.md`

**Triggers when:** TBD — placeholder for future "no wrapper" requirement.
**Provides:** Structure is ready; content to be filled in after directory structure is complete.

## Hooks

### `hooks/hooks.json`

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

Design principles:
- **PreToolUse (Write|Edit):** Blocks only on clear structural violations. Silent on pass.
- **Stop:** Advisory test reminder. Never blocks.
- Heavy review work stays in explicitly invoked commands, not hooks.
- Semgrep not in hooks due to false-positive noise — available on-demand via `/audit-server`.

### Helper Script: `hooks/scripts/validate-server-structure.sh`

Fast structural check for MCP server directories. Validates:
- Required files exist (pyproject.toml, README.md, LICENSE)
- `awslabs/` package directory exists
- `tests/` directory exists

Used by agents and commands as a utility. Exit code = number of errors.

## MCP Servers (`.mcp.json`)

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

Minimal for now. Semgrep is also available via the official semgrep plugin. This is the extension point for adding future review-specific MCP servers.

## Shared Scripts

### `scripts/check-all-servers.sh`

Iterates all `src/*-mcp-server/` directories and runs `validate-server-structure.sh` on each. Used by `/check-consistency` command.

### `scripts/server-conventions.py`

Python script for deeper convention checks:
- pyproject.toml field validation (name format, version, entry points, commitizen config)
- Version sync between pyproject.toml and `__init__.py`
- Entry point naming conventions
- License header presence on `.py` files

Used by the `consistency-checker` agent.

## Configuration

### `settings.json` (committed, shared)

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

### `settings.local.json` (gitignored, per-user)

Retains existing content (gh pr, gh api, pip3 show permissions). Contributors add their own AWS_PROFILE and other credentials here.

### `.gitignore` addition

```
.claude/settings.local.json
.worktrees/
```

## Future Extensibility

- **New skills:** Add a new subdirectory under `skills/` with a `SKILL.md`. Auto-discovered.
- **New commands:** Drop a `.md` file in `commands/`. Auto-discovered.
- **New agents:** Drop a `.md` file in `agents/`. Auto-discovered.
- **New MCP servers:** Add entries to `.mcp.json`.
- **New hooks:** Add event entries to `hooks/hooks.json`.
- **"No wrapper" requirement:** `skills/no-wrapper/SKILL.md` is ready to be filled in.
