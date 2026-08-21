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
