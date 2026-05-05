# AgentCore Investigation Skill Setup for Kiro CLI

This guide explains how to set up the AgentCore investigation skill with
[Kiro CLI](https://kiro.dev/docs/cli/) from the GitHub repository.

## Prerequisites

- Git installed
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- AWS credentials configured with CloudWatch Logs access
- [Kiro CLI](https://kiro.dev/docs/cli/) installed

## Setup Steps

### 1. Create a base repos directory

```bash
mkdir -p .agentcore_skill_repos
```

### 2. Sparse clone the skill from the mcp repository

Clone only the `agentcore-investigation` skill folder (no other files):

```bash
cd .agentcore_skill_repos
git clone --filter=blob:none --no-checkout https://github.com/awslabs/mcp.git
cd mcp
git sparse-checkout init --cone
git sparse-checkout set src/cloudwatch-mcp-server/skills/agentcore-investigation
git checkout
cd ../..
```

### 3. Symlink the skill into the Kiro skills directory

```bash
mkdir -p ~/.kiro/skills
ln -s "$(pwd)/.agentcore_skill_repos/mcp/src/cloudwatch-mcp-server/skills/agentcore-investigation" \
  ~/.kiro/skills/cloudwatch-agentcore-investigator
```

### 4. Create the Kiro agent definition

Create `~/.kiro/agents/agentcore-investigator.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/aws/amazon-q-developer-cli/refs/heads/main/schemas/agent-v1.json",
  "name": "agentcore-investigator",
  "description": "Investigate AgentCore runtime sessions via CloudWatch Logs Insights",
  "resources": [
    "skill://.kiro/skills/cloudwatch-agentcore-investigator/SKILL.md"
  ],
  "mcpServers": {
    "cloudwatch": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-mcp-server@latest"],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" }
    },
    "cloudwatch-appsignals": {
      "command": "uvx",
      "args": ["awslabs.cloudwatch-applicationsignals-mcp-server@latest"],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" }
    }
  },
  "tools": [
    "fs_read", "fs_write", "execute_bash",
    "@cloudwatch", "@cloudwatch-appsignals"
  ]
}
```

### 5. Launch and verify

```bash
kiro-cli chat --agent agentcore-investigator
```

Test with:
```
investigate session <YOUR_SESSION_ID>
```

The agent should resolve the session ID, run CloudWatch Logs Insights queries, filter OTEL noise, and produce an investigation report.

## Updating the Skill

To pull the latest changes from the repository:

```bash
cd .agentcore_skill_repos/mcp
git pull
```

## Directory Structure

After setup, your environment will look like:

```
.agentcore_skill_repos/
└── mcp/                                    # Sparse git checkout
    └── src/
        └── cloudwatch-mcp-server/
            └── skills/
                └── agentcore-investigation/
                    ├── SKILL.md
                    ├── references/
                    │   └── otel-span-schema.md
                    └── mcp/
                        ├── mcp-setup.md
                        └── .mcp.json

~/.kiro/
├── skills/
│   └── cloudwatch-agentcore-investigator -> /path/to/.agentcore_skill_repos/mcp/src/cloudwatch-mcp-server/skills/agentcore-investigation
└── agents/
    └── agentcore-investigator.json
```

## Notes

- Add `.agentcore_skill_repos/` to your `.gitignore` if you don't want to track it
- The sparse checkout keeps only the skill folder, minimizing disk usage
- The agent definition can be customized — see `mcp/mcp-setup.md` for additional configuration options (model selection, shell restrictions, etc.)
