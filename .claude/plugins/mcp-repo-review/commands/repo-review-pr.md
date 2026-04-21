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
