# MCP Database Operation Tools

Part of [Aurora DSQL MCP Tools Reference](../mcp-tools.md).

---

## 1. readonly_query - Execute read-only SQL queries

**Use for:** SELECT queries, data exploration, ad-hoc analysis

**Parameters:**

- `sql` (string, required) - SQL query to run

**Returns:** List of dictionaries containing query results

**Server-side filters (read-only mode only):** Reject mutating keywords,
textbook injection patterns (tautologies, `--` comments, `UNION SELECT`,
stacked queries, `pg_sleep`, `COPY ... FROM/TO`), and `COMMIT; <other>`
transaction-bypass attempts. These are a safety net, not a substitute for
input validation.

**Examples:**

```python
from safe_query import build, regex, ident, TENANT_SLUG

# Simple SELECT — user-supplied tenant_id goes through a validator
readonly_query(build(
    "SELECT * FROM {tbl} WHERE tenant_id = {tid} LIMIT 10",
    tbl=ident("entities"),
    tid=regex(tenant_id, TENANT_SLUG),
))

# Aggregate query (no user-supplied values)
readonly_query(build(
    "SELECT tenant_id, COUNT(*) as count FROM objectives GROUP BY tenant_id",
))

# Join query — e./o. aliases are static template text, not interpolated
readonly_query(build(
    "SELECT e.entity_id, e.name, o.title "
    "FROM {e} INNER JOIN {o} ON e.entity_id = o.entity_id "
    "WHERE e.tenant_id = {tid}",
    e=ident("entities"),
    o=ident("objectives"),
    tid=regex(tenant_id, TENANT_SLUG),
))
```

**Building queries:** **MUST** build SQL with
[`safe_query.build()`](safe_query.py). Parameter binding is not supported by
this tool, and raw f-string interpolation is the primary SQL-injection vector.
See [input-validation.md](input-validation.md) for the required pattern.

---

## 2. transact - Execute write operations in a transaction

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

# Insert rows — build each statement with safe_query.
from safe_query import build, allow, regex, literal, UUID, TENANT_SLUG

transact([
    build(
        "INSERT INTO entities (entity_id, tenant_id, name) "
        "VALUES ({eid}, {tid}, {name})",
        eid=regex(row["entity_id"], UUID),
        tid=regex(row["tenant_id"], TENANT_SLUG),
        name=literal(row["name"]),
    )
    for row in rows
])

# Two-step column migration
STATUSES = {"active", "archived", "pending"}
transact(["ALTER TABLE entities ADD COLUMN status VARCHAR(50)"])
transact([
    build(
        "UPDATE entities SET status = {s} "
        "WHERE status IS NULL AND tenant_id = {tid}",
        s=allow("active", STATUSES),
        tid=regex(tenant_id, TENANT_SLUG),
    )
])
```

**Important Notes:**

- Each ALTER TABLE must be in its own transaction (DSQL limitation)
- Keep transactions under 3,000 rows and 10 MiB
- For large batch operations, split into multiple transact calls
- **MUST** build every statement with [`safe_query.build()`](safe_query.py).
  Write mode disables all server-side injection filters
  ([`server.py:295-318`](https://github.com/awslabs/mcp/blob/296b7aacf733f45bcb2a738875c4694eb3459686/src/aurora-dsql-mcp-server/awslabs/aurora_dsql_mcp_server/server.py#L295-L318)) —
  skill-level validation is the only defense.

---

## 3. get_schema - Get table schema details

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
