# Aurora DSQL MCP Tools Reference

Detailed reference for the aurora-dsql MCP server tools based on the actual implementation.

## MCP Server Configuration

**Package:** `awslabs.aurora-dsql-mcp-server@latest`
**Connection:** uvx-based MCP server
**Authentication:** AWS IAM credentials with automatic token generation

**Environment Variables:**

- `CLUSTER` - Your DSQL cluster identifier (used to form endpoint)
- `REGION` - AWS region (e.g., "us-east-1")
- `AWS_PROFILE` - AWS CLI profile (optional, uses default if not set)

**Command Line Flags:**

- `--cluster_endpoint` - Full cluster endpoint (e.g., "abc123.dsql.us-east-1.on.aws")
- `--database_user` - Database username (typically "admin")
- `--region` - AWS region
- `--allow-writes` - Enable write operations (required for `transact` tool)
- `--profile` - AWS credentials profile

**Permissions Required:**

- `dsql:DbConnect` - Connect to DSQL cluster
- `dsql:DbConnectAdmin` - Admin access for DDL operations

**Database Name**: Always use `postgres` (only database available in DSQL)

---

## Detailed References

- **[tools/input-validation.md](tools/input-validation.md)** — **MUST** load
  before building any query. Build SQL with `safe_query.build()`, which rejects
  raw strings by construction.
- **[tools/safe_query.py](tools/safe_query.py)** — the validated-query helper
  module.
- **[tools/database-tools.md](tools/database-tools.md)** — readonly_query, transact, get_schema
- **[tools/documentation-tools.md](tools/documentation-tools.md)** — dsql_search_documentation, dsql_read_documentation, dsql_recommend
- **[tools/workflow-patterns.md](tools/workflow-patterns.md)** — Common multi-step workflow patterns

## Additional Resources

- [Aurora DSQL MCP Server Documentation](https://awslabs.github.io/mcp/servers/aurora-dsql-mcp-server)
- [Aurora DSQL MCP Server README](https://github.com/awslabs/mcp/tree/main/src/aurora-dsql-mcp-server)
- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
