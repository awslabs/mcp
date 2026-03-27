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

## Database Operation Tools

### 1. readonly_query - Execute read-only SQL queries

**Use for:** SELECT queries, data exploration, ad-hoc analysis

**Parameters:**
- `sql` (string, required) - SQL query to run

**Returns:** List of dictionaries containing query results

**Security:**
- Automatically prevents mutating keywords (INSERT, UPDATE, DELETE, etc.)
- Checks for SQL injection risks
- Prevents transaction bypass attempts

**Examples:**

```sql
-- Simple SELECT
SELECT * FROM entities WHERE tenant_id = 'tenant-123' LIMIT 10

-- Aggregate query
SELECT tenant_id, COUNT(*) as count FROM objectives GROUP BY tenant_id

-- Join query
SELECT e.entity_id, e.name, o.title
FROM entities e
INNER JOIN objectives o ON e.entity_id = o.entity_id
WHERE e.tenant_id = 'tenant-123'
```

**Note:** Parameterized queries ($1, $2) are NOT supported by this MCP tool. Use string interpolation carefully and validate inputs to prevent SQL injection.

---

### 2. transact - Execute write operations in a transaction

**Use for:** INSERT, UPDATE, DELETE, CREATE TABLE, ALTER TABLE

**Parameters:**
- `sql_list` (List[string], required) - **List of SQL statements** to execute in a transaction

**Returns:** List of dictionaries with execution results

**Requirements:**
- Server must be started with `--allow-writes` flag
- Cannot be used in read-only mode

**Behavior:**
- Automatically wraps statements in BEGIN/COMMIT
- Rolls back on any error
- All statements execute atomically

**Examples:**

```python
# Single DDL statement (still needs to be in a list)
["CREATE TABLE IF NOT EXISTS entities (...)"]

# Create table with index (two separate statements)
[
  "CREATE TABLE IF NOT EXISTS entities (...)",
  "CREATE INDEX ASYNC idx_entities_tenant ON entities(tenant_id)"
]

# Insert multiple rows in one transaction
[
  "INSERT INTO entities (entity_id, tenant_id, name) VALUES ('e1', 't1', 'Entity 1')",
  "INSERT INTO entities (entity_id, tenant_id, name) VALUES ('e2', 't1', 'Entity 2')",
  "INSERT INTO entities (entity_id, tenant_id, name) VALUES ('e3', 't1', 'Entity 3')"
]

# Safe migration pattern
[
  "ALTER TABLE entities ADD COLUMN status VARCHAR(50)"
]
# Then in a separate transaction:
[
  "UPDATE entities SET status = 'active' WHERE status IS NULL AND tenant_id = 'tenant-123'"
]

# Batch update
[
  "UPDATE entities SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE tenant_id = 'tenant-123' AND created_at < '2024-01-01'"
]
```

**Important Notes:**
- Each ALTER TABLE must be in its own transaction (DSQL limitation)
- Keep transactions under 3,000 rows and 10 MiB
- For large batch operations, split into multiple transact calls
- Cannot use parameterized queries - validate inputs before building SQL strings

---

### 3. get_schema - Get table schema details

**Use for:** Understanding table structure, planning migrations, exploring database

**Parameters:**
- `table_name` (string, required) - Name of table to inspect

**Returns:** List of dictionaries with column information (name, type, nullable, default, etc.)

**Example:**

```python
# Get schema for entities table
table_name = "entities"

# Returns column definitions like:
# [
#   {"column_name": "entity_id", "data_type": "character varying", "is_nullable": "NO", ...},
#   {"column_name": "tenant_id", "data_type": "character varying", "is_nullable": "NO", ...},
#   ...
# ]
```

**Note:** There is no `list_tables` tool. To discover tables, use `readonly_query` with:
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
```

---

## Documentation and Knowledge Tools

### 4. dsql_search_documentation - Search Aurora DSQL documentation

**Use for:** Finding relevant documentation, looking up features, troubleshooting

**Parameters:**
- `search_phrase` (string, required) - Search query
- `limit` (int, optional) - Maximum number of results

**Returns:** Dictionary of search results with URLs and snippets

**Example:**
```python
search_phrase = "foreign key constraints"
limit = 5
```

---

### 5. dsql_read_documentation - Read specific DSQL documentation pages

**Use for:** Retrieving detailed documentation content

**Parameters:**
- `url` (string, required) - URL of documentation page
- `start_index` (int, optional) - Starting character index
- `max_length` (int, optional) - Maximum characters to return

**Returns:** Dictionary with documentation content

**Example:**
```python
url = "https://docs.aws.amazon.com/aurora-dsql/latest/userguide/..."
start_index = 0
max_length = 5000
```

---

### 6. dsql_recommend - Get DSQL best practice recommendations

**Use for:** Getting contextual recommendations for DSQL usage

**Parameters:**
- `url` (string, required) - URL of documentation page to get recommendations for

**Returns:** Dictionary with recommendations

---

## Common Workflow Patterns

### Pattern 1: Explore Schema

```python
# Step 1: List all tables
readonly_query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")

# Step 2: Get schema for specific table
get_schema("entities")

# Step 3: Query data
readonly_query("SELECT * FROM entities LIMIT 10")
```

### Pattern 2: Create Table with Index

```python
# WRONG - Don't put DDL and index in same transaction
transact([
  "CREATE TABLE entities (...)",
  "CREATE INDEX ASYNC idx_tenant ON entities(tenant_id)"  # ❌ Will fail
])

# CORRECT - Separate transactions
transact(["CREATE TABLE entities (...)"])
transact(["CREATE INDEX ASYNC idx_tenant ON entities(tenant_id)"])
```

### Pattern 3: Safe Data Migration

```python
# Step 1: Add column (one transaction)
transact(["ALTER TABLE entities ADD COLUMN status VARCHAR(50)"])

# Step 2: Populate in batches (separate transactions)
transact(["UPDATE entities SET status = 'active' WHERE status IS NULL LIMIT 1000"])
transact(["UPDATE entities SET status = 'active' WHERE status IS NULL LIMIT 1000"])

# Step 3: Verify
readonly_query("SELECT COUNT(*) as total, COUNT(status) as with_status FROM entities")

# Step 4: Create index (separate transaction)
transact(["CREATE INDEX ASYNC idx_status ON entities(tenant_id, status)"])
```

### Pattern 4: Batch Inserts

```python
# Build list of INSERT statements
inserts = []
for i in range(100):  # Keep under 3,000 rows per transaction
    inserts.append(f"INSERT INTO entities (entity_id, tenant_id, name) VALUES ('e{i}', 't1', 'Entity {i}')")

# Execute in one transaction
transact(inserts)
```

### Pattern 5: Application-Layer Foreign Key Check

```python
# Step 1: Validate parent exists
result = readonly_query("SELECT entity_id FROM entities WHERE entity_id = 'parent-123' AND tenant_id = 'tenant-123'")

if len(result) == 0:
    raise Error("Invalid parent reference")

# Step 2: Insert child
transact([
    "INSERT INTO objectives (objective_id, entity_id, tenant_id, title) VALUES ('obj-456', 'parent-123', 'tenant-123', 'My Objective')"
])
```

---

## Best Practices

### Follow General Developing Best Practices

Refer to the listed [Best Practices](./development-guide.md#best-practices).

### Input Validation (Critical!)

Since parameterized queries are NOT supported, you MUST validate and sanitize inputs:

```python
# BAD - SQL injection risk
user_input = request.get("tenant_id")
sql = f"SELECT * FROM entities WHERE tenant_id = '{user_input}'"
readonly_query(sql)  # ❌ Vulnerable!

# GOOD - Validate input format
import re
user_input = request.get("tenant_id")
if not re.match(r'^[a-zA-Z0-9-]+$', user_input):
    raise ValueError("Invalid tenant_id format")
sql = f"SELECT * FROM entities WHERE tenant_id = '{user_input}'"
readonly_query(sql)  # ✓ Safe after validation

# BETTER - Use allowlist for tenant IDs
ALLOWED_TENANTS = {"tenant-123", "tenant-456"}
if user_input not in ALLOWED_TENANTS:
    raise ValueError("Unknown tenant")
sql = f"SELECT * FROM entities WHERE tenant_id = '{user_input}'"
readonly_query(sql)  # ✓ Most secure
```

### Quote Escaping

```python
# Escape single quotes in string values
name = user_input.replace("'", "''")
sql = f"INSERT INTO entities (name) VALUES ('{name}')"
```

---

## Additional Resources

- [Aurora DSQL MCP Server Documentation](https://awslabs.github.io/mcp/servers/aurora-dsql-mcp-server)
- [Aurora DSQL MCP Server README](https://github.com/awslabs/mcp/tree/main/src/aurora-dsql-mcp-server)
- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
