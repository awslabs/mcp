---
name: distributed sql
description: Build with Aurora DSQL - manage schemas, execute queries, and handle migrations with DSQL-specific requirements. Use when developing a scalable or distributed database/application or user requests DSQL.
---

# Amazon Aurora DSQL Skill

Aurora DSQL is a serverless, PostgreSQL-compatible distributed SQL database. This skill provides direct database interaction via MCP tools, schema management, migration support, and multi-tenant patterns.

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
**When:** Always load for guidance using or updating the DSQL MCP server
**Contains:** Instructions for setting up the DSQL MCP server with 2 configuration options as
sampled in [.mcp.json](mcp/.mcp.json)
1. Documentation-Tools Only
2. Database Operations (requires a cluster endpoint)

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

### [access-control.md](references/access-control.md)
**When:** MUST load when creating database roles, granting permissions, setting up schemas for applications, or handling sensitive data
**Contains:** Scoped role setup, IAM-to-database role mapping, schema separation for sensitive data, role design patterns

### [ddl-migrations.md](references/ddl-migrations.md)
**When:** MUST load when trying to perform DROP COLUMN, RENAME COLUMN, ALTER COLUMN TYPE, or DROP CONSTRAINT functionality
**Contains:** Table recreation patterns, batched migration for large tables, data validation

### [mysql-to-dsql-migrations.md](references/mysql-to-dsql-migrations.md)
**When:** MUST load when migrating from MySQL to DSQL or translating MySQL DDL to DSQL-compatible equivalents
**Contains:** MySQL data type mappings, DDL operation translations, AUTO_INCREMENT/ENUM/SET/FOREIGN KEY migration patterns, ALTER TABLE ALTER COLUMN and DROP COLUMN via table recreation

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

See [mcp-setup.md](mcp/mcp-setup.md) for detailed setup instructions.
See [mcp-tools.md](mcp/mcp-tools.md) for detailed usage and examples.

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

### Workflow 5: Set Up Scoped Database Roles

**Goal:** Create application-specific database roles instead of using the `admin` role

**MUST load [access-control.md](references/access-control.md) for detailed guidance.**

**Steps:**
1. Connect as `admin` (the only time admin should be used)
2. Create database roles with `CREATE ROLE <name> WITH LOGIN`
3. Create an IAM role with `dsql:DbConnect` for each database role
4. Map database roles to IAM roles with `AWS IAM GRANT`
5. Create dedicated schemas for sensitive data (e.g., `users_schema`)
6. Grant schema and table permissions per role
7. Applications connect using `generate-db-connect-auth-token` (not the admin variant)

**Critical rules:**
- ALWAYS use scoped database roles for application connections
- MUST place user PII and sensitive data in dedicated schemas, not `public`
- ALWAYS use `dsql:DbConnect` for application IAM roles
- SHOULD create separate roles per service component (read-only, read-write, user service, etc.)

### Workflow 6: Table Recreation DDL Migration

**Goal:** Perform DROP COLUMN, RENAME COLUMN, ALTER COLUMN TYPE, or DROP CONSTRAINT using the table recreation pattern.

**MUST load [ddl-migrations.md](references/ddl-migrations.md) for detailed guidance.**

**Steps:**
1. MUST validate table exists and get row count with `readonly_query`
2. MUST get current schema with `get_schema`
3. MUST create new table with desired structure using `transact`
4. MUST migrate data (batched in 500-1,000 row chunks for tables > 3,000 rows)
5. MUST verify row counts match before proceeding
6. MUST swap tables: drop original, rename new
7. MUST recreate indexes using `CREATE INDEX ASYNC`

**Rules:**
- MUST use batching for tables exceeding 3,000 rows
- PREFER batches of 500-1,000 rows for optimal throughput
- MUST validate data compatibility before type changes (abort if incompatible)
- MUST NOT drop original table until new table is verified
- MUST recreate all indexes after table swap using ASYNC

### Workflow 6: MySQL to DSQL Schema Migration

**Goal:** Migrate MySQL table schemas and DDL operations to DSQL-compatible equivalents, including data type mapping, ALTER TABLE ALTER COLUMN, and DROP COLUMN operations.

**MUST load [mysql-to-dsql-migrations.md](references/mysql-to-dsql-migrations.md) for detailed guidance.**

**Steps:**
1. MUST map all MySQL data types to DSQL equivalents (e.g., AUTO_INCREMENT → UUID/IDENTITY/SEQUENCE, ENUM → VARCHAR with CHECK, JSON → TEXT)
2. MUST remove MySQL-specific features (ENGINE, FOREIGN KEY, ON UPDATE CURRENT_TIMESTAMP, FULLTEXT INDEX)
3. MUST implement application-layer replacements for removed features (referential integrity, timestamp updates)
4. For `ALTER TABLE ... ALTER COLUMN col datatype` or `MODIFY COLUMN`: MUST use table recreation pattern
5. For `ALTER TABLE ... DROP COLUMN col`: MUST use table recreation pattern
6. MUST convert all index creation to `CREATE INDEX ASYNC` in separate transactions
7. MUST validate data compatibility before type changes (abort if incompatible)

**Rules:**
- MUST use table recreation pattern for ALTER COLUMN and DROP COLUMN (not directly supported)
- MUST replace FOREIGN KEY with application-layer referential integrity
- MUST replace ENUM with VARCHAR and CHECK constraint
- MUST replace SET with TEXT (comma-separated)
- MUST replace JSON columns with TEXT
- MUST convert AUTO_INCREMENT to UUID, IDENTITY column, or SEQUENCE (SERIAL not supported)
- MUST replace UNSIGNED integers with CHECK (col >= 0)
- MUST use batching for tables exceeding 3,000 rows
- MUST NOT drop original table until new table is verified

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
- **REQUIRED: Sanitize SQL inputs with allowlists, regex, and quote escaping** - See [Input Validation](mcp/mcp-tools.md#input-validation-critical)
- **MUST follow correct Application Layer Patterns** - when multi-tenant isolation or application referential itegrity are required; refer to [Application Layer Patterns](references/development-guide.md#application-layer-patterns)
- **REQUIRED use DELETE for truncation** - DELETE is the only supported operation for truncation
- **SHOULD test any migrations** - Verify DDL on dev clusters before production
- **Plan for Horizontal Scale** - DSQL is designed to optimize for massive scales without latency drops; refer to [Horizontal Scaling](references/development-guide.md#horizontal-scaling-best-practice)
- **SHOULD use connection pooling in production applications** - Refer to [Connection Pooling](references/development-guide.md#connection-pooling-recommended)
- **SHOULD debug with the troubleshooting guide:** - Always refer to the resources and guidelines in [troubleshooting.md](references/troubleshooting.md)
- **ALWAYS use scoped roles for applications** - Create database roles with `dsql:DbConnect`; refer to [Access Control](references/access-control.md)

---

## Additional Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- [Code Samples Repository](https://github.com/aws-samples/aurora-dsql-samples)
- [PostgreSQL Compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [IAM Authentication Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)
- [CloudFormation Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dsql-cluster.html)
