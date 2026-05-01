## Default Configuration

This skill is distributed as a **standalone skill** — a self-contained directory that lives
wherever the user installs it (e.g., `~/.claude/skills/dsql/`, `.claude/skills/dsql/`, or an
equivalent directory for other assistants). Because the skill files don't sit at the user's
project root, the skill cannot register the DSQL MCP server automatically — the user must add the
MCP configuration themselves.

A ready-to-copy sample lives alongside this doc: [`.mcp.json`](.mcp.json). Copy its contents into
the user's project-root `.mcp.json` (or the equivalent per-assistant config — see [platform
guides](#coding-assistant---custom-instructions)) to register the DSQL MCP server. The server
provides DSQL documentation search, reading, and recommendations out of the box without requiring
any cluster connection.

To enable database operations (queries, schema exploration, DDL, DML), users must update the config
with their cluster details (see [Database Operation Support Configuration](#database-operation-support-configuration)
below).

### Documentation-Only Config

The skill's MCP configuration is pre-written as follows:

```json
{
  "mcpServers": {
    "awsknowledge": {
      "type": "http",
      "url": "https://knowledge-mcp.global.api.aws"
    },
    "aurora-dsql": {
      "command": "uvx",
      "args": ["awslabs.aurora-dsql-mcp-server@latest"],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" },
    }
  }
}
```

To upgrade to full database operations, add `--cluster_endpoint`, `--region`, `--database_user`, and optionally `--allow-writes` to the args array.

---

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
    "aurora-dsql": {
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
        "[your aws profile name, eg. default]",
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

- Arg: `--profile` or Env: `"AWS_PROFILE"` only need
  to be configured for non-default values.
- Env: `"REGION"` when the cluster region management is
  distinct from user's primary region in project/application.
- Arg: `--allow-writes` based on how permissive the user wants
  to be for the MCP server. Always ask the user if writes
  should be allowed.

## Coding Assistant - Custom Instructions

Before proceeding, identify which coding assistant you are adding the MCP server to and
navigate to those custom instructions.

1. [Claude Code](platforms/claude-code.md)
2. [Gemini](platforms/gemini.md)
3. [Codex](platforms/codex.md)
4. [Kiro](platforms/kiro.md)

## Additional Documentation

- [MCP Server Setup Guide](https://awslabs.github.io/mcp/servers/aurora-dsql-mcp-server)
- [DSQL MCP User Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_aurora-dsql-mcp-server.html)
