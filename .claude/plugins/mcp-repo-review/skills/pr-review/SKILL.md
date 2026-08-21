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
