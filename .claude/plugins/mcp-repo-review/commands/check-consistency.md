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
