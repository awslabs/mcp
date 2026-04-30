# DSQL Examples: Schema Design

Part of [Aurora DSQL Implementation Examples](../dsql-examples.md).

---

## Schema Design: Table Creation

SHOULD use UUIDs with `gen_random_uuid()` for distributed write performance. Source: [aurora-dsql-samples/java/liquibase](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/liquibase)

```sql
CREATE TABLE IF NOT EXISTS owner (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(30) NOT NULL,
  city VARCHAR(80) NOT NULL,
  telephone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS orders (
  order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL,
  tags TEXT,
  metadata TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Schema Design: Index Creation

MUST use `CREATE INDEX ASYNC` (max 24 indexes/table, 8 columns/index — verify via `awsknowledge`: `aurora dsql index limits`). Source: [aurora-dsql-samples/java/liquibase](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/liquibase)

```sql
CREATE INDEX ASYNC idx_owner_city ON owner(city);
CREATE INDEX ASYNC idx_orders_tenant ON orders(tenant_id);
CREATE INDEX ASYNC idx_orders_status ON orders(tenant_id, status);
```

---

## Schema Design: Column Modifications

MUST use two-step process: add column, then UPDATE for defaults (ALTER COLUMN not supported).

```sql
ALTER TABLE orders ADD COLUMN priority INTEGER;
UPDATE orders SET priority = 0 WHERE priority IS NULL;
```
