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
