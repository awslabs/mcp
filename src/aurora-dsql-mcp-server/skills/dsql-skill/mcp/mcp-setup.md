# MCP Server Setup Instructions

## Prerequisites:
```bash
uv --version
```

**If missing:**
- Install from: [Astral](https://docs.astral.sh/uv/getting-started/installation/)

## General MCP Configuration:
Add the following configuration after checking if the user wants documentation-only functionality
or database operation support too.

### Documentation-Only Configuration
```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aurora-dsql-mcp-server@latest"
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

### Database Operation Support Configuration
```json
{
  "mcpServers": {
    "aurora-dsql": {
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

### Optional Arguments and Environment Variables:
The following args and environment variables are not required, but may be required if the user
has custom AWS configurations or would like to allow/disallow the MCP server mutating their database.
* Arg: `--profile` or Env: `"AWS_PROFILE"` only need
  to be configured for non-default values.
* Env: `"REGION"` when the cluster region management is
  distinct from user's primary region in project/application.
* Arg: `--allow-writes` based on how permissive the user wants
  to be for the MCP server. Always ask the user if writes
  should be allowed.

## Coding Assistant - Custom Instructions
Before proceeding, identify which coding assistant you are adding the MCP server to and
navigate to those custom instructions.
1. [Claude Code](#claude-code)
2. [Gemini](#gemini)
3. [Codex](#codex)

## == STOP READING HERE AND PROCEED TO CORRECT SECTION ==

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
choose based on credential sensitivity and need to share. ***What scope does the user prefer?***

1. **Local-scoped** servers represent the default configuration level and are stored in
   `~/.claude.json` under your project’s path. They’re **both** private to you and only accessible
   within the current project directory. This is the default `scope` when creating MCP servers.
2. **Project-scoped** servers **enable team collaboration** while still only being accessible in a
   project directory. Project-scoped servers add a `.mcp.json` file at your project’s root directory.
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

You can also directly configure the MCP adding the [provided MCP json configuration](#mcp-configuration)
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

Add/update the `.mcp.json` file in the project root with the specified MCP configuration,
([sample file](../.mcp.json))

##### User

Update  `~/.claude.json`  at a top-level `mcpServers` field:

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

## Gemini

**Check if the MCP server is configured:**
Look for the `aurora-dsql` MCP server:

Gemini CLI command:
```bash
gemini mcp list
```

### Setup Instructions:

#### Choosing the Right Scope

Gemini offers 2 scopes: project (default) and user. ***What scope does the user prefer?***

1. **Project-Scoped** servers are only accessible from the project's root directory and added to
   the project configuation: `.gemini/settings.json`. Useful for project-specific tools that should
   stay wthin the codebase.
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

You can also directly configure the MCP adding the [provided MCP json configuration](#mcp-configuration)
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
configuration file. Each MCP server is configured with a [mcp_servers.<server-name>] table in the
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

## Additional Documentation
- [MCP Server Setup Guide](https://awslabs.github.io/mcp/servers/aurora-dsql-mcp-server)
- [DSQL MCP User Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_aurora-dsql-mcp-server.html)
