# MCP Setup: Codex

Part of [MCP Server Setup](../mcp-setup.md). See [General MCP Configuration](../mcp-setup.md#general-mcp-configuration) for the base JSON config.

---

## Codex

**Check if the MCP server is configured:**

Look for `aurora-dsql` in the TUI

```bash
/mcp
```

### Setup Instructions

#### Default Installation - Codex CLI

Using the Codex CLI:

```bash
codex mcp add aurora-dsql \
  --env FASTMCP_LOG_LEVEL="ERROR" \
  -- uvx "awslabs.aurora-dsql-mcp-server@latest" \
  --cluster_endpoint "[dsql-cluster-id].dsql.[region].on.aws" \
  --region "[dsql cluster region, eg. us-east-1]" \
  --database_user "[your-username]"
```

#### Alternative: Directly modifying `config.toml`

For more fine grained control over MCP server options, you can manually edit the `~/.codex/config.toml`
configuration file. Each MCP server is configured with a `[mcp_servers.<server-name>]` table in the
config file.

```
[mcp_servers.amazon-aurora-dsql]
command = "uvx"
args = [
  "awslabs.aurora-dsql-mcp-server@latest",
  "--cluster_endpoint", "<DSQL_CLUSTER_ID>.dsql.<AWS_REGION>.on.aws",
  "--region", "<AWS_REGION>",
  "--database_user", "<DATABASE_USERNAME>"
]

[mcp_servers.amazon-aurora-dsql.env]
FASTMCP_LOG_LEVEL = "ERROR"
```

#### Troubleshooting and Optional Arguments

**Does the user want to allow writes?**
Add the additional argument flag.

```bash
--allow-writes
```

**Are there multiple AWS credentials configured in the application or environment?**
Add environment variables for AWS Profile and Region for the DSQL cluster to the command.

```
AWS_PROFILE = "[dsql profile, eg. default]" \
AWS_REGION = "[dsql cluster region, eg. us-east-1]" \
```
