## Skill Aliases

The following folders are aliases for `dsql-skill` for more accurate domain
representation.

| Folder | Skill Name |
|--------|-----------|
| `dsql-skill` | `dsql` (source of truth) |
| `aurora-dsql-skill` | `aurora dsql` |
| `amazon-aurora-dsql-skill` | `amazon aurora dsql` |
| `aws-dsql-skill` | `aws dsql` |
| `distributed-sql-skill` | `distributed sql` |
| `distributed-postgres-skill` | `distributed postgres` |

Each alias folder contains:
- Its own `SKILL.md` with only the `name` field changed
- Symlinks for `mcp/`, `references/`, and `scripts/` pointing back to `dsql-skill/`

### Keeping aliases in sync

A pre-commit hook in `src/aurora-dsql-mcp-server/.pre-commit-config.yaml` keeps alias
SKILL.md files in sync when `dsql-skill/SKILL.md` changes. CI enforces this automatically
via the repo's `pre-commit.yml` workflow.

To run locally:

```bash
cd src/aurora-dsql-mcp-server
pre-commit run sync-dsql-skill-aliases --all-files
```
