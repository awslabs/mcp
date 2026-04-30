# MCP Setup: Kiro

Part of [MCP Server Setup](../mcp-setup.md). See [General MCP Configuration](../mcp-setup.md#general-mcp-configuration) for the base JSON config.

---

## Kiro

**Check if the MCP server is configured:**

Open the command palette (`Cmd/Ctrl+Shift+P`) and search for `MCP` — the MCP view lists
registered servers. Look for `aurora-dsql`.

### Setup Instructions

#### Choosing the Right Scope

Kiro offers 2 scopes: workspace (default) and user. _**What scope does the user prefer?**_

1. **Workspace-Scoped** servers live at `.kiro/settings/mcp.json` in the project root and are
   only accessible from the current workspace. Useful for project-specific tools that should
   stay within the codebase and can be checked into version control.
2. **User-Scoped** servers live at `~/.kiro/settings/mcp.json` and are accessible across all
   workspaces the user opens in Kiro.

When both files define the same server name, **workspace settings take precedence**.

#### Default Installation - Edit `mcp.json`

Add the MCP configuration to the `mcpServers` object in the appropriate file. Kiro applies
changes automatically on save — no restart required.

```json
{
  "mcpServers": {
    "aurora-dsql": {
      "command": "uvx",
      "args": [
        "awslabs.aurora-dsql-mcp-server@latest",
        "--cluster_endpoint", "[dsql-cluster-id].dsql.[region].on.aws",
        "--region", "[dsql cluster region, eg. us-east-1]",
        "--database_user", "[your-username]"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

#### Kiro-Specific Fields

- `disabled` (bool) — set `true` to suspend a server without deleting its entry
- `autoApprove` (string array) — tool names that skip the per-call approval prompt.
  Leave empty to require approval for every call. For DSQL, keep this empty as a safe
  default so the user approves each `transact` call (which can mutate data).
- `disabledTools` (string array) — hide specific tools from this server
- `env` supports `${VAR}` expansion from the shell environment,
  e.g. `"AWS_PROFILE": "${DSQL_PROFILE}"`

#### Troubleshooting and Optional Arguments

**Does the user want to allow writes?**
Add the additional argument flag to `args`.

```json
"--allow-writes"
```

**Are there multiple AWS credentials configured in the application or environment?**
Add environment variables for AWS Profile and Region for the DSQL cluster to the `env` object.

```json
"env": {
  "FASTMCP_LOG_LEVEL": "ERROR",
  "AWS_PROFILE": "[dsql profile, eg. default]",
  "AWS_REGION": "[dsql cluster region, eg. us-east-1]"
}
```

### Verification

Open the command palette (`Cmd/Ctrl+Shift+P`) → search `MCP` → open the MCP view in the Kiro
panel. The `aurora-dsql` entry should appear in the server list with an active status.
