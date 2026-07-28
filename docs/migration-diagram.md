# Migration Guide: AWS Diagram MCP Server to Diagram Agent Skill

This guide helps you migrate from `awslabs.aws-diagram-mcp-server` to the [diagram agent skill](https://github.com/awslabs/agent-plugins/tree/main/plugins/deploy-on-aws) in the `deploy-on-aws` plugin.

## Why We're Deprecating

The diagram MCP server wraps the Python `diagrams` package behind a sandboxed MCP tool. The diagram agent skill achieves the same result more directly — Claude Code writes a Python script using the `diagrams` DSL and runs it via Bash. This removes the MCP server overhead and gives the agent full flexibility with the `diagrams` API.

## Before and After

### Before (MCP Server)

1. Configure MCP server in your client settings
2. Server starts, loads sandbox, imports `diagrams`
3. Ask Claude to generate a diagram
4. Claude calls `generate_diagram` tool with Python code
5. Server validates code (AST scan + Bandit), runs in subprocess sandbox
6. Server returns path to generated PNG

### After (Agent Skill)

1. Install the `deploy-on-aws` plugin (includes the diagram skill)
2. Ask Claude to generate a diagram
3. Claude writes a Python script using the `diagrams` DSL
4. Claude runs `python3 diagram.py` via Bash (you approve the execution)
5. PNG is generated in `generated-diagrams/`

## Installing the Skill

### Claude Code Plugin

```bash
claude plugin add awslabs/agent-plugins --plugin deploy-on-aws
```

### Manual Installation

See the [deploy-on-aws plugin README](https://github.com/awslabs/agent-plugins/tree/main/plugins/deploy-on-aws) for manual installation instructions.

## Prerequisites

The skill requires two dependencies installed locally:

1. **GraphViz** (system package providing `dot`):
   - macOS: `brew install graphviz`
   - Ubuntu/Debian: `sudo apt-get install graphviz`
   - Amazon Linux/RHEL: `sudo yum install graphviz`

2. **Python diagrams package**: `pip install diagrams`

Verify: `dot -V && python3 -c "import diagrams; print('OK')"`

> **Note:** The MCP server bundled these dependencies internally. With the skill, you install them on your local machine.

## Tool-by-Tool Migration

### generate_diagram

**MCP server:** Accepted Python code string, validated it through AST scanning and Bandit, ran in a sandboxed subprocess with restricted builtins.

**Skill:** Claude writes the same Python code to a file and runs it with `python3`. No sandbox — you approve the execution via Claude Code's standard Bash permission prompt.

**What changes:**
- No import restrictions — you have full access to the `diagrams` API
- No AST validation — Claude Code's permission model replaces the sandbox
- Output directory: `generated-diagrams/` in your current working directory
- You can inspect the script before approving execution

### get_diagram_examples

**MCP server:** Returned example code for different diagram types (aws, sequence, flow, class, k8s, onprem, custom).

**Skill:** Examples are embedded in the skill's reference files. Claude loads them automatically based on what you're asking for:
- AWS examples: `references/aws-services.md`
- Non-AWS examples: `references/non-aws-providers.md`

### list_icons

**MCP server:** Dynamically inspected the `diagrams` package to list available providers, services, and icons.

**Skill:** Icon reference is documented statically in `references/dsl-syntax.md` (provider import paths) and `references/aws-services.md` (common AWS icons). For a complete listing, run `python3 -c "import diagrams; help(diagrams)"` locally.

## Security Model Change

The MCP server used a 4-layer defense-in-depth approach:

1. **AST scanning** — blocked dangerous constructs (`import os`, `eval`, `exec`)
2. **Bandit analysis** — flagged security anti-patterns
3. **Subprocess isolation** — ran code in a separate process
4. **Restricted builtins** — whitelisted safe Python builtins only

The agent skill replaces all of this with Claude Code's standard permission model:
- Claude writes a Python script you can read
- You approve (or reject) the Bash execution
- The script runs with your normal user permissions

This is the same security model used for all Claude Code Bash operations. If you're comfortable running code through Claude Code, the diagram skill adds no additional risk.

## FAQ

### Do I need to change my diagram code?

No. The same Python `diagrams` DSL works in both the MCP server and the skill. Your existing diagram code is compatible.

### What if I don't have GraphViz installed?

The skill will detect this and prompt you to install it. Without GraphViz, diagram generation will fail (same as the MCP server — GraphViz was bundled inside the server's environment).

### Can I still use the MCP server?

The server remains published on PyPI and will continue to function, but it will not receive updates, bug fixes, or new features.

### What about IDE integrations (VS Code, Cursor, Kiro)?

The MCP server worked across all MCP-compatible clients. The agent skill currently works with Claude Code. For other clients, continue using the MCP server until those clients support agent skills.

## Removing the Old Server

Once you've verified the skill meets your needs:

1. Remove `awslabs.aws-diagram-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.aws-diagram-mcp-server`
3. The old package will remain on PyPI but will not receive updates
