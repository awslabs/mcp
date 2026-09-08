---
name: distributed sql
description: "Deprecated compatibility redirect for Aurora DSQL guidance. Use when a request concerns DSQL, Aurora DSQL, distributed SQL, DSQL schemas, migrations, queries, authentication, performance, or application development."
---

# Aurora DSQL Skill Moved

This standalone skill is deprecated. The canonical DSQL skill is now:

`plugins/databases-on-aws/skills/dsql/SKILL.md` in
[`awslabs/agent-plugins`](https://github.com/awslabs/agent-plugins).

## Redirect

1. Check whether the canonical `dsql` skill is already available.
2. If it is available, read and follow its `SKILL.md`, then read only the
   references that canonical skill routes to.
3. Do not combine canonical guidance with content from this deprecated
   standalone skill.
4. If the canonical skill is unavailable, explain that the DSQL skill moved
   to `awslabs/agent-plugins`.
5. Get explicit user approval before installing anything or changing user
   configuration.

Repository-reading tools may read the canonical skill to provide advisory
guidance. Reading its repository does not install the plugin, hooks, scripts,
or MCP servers.

For Claude Code, the verified installation commands are:

```text
/plugin marketplace add awslabs/agent-plugins
/plugin install databases-on-aws@agent-plugins-for-aws
```

For Codex and Cursor, use the
[current canonical installation instructions](https://github.com/awslabs/agent-plugins#installation).
