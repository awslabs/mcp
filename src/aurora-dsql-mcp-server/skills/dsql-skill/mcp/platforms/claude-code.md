# MCP Setup: Claude Code

Part of [MCP Server Setup](../mcp-setup.md). See [General MCP Configuration](../mcp-setup.md#general-mcp-configuration) for the base JSON config.

---

## Claude Code

**Check if MCP server is configured:**
Look for `aurora-dsql` in MCP settings in either `~/.claude.json` or in a `.mcp.json`
file in the project root.

**If not configured, offer to set up:**

Edit the appropriate MCP settings file as outlined below.

### Claude Code CLI

Check if the Claude CLI is installed:

```bash
claude --version
```

If present, prefer [default installation](#default-installation---claude-code-cli-command).
If missing, prefer [alternative installation](#alternative-directly-editupdate-the-json-configurations)

### Setup Instructions:

#### Choosing the Right Scope

Claude Code offers 3 different scopes: local (default), project, and user and details which scope to
choose based on credential sensitivity and need to share. _**What scope does the user prefer?**_

1. **Local-scoped** servers represent the default configuration level and are stored in
   `~/.claude.json` under your project's path. They're **both** private to you and only accessible
   within the current project directory. This is the default `scope` when creating MCP servers.
2. **Project-scoped** servers **enable team collaboration** while still only being accessible in a
   project directory. Project-scoped servers add a `.mcp.json` file at your project's root directory.
   This file is designed to be checked into version control, ensuring all team members have access
   to the same MCP tools and services. When you add a project-scoped server, Claude Code automatically
   creates or updates this file with the appropriate configuration structure.
3. **User-scoped** servers are stored in `~/.claude.json` and are available across all projects on
   your machine while remaining **private to your user account.**

#### Default Installation - Claude Code CLI Command

Use the Claude Code CLI.

```bash
claude mcp add aurora-dsql \
  --scope $SCOPE \
  --env FASTMCP_LOG_LEVEL="ERROR" \
  -- uvx "awslabs.aurora-dsql-mcp-server@latest" \
  --cluster_endpoint "[dsql-cluster-id].dsql.[region].on.aws" \
  --region "[dsql cluster region, eg. us-east-1]" \
  --database_user "[your-username]"
```

**Does the user want to allow writes?**
Add the additional argument flag.

```bash
--allow-writes
```

##### **Troubleshooting: Using Claude Code with Bedrock on a different AWS Account**

If Claude Code is configured with a Bedrock AWS account or profile that is distinct from the profile
needed to connect to your dsql cluster, additional environment variables are required:

```
--env AWS_PROFILE="[dsql profile, eg. default]" \
--env AWS_REGION="[dsql cluster region, eg. us-east-1]" \
```

#### Alternative: Directly edit/update the JSON Configurations

You can also directly configure the MCP adding the [provided MCP json configuration](../mcp-setup.md#general-mcp-configuration)
to the (new or existing) relevant json file and field by scope.

##### Local

Update `~/.claude.json` within the project-specific `mcpServers` field:

```
{
   "projects": {
       "/path/to/project": {
           "mcpServers": {}
       }
   }
}
```

##### Project

Add/update the `.mcp.json` file in the project root with the specified MCP configuration. A
ready-to-copy sample lives inside the skill: [sample `.mcp.json`](../.mcp.json).

##### User

Update `~/.claude.json` at a top-level `mcpServers` field:

```
{
   "mcpServers": {}
}
```

### Verification

After setup, verify the MCP server status. You may need to restart your Claude Code session. You should see the `amazon-aurora-dsql` server listed with its current status.

```
claude mcp list
```
