# AWS Transform MCP Server — Setup & Troubleshooting

This file guides the IDE/CLI agent through verifying and troubleshooting the AWS Transform MCP Server setup.

## When to Use

When a customer reports issues connecting to the AWS Transform MCP Server and the MCP server isn't responding.

## Step 1: Detect Environment

Determine automatically:
- **IDE**: Check which IDE you're running in (VS Code, Kiro, JetBrains)
- **Chat agent**: You already know this — you are the agent (Claude, Copilot, Q, Cline, Kiro)
- **OS**: Detect from environment (macOS, Linux, Windows)

## Step 2: Verify Prerequisites

Run these checks and report results to the customer:

```bash
# Python 3.10+
python3 --version          # macOS/Linux
python --version           # Windows (may use 'python' not 'python3')

# uvx available (recommended runner)
which uvx                  # macOS/Linux
where uvx                  # Windows
```

If any fail, tell the customer:
- **No python3**: "Install Python 3.10+ from https://www.python.org/downloads/"
- **No uvx**: "Install with: `pip install uv` (Windows) or `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux), then restart your terminal"

## Step 3: Check MCP Config

Based on the detected IDE and agent, check the correct config file:

| Agent | Config Location |
|-------|----------------|
| GitHub Copilot | `.vscode/settings.json` (workspace) or User settings: macOS `~/Library/Application Support/Code/User/settings.json`, Linux `~/.config/Code/User/settings.json`, Windows `%APPDATA%\Code\User\settings.json` → `github.copilot.chat.mcpServers` |
| Claude (VS Code) | `.vscode/mcp.json` → `mcpServers` |
| Cline | `.vscode/mcp.json` → `mcpServers` |
| Kiro | `~/.kiro/settings/mcp.json` → `mcpServers` |
| Amazon Q Developer | `~/.aws/amazonq/mcp.json` or `~/.aws/amazonq/default.json` (global), `.amazonq/mcp.json` or `.amazonq/default.json` (workspace) — check only these paths, do NOT search the filesystem |
| Claude Code (CLI) | Run: `claude mcp list` to verify |
| Claude Desktop | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows: `%APPDATA%\Claude\claude_desktop_config.json` |

Read the appropriate file and check if `awslabs.aws-transform-mcp-server` entry exists.

### Expected config (all agents except GitHub Copilot):

**macOS / Linux:**

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

**Windows:**

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false
    }
  }
}
```

### GitHub Copilot (in `.vscode/settings.json`):

**macOS / Linux:**

```json
{
  "github.copilot.chat.mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

**Windows:**

```json
{
  "github.copilot.chat.mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false
    }
  }
}
```

### Amazon Q Developer (via GUI):

Open Q Developer panel → Chat → Tools icon (⚙️) → + → Add STDIO server:
- Name: `awslabs.aws-transform-mcp-server`
- Command: `uvx`
- Args (macOS/Linux): `awslabs.aws-transform-mcp-server@latest`
- Args (Windows): `--from`, `awslabs.aws-transform-mcp-server@latest`, `awslabs.aws-transform-mcp-server.exe`
- Env: `AWS_REGION=us-east-1`, `FASTMCP_LOG_LEVEL=ERROR`

## Step 4: Check VS Code MCP Settings (VS Code only)

If the customer is using VS Code, check these settings that can block MCP servers:

| Setting | Expected Value | Problem if wrong |
|---------|---------------|-----------------|
| `chat.mcp.access` | `"all"` | If `"none"` — all MCP servers blocked |
| `chat.mcp.autostart` | `"newAndOutdated"` | If `"never"` — servers won't auto-start |
| `chat.mcp.apps.enabled` | `true` | If `false` — MCP UI disabled |

Also check for organization policies:
```bash
# macOS
ls "$HOME/Library/Application Support/Code/User/policies/" 2>/dev/null
# Linux
ls "$HOME/.config/Code/User/policies/" 2>/dev/null
# Windows (PowerShell)
ls "$env:APPDATA\Code\User\policies\" 2>$null
# Windows Registry
reg query "HKLM\SOFTWARE\Policies\Microsoft\VSCode" 2>$null
```

If policies exist with MCP restrictions, tell the customer: "Your organization has policies restricting MCP servers. Contact your IT admin to allowlist `awslabs.aws-transform-mcp-server`."

## Step 5: Test Server Startup

```bash
# macOS/Linux
timeout 3 uvx awslabs.aws-transform-mcp-server@latest 2>&1 </dev/null

# Windows (PowerShell)
Start-Process uvx -ArgumentList "awslabs.aws-transform-mcp-server@latest" -NoNewWindow -Wait -PassThru | Stop-Process -Force
```

- If errors appear → report them to customer
- If process starts and waits (no output) → server is working (it expects stdio input)
- If "command not found" → uvx not on PATH, ask customer to use full path or reinstall

## Step 6: Report Findings & Offer to Fix

Present findings as a checklist:

```
MCP Server Setup Check:
✅ Python 3.12 installed
✅ uvx available
✅ AWS credentials valid (account: 123456789)
❌ MCP config missing — no entry found

Would you like me to create the config file for you? I will add the AWS Transform MCP Server entry to <config path>. [Yes / No]
```

**CRITICAL**: Do NOT write any files without explicit customer approval. Always ask first and show exactly what will be written and where.

If customer approves:
- Write the appropriate config to the correct path
- If the file already exists, merge the new entry without overwriting existing servers
- Show the customer what was written

If customer declines:
- Show them the exact config they need to add manually
- Tell them the file path

## Step 7: Post-Fix Verification

After config is in place (whether auto-applied or manual), tell the customer:

```
Config is ready. Please:
1. Restart your IDE completely (Cmd+Q / close all windows — "Reload Window" is NOT sufficient)
2. After restart, type in chat: "Check my AWS Transform connection status"
```

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Server not detected after config added | IDE not restarted | Fully quit and reopen IDE |
| "uvx: command not found" | uvx not on PATH | Use full path `~/.local/bin/uvx` or reinstall uv |
| Server starts but auth fails | AWS creds expired | Run `aws sso login` or refresh credentials |
| "INVALID_SESSION" errors | Cookie expired | Re-authenticate via SSO |
| Copilot doesn't show MCP tools | Wrong config location | Must be in `settings.json` under `github.copilot.chat.mcpServers` |
| Amazon Q doesn't show MCP tools | Server not enabled | Open Q panel → Tools → ensure server is enabled |
| Org policy blocks MCP | IT restriction | Contact admin to allowlist the server |

## Reference

- Documentation: https://pypi.org/project/awslabs.aws-transform-mcp-server/
- Amazon Q MCP docs: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/mcp-ide.html
