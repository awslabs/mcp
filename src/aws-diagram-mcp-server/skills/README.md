# Diagram Skills

## Skill Aliases

The following folders are aliases for `diagram-skill` for more accurate domain representation.

| Folder | Skill Name |
|--------|-----------|
| `diagram-skill` | `diagram` (source of truth) |
| `aws-diagram-skill` | `aws diagram` |
| `architecture-diagram-skill` | `architecture diagram` |

Each alias folder contains:
- Its own `SKILL.md` with only the `name` field changed
- Symlinks for `references/`, `examples/`, and `scripts/` pointing back to `diagram-skill/`

## Installation

### Skills CLI

```bash
npx skills add awslabs/mcp --skill diagram
```

### Manual (Claude Code)

```bash
# Sparse clone the skill
mkdir -p .diagram_skill_repos
cd .diagram_skill_repos
git clone --filter=blob:none --no-checkout https://github.com/awslabs/mcp.git
cd mcp
git sparse-checkout init --cone
git sparse-checkout set src/aws-diagram-mcp-server/skills/diagram-skill
git checkout
cd ../..

# Symlink into Claude Code skills directory
mkdir -p ~/.claude/skills
ln -s "$(pwd)/.diagram_skill_repos/mcp/src/aws-diagram-mcp-server/skills/diagram-skill" ~/.claude/skills/diagram-skill
```

For project-scoped installation, use `.claude/skills/` in your project root instead of `~/.claude/skills/`.

### Verify

```bash
ls -la ~/.claude/skills/diagram-skill/
# Should show SKILL.md and other skill files
```

In Claude Code, type `/diagram` -- it should appear in autocomplete.

## Prerequisites

The skill requires:
1. **GraphViz**: `brew install graphviz` (macOS) or `apt-get install graphviz` (Linux)
2. **Python diagrams package**: `pip install diagrams`

Run `scripts/setup.sh` inside the skill directory to check prerequisites.

## Updating

```bash
cd .diagram_skill_repos/mcp
git pull
```
