# MCP Setup: Gemini

Part of [MCP Server Setup](../mcp-setup.md). See [General MCP Configuration](../mcp-setup.md#general-mcp-configuration) for the base JSON config.

---

## Gemini

**Check if the MCP server is configured:**
Look for the `aurora-dsql` MCP server:

Gemini CLI command:

```bash
gemini mcp list
```

### Setup Instructions:

#### Choosing the Right Scope

Gemini offers 2 scopes: project (default) and user. _**What scope does the user prefer?**_

1. **Project-Scoped** servers are only accessible from the project's root directory and added to
   the project configuration: `.gemini/settings.json`. Useful for project-specific tools that should
   stay within the codebase.
2. **User-Scoped** servers are accessible from all projects you work on with the Gemini CLI and
   added to global configuration: `~/.gemini/settings.json`

#### Default Installation - Gemini CLI Command

Using the Gemini CLI.

```bash
gemini mcp add \
  --scope $SCOPE \
  --env FASTMCP_LOG_LEVEL="ERROR" \
  aurora-dsql \
  uvx "awslabs.aurora-dsql-mcp-server@latest" \
  -- \
  --cluster_endpoint "[dsql-cluster-id].dsql.[region].on.aws" \
  --region "[dsql cluster region, eg. us-east-1]" \
  --database_user "[your-username]"
```

#### Alternative: Directly edit/update the JSON Configurations

You can also directly configure the MCP adding the [provided MCP json configuration](../mcp-setup.md#general-mcp-configuration)
to `.gemini/settings.json` (project scope) or `~/.gemini/settings.json`

```
{
  ...other fields...
   "mcpServers": {
   }
}
```

#### Troubleshooting and Optional Arguments

**Does the user want to allow writes?**
Add the additional argument flag.

```bash
--allow-writes
```

**Are there multiple AWS credentials configured in the application or environment?**
Add environment variables for AWS Profile and Region for the DSQL cluster to the command.

```bash
--env AWS_PROFILE="[dsql profile, eg. default]" \
--env AWS_REGION="[dsql cluster region, eg. us-east-1]" \
```

### Verification

Restart Gemini CLI.

```bash
gemini mcp list
```

Should see `aurora-dsql` with a `Connected` status.
