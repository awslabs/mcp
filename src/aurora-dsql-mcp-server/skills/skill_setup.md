# DSQL Skill Setup

This guide explains how to add the DSQL skill to your project from the GitHub repository.

## Prerequisites

- Git installed

## Setup Steps

### 1. Create a base repos directory

```bash
mkdir -p .repos
```

### 2. Sparse clone the skill from the starter-kit repository

Clone only the `ai-rules/dsql-skill` folder (no other files):

```bash
cd .repos
git clone --filter=blob:none --no-checkout https://github.com/awslabs/aurora-dsql-starter-kit.git
cd aurora-dsql-starter-kit
git sparse-checkout init --cone
git sparse-checkout set ai-rules/dsql-skill
git checkout
cd ../..
```

### 3. Symlink the skill into the Skills Directory

#### Adding the Skills Directory
```bash
mkdir -p .claude/skills
```

***NOTE: If you want to make this a global skill, this should be your top-level `~/.claude/skills.` directory.***


#### Add symlink:
```bash
ln -s "/path/to/.repos/aurora-dsql-starter-kit/ai-rules/dsql-skill" /path/to/.claude/skills/dsql-skill
```


### 4. Verify the setup

```bash
# Should show SKILL.md and other skill files
ls -la .claude/skills/dsql-skill/
```

### 5. Verify Skill Use

Once the skill is configured, you should have a new skill command for the named skill: `/dsql`.
You may have to restart Claude Code after adding the skill for it to be detected. You should be able
to use this command from the Claude Code CLI or panel as desired.


## Updating the Skill

To pull the latest changes from the repository:

```bash
cd .repos/aurora-dsql-starter-kit
git pull
```

## Directory Structure

After setup, your project will look like:

```
your-project/
├── .repos/
│   └── aurora-dsql-starter-kit/    # Sparse git checkout
│       └── ai-rules/
│           └── dsql-skill/
│               ├── SKILL.md
│               └── ...
├── .claude/
│   └── skills/
│       └── dsql-skill -> ../../.repos/.../dsql-skill  # Symlink
└── ...
```

## Notes

- Add `.repos/` to your `.gitignore` if you don't want to track it
- The sparse checkout keeps only the skill folder, minimizing disk usage
