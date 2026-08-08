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
