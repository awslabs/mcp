# Kiro MCP Setup Configuration

## Prerequisites:
```bash
uv --version
```

**If missing:**
- Install from: [Astral](https://docs.astral.sh/uv/getting-started/installation/)

**Check if MCP server is configured:**
- Look for `aurora-dsql-mcp-server` in MCP settings

**If not configured, offer to set up:**

Edit the appropriate MCP settings file.

## Where to keep the MCP Configuration?
Would the user like a global MCP configuration or a project-scoped MCP configuration?

**Default:**
By default, the power has a placeholder MCP configuration globally.

```bash
cat ~/.kiro/settings/mcp.json
```

The user can update the MCP settings any time by navigating to the Kiro panel from
the left sidebar (Kiro's ghost icon) and navigating to the bottom "MCP Servers" pane.

**Global Scope:**
1. Locate `~/.kiro/settings/mcp.json`
2. Identify the `"powers"` field and find the `power-aurora-dsql-aurora-dsql` in the
   list of MCP servers.
3. Update the configuration args for the cluster endpoint, region, and database
   user (default to admin).
4. Update the environment variables if necessary (`"env"` field):
   1. Is the cluster region different than the default region?
      Set the environment variable `"REGION"`
   2. Is the user using an AWS Profile other than `default`?
      List AWS profiles with:
      ```bash
      aws configure list-profiles
      ```
      For a non-default profile, configure the environment variable:
      `"AWS_PROFILE"`.
5. How permissive is the user? Is the MCP server permitted to write
   to the database? If not, remove the `--allow-writes` flag from the
   arguments in the MCP configuration.

**Project-Scope**:
1. Recommend disabling the power's global MCP server: `"disabled": true`
2. Locate or create a `.kiro/settings` directory in the project workspace:
   ```bash
   mkdir -p .kiro/settings
   ```
3. Create a local `.kiro/settings/mcp.json` and add the Aurora DSQL MCP
   server as specified in [MCP Configuration](#mcp-configuration).
   1. Optional Arguments/Environment Variables:
      * Arg: `--profile` or Env: `"AWS_PROFILE"` only need
        to be configured for non-default values.
      * Env: `"REGION"` when the cluster region management is
        distinct from user's primary region in project/application.
      * Arg: `--allow-writes` based on how permissive the user wants
        to be for the MCP server. Always ask the user if writes
        should be allowed.

## MCP Configuration:
Add the following configuration:

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aurora-dsql-mcp-server@latest",
        "--cluster_endpoint",
        "[your dsql cluster endpoint, e.g. abcdefghijklmnopqrst234567.dsql.us-east-1.on.aws]",
        "--region",
        "[your dsql cluster region, e.g. us-east-1]",
        "--database_user",
        "[your dsql username, e.g. admin]",
        "--profile",
        "[your aws profile name, eg. default]"
        "--allow-writes"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "REGION": "[your dsql cluster region, eg. us-east-1, only when necessary]",
        "AWS_PROFILE": "[your aws profile name, eg. default]"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Documentation:**
- [MCP Server Setup Guide](https://awslabs.github.io/mcp/servers/aurora-dsql-mcp-server)
- [AWS User Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_aurora-dsql-mcp-server.html)
