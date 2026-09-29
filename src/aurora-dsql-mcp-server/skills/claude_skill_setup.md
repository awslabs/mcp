# Migrate the DSQL Skill in Claude Code

The standalone DSQL skill from `awslabs/mcp` is deprecated. DSQL guidance now
ships in the `databases-on-aws` plugin from
[`awslabs/agent-plugins`](https://github.com/awslabs/agent-plugins).

## Install the Canonical Plugin

Run these commands in Claude Code:

```text
/plugin marketplace add awslabs/agent-plugins
/plugin install databases-on-aws@agent-plugins-for-aws
```

Restart Claude Code if the newly installed plugin is not detected immediately.

## Remove a Legacy Installation

An older setup may have a `dsql-skill` symlink in `~/.claude/skills/` or
`.claude/skills/` and a sparse checkout such as `.dsql_skill_repos/mcp`.

Inspect those paths first. Get explicit user approval before removing an
existing symlink, checkout, or any other user configuration. The canonical
plugin installation does not require the old checkout.

For other supported clients, follow the
[current canonical installation instructions](https://github.com/awslabs/agent-plugins#installation).
