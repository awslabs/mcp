## Deprecated Compatibility Aliases

The standalone DSQL skill in `awslabs/mcp` is deprecated. The canonical skill
is now
[`plugins/databases-on-aws/skills/dsql`](https://github.com/awslabs/agent-plugins/tree/main/plugins/databases-on-aws/skills/dsql)
in `awslabs/agent-plugins`.

These directories remain only as deprecated compatibility aliases:

| Folder | Skill Name |
|--------|-----------|
| `dsql-skill` | `dsql` |
| `aurora-dsql-skill` | `aurora dsql` |
| `amazon-aurora-dsql-skill` | `amazon aurora dsql` |
| `aws-dsql-skill` | `aws dsql` |
| `distributed-sql-skill` | `distributed sql` |
| `distributed-postgres-skill` | `distributed postgres` |

Each directory contains only a redirect `SKILL.md`. The redirects preserve the
legacy names, point agents to the canonical skill, and require user approval
before installation or configuration changes.

The package pre-commit hooks keep the six redirect files synchronized and
verify that no standalone skill content is reintroduced.
