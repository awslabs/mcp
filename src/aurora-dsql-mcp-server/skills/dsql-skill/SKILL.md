---
name: dsql
description: Build and deploy PostgreSQL-compatible serverless distributed SQL databases with Aurora DSQL - manage schemas, execute queries, and handle migrations with DSQL-specific requirements. Use when wanting a good solution for developing a scalable or distributed SQL database, user asks to use Amazon Aurora DSQL, or a project is already built with DSQL. Includes MCP tools for direct database interaction.
---

# Amazon Aurora DSQL Skill

Aurora DSQL is a serverless, PostgreSQL-compatible distributed SQL database with specific constraints. This skill provides direct database interaction via MCP tools, schema management, migration support, and multi-tenant patterns.

**Key capabilities:**
- Direct query execution via MCP tools
- Schema management with DSQL constraints
- Migration support and safe schema evolution
- Multi-tenant isolation patterns
- IAM-based authentication

---

## Reference Files

Load these files as needed for detailed guidance:

### [development-guide.md](references/development-guide.md)
**When:** ALWAYS load before implementing schema changes or database operations
**Contains:** DDL rules, connection patterns, transaction limits, security best practices

### MCP:
#### [mcp-setup.md](mcp/mcp-setup.md)
**When:** Load for guidance adding to the DSQL MCP server
**Requires:** An existing cluster endpoint
**Contains:** Instructions for setting up the DSQL MCP server

#### [mcp-tools.md](mcp/mcp-tools.md)
**When:** Load when you need detailed MCP tool syntax and examples
**Contains:** Tool parameters, detailed examples, usage patterns

### [language.md](references/language.md)
**When:** MUST load when making language-specific implementation choices
**Contains:** Driver selection, framework patterns, connection code for Python/JS/Go/Java/Rust

### [dsql-examples.md](references/dsql-examples.md)
**When:** Load when looking for specific implementation examples
**Contains:** Code examples, repository patterns, multi-tenant implementations

### [troubleshooting.md](references/troubleshooting.md)
**When:** Load when debugging errors or unexpected behavior
**Contains:** Common pitfalls, error messages, solutions

### [onboarding.md](references/onboarding.md)
**When:** User explicitly requests to "Get started with DSQL" or similar phrase
**Contains:** Interactive step-by-step guide for new users

---

## MCP Tools Available

The `aurora-dsql` MCP server provides these tools:

**Database Operations:**
1. **readonly_query** - Execute SELECT queries (returns list of dicts)
2. **transact** - Execute DDL/DML statements in transaction (takes list of SQL statements)
3. **get_schema** - Get table structure for a specific table

**Documentation & Knowledge:**
4. **dsql_search_documentation** - Search Aurora DSQL documentation
5. **dsql_read_documentation** - Read specific documentation pages
6. **dsql_recommend** - Get DSQL best practice recommendations

**Note:** There is no `list_tables` tool. Use `readonly_query` with information_schema.

See [mcp-tools.md](references/mcp-tools.md) for detailed usage and examples.

---

## CLI Scripts Available

Bash scripts for cluster management and direct psql connections. All scripts are located in [scripts/](scripts/).

**Cluster Management:**
- **create-cluster.sh** - Create new DSQL cluster with optional tags
- **delete-cluster.sh** - Delete cluster with confirmation prompt
- **list-clusters.sh** - List all clusters in a region
- **cluster-info.sh** - Get detailed cluster information

**Database Connection:**
- **psql-connect.sh** - Connect to DSQL using psql with automatic IAM auth token generation

**Quick example:**
```bash
./scripts/create-cluster.sh --region us-east-1
export CLUSTER=abc123def456
./scripts/psql-connect.sh
```

See [scripts/README.md](scripts/README.md) for detailed usage.

---

## Quick Start

### 1. List tables and explore schema
```
Use readonly_query with information_schema to list tables
Use get_schema to understand table structure
```

### 2. Query data
```
Use readonly_query for SELECT queries
Always include tenant_id in WHERE clause for multi-tenant apps
Validate inputs carefully (no parameterized queries available)
```

### 3. Execute schema changes
```
Use transact tool with list of SQL statements
Follow one-DDL-per-transaction rule
Always use CREATE INDEX ASYNC in separate transaction
```

---

## Common Workflows

### Workflow 1: Create Multi-Tenant Schema

**Goal:** Create a new table with proper tenant isolation

**Steps:**
1. Create main table with tenant_id column using transact
2. Create async index on tenant_id in separate transact call
3. Create composite indexes for common query patterns (separate transact calls)
4. Verify schema with get_schema

**Critical rules:**
- Include tenant_id in all tables
- Use CREATE INDEX ASYNC (never synchronous)
- Each DDL in its own transact call: `transact(["CREATE TABLE ..."])`
- Store arrays/JSON as TEXT

### Workflow 2: Safe Data Migration

**Goal:** Add a new column with defaults safely

**Steps:**
1. Add column using transact: `transact(["ALTER TABLE ... ADD COLUMN ..."])`
2. Populate existing rows with UPDATE in separate transact calls (batched under 3,000 rows)
3. Verify migration with readonly_query using COUNT
4. Create async index for new column using transact if needed

**Critical rules:**
- Add column first, populate later
- Never add DEFAULT in ALTER TABLE
- Batch updates under 3,000 rows in separate transact calls
- Each ALTER TABLE in its own transaction

### Workflow 3: Application-Layer Referential Integrity

**Goal:** Safely insert/delete records with parent-child relationships

**Steps for INSERT:**
1. Validate parent exists with readonly_query
2. Throw error if parent not found
3. Insert child record using transact with parent reference

**Steps for DELETE:**
1. Check for dependent records with readonly_query (COUNT)
2. Return error if dependents exist
3. Delete record using transact if safe

### Workflow 4: Query with Tenant Isolation

**Goal:** Retrieve data scoped to a specific tenant

**Steps:**
1. Always include tenant_id in WHERE clause
2. Validate and sanitize tenant_id input (no parameterized queries available!)
3. Use readonly_query with validated tenant_id
4. Never allow cross-tenant data access

**Critical rules:**
- Validate ALL inputs before building SQL (SQL injection risk!)
- ALL queries include WHERE tenant_id = 'validated-value'
- Reject cross-tenant access at application layer
- Use allowlists or regex validation for tenant IDs

---

## Best Practices

- **SHOULD read guidelines first** - Check [development_guide.md](references/development-guide.md) before making schema changes
- **SHOULD use preferred language patterns** - Check [language.md](references/language.md)
- **SHOULD Execute queries directly** - PREFER MCP tools for ad-hoc queries
- **REQUIRED: Follow DDL Guidelines** - Refer to [DDL Rules](references/development-guide.md#schema-ddl-rules)
- **SHALL repeatedly generate fresh tokens** - Refer to [Connection Limits](references/development-guide.md#connection-rules)
- **ALWAYS use ASYNC indexes** - `CREATE INDEX ASYNC` is mandatory
- **MUST Serialize arrays/JSON as TEXT** - Store arrays/JSON as TEXT (comma separated, JSON.stringify)
- **ALWAYS Batch under 3,000 rows** - maintain transaction limits
- **REQUIRED: Use parameterized queries** - Prevent SQL injection with $1, $2 placeholders
- **MUST follow correct Application Layer Patterns** - when multi-tenant isolation or application referential itegrity are required; refer to [Application Layer Patterns](references/development-guide.md#application-layer-patterns)
- **REQUIRED use DELETE for truncation** - DELETE is the only supported operation for truncation
- **SHOULD test any migrations** - Verify DDL on dev clusters before production
- **Plan for Horizontal Scale** - DSQL is designed to optimize for massive scales without latency drops; refer to [Horizontal Scaling](references/development-guide.md#horizontal-scaling-best-practice)
- **SHOULD use connection pooling in production applications** - Refer to [Connection Pooling](references/development-guide.md#connection-pooling-recommended)
- **SHOULD debug with the troubleshooting guide:** - Always refer to the resources and guidelines in [troubleshooting.md](references/troubleshooting.md)

---

## Additional Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- [Code Samples Repository](https://github.com/aws-samples/aurora-dsql-samples)
- [PostgreSQL Compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [IAM Authentication Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)
- [CloudFormation Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dsql-cluster.html)
