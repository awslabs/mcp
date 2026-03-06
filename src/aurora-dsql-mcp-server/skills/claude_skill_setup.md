# DSQL Skill Setup for Claude Code

This guide explains how to add the DSQL skill to Claude Code in your project
from the GitHub repository.

## Prerequisites

- Git installed

## Setup Steps

### 1. Create a base repos directory

```bash
mkdir -p .dsql_skill_repos
```

### 2. Sparse clone the skill from the mcp repository

Clone only the `dsql-skill` folder (no other files):

```bash
cd .dsql_skill_repos
git clone --filter=blob:none --no-checkout https://github.com/awslabs/mcp.git
cd mcp
git sparse-checkout init --cone
git sparse-checkout set src/aurora-dsql-mcp-server/skills/dsql-skill
git checkout
cd ../..
```

### 3. Symlink the skill into the Skills Directory

#### Adding the Skills Directory
```bash
mkdir -p ~/.claude/skills
```

***NOTE: If you want to make this a project-scoped skill, use your project root's `.claude/skills/` directory instead. .***


#### Add symlink:
```bash
ln -s "$(pwd)/.dsql_skill_repos/mcp/src/aurora-dsql-mcp-server/skills/dsql-skill" ~/.claude/skills/dsql-skill
```


### 4. Verify the setup

```bash
# Should show SKILL.md and other skill files
ls -la ~/.claude/skills/dsql-skill/
```

### 5. Verify Skill Use

Once the skill is configured, you should have a new skill command for the named skill: `/dsql`.
You may have to restart Claude Code after adding the skill for it to be detected. You should be able
to use this command from the Claude Code CLI or panel as desired.


## Updating the Skill

To pull the latest changes from the repository:

```bash
cd .dsql_skill_repos/mcp
git pull
```

## Directory Structure

After setup, your project will look like:

```
.dsql_skill_repos/
└── mcp/                              # Sparse git checkout
    └── src/
        └── aurora-dsql-mcp-server/
            └── skills/
                └── dsql-skill/
                    ├── SKILL.md
                    └── ...

~/.claude/
└── skills/
    └── dsql-skill -> /path/to/.dsql_skill_repos/mcp/src/aurora-dsql-mcp-server/skills/dsql-skill
```

## Notes

- Add `.repos/` to your `.gitignore` if you don't want to track it
- The sparse checkout keeps only the skill folder, minimizing disk usage
