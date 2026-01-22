# Aurora DSQL Implementation Examples

This file contains DSQL integration code examples; only load this when actively implementing database code.

For language-specific framework selection, recommendations, and examples see [language.md](./language.md).

For developer rules, see [development-guide.md](./development-guide.md).

For additional samples, including in alternative language and driver support, refer to the official
[aurora-dsql-samples](https://github.com/aws-samples/aurora-dsql-samples).

---

## Ad-Hoc Queries with psql

```bash
# Execute queries with admin token
PGPASSWORD="$(aws dsql generate-db-connect-admin-auth-token \
  --hostname ${CLUSTER}.dsql.${REGION}.on.aws \
  --region ${REGION})" \
psql -h ${CLUSTER}.dsql.${REGION}.on.aws -U admin -d postgres \
  -c "SELECT COUNT(*) FROM objectives WHERE tenant_id = 'tenant-123';"
```

---

## Connection Management

### RECOMMENDED: DSQL Connector

Source: [aurora-dsql-samples/javascript](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript)

```javascript
import { AuroraDSQLPool } from "@aws/aurora-dsql-node-postgres-connector";

function createPool(clusterEndpoint, user) {
  return new AuroraDSQLPool({
    host: clusterEndpoint,
    user: user,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 10000,
  });
}

async function example() {
  const pool = createPool(process.env.CLUSTER_ENDPOINT, process.env.CLUSTER_USER);

  try {
    const result = await pool.query("SELECT $1::int as value", [42]);
    console.log(`Result: ${result.rows[0].value}`);
  } finally {
    await pool.end();
  }
}
```

### Token Generation for Custom Implementations

For custom drivers or languages without DSQL Connector. Source: [aurora-dsql-samples/javascript/authentication](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/authentication)

```javascript
import { DsqlSigner } from "@aws-sdk/dsql-signer";

async function generateToken(clusterEndpoint, region) {
  const signer = new DsqlSigner({ hostname: clusterEndpoint, region });
  return await signer.getDbConnectAdminAuthToken();
}
```

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

MUST use `CREATE INDEX ASYNC` (max 24 indexes/table, 8 columns/index). Source: [aurora-dsql-samples/java/liquibase](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/liquibase)

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

---

## Data Operations: Basic CRUD

Source: [aurora-dsql-samples/quickstart_data](https://github.com/aws-samples/aurora-dsql-samples/tree/main/quickstart_data)

```sql
-- Insert with transaction
BEGIN;
INSERT INTO owner (name, city) VALUES
  ('John Doe', 'New York'),
  ('Mary Major', 'Anytown');
COMMIT;

-- Query with JOIN
SELECT o.name, COUNT(p.id) as pet_count
FROM owner o
LEFT JOIN pet p ON p.owner_id = o.id
GROUP BY o.name;

-- Update and delete
UPDATE owner SET city = 'Boston' WHERE name = 'John Doe';
DELETE FROM owner WHERE city = 'Portland';
```

---

## Data Operations: Batch Processing

**Transaction Limits:**
- Maximum 3,000 rows per transaction
- Maximum 10 MiB data size per transaction
- Maximum 5 minutes per transaction

### Safe Batch Insert

```javascript
async function batchInsert(pool, tenantId, items) {
  const BATCH_SIZE = 500;

  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    const batch = items.slice(i, i + BATCH_SIZE);
    const client = await pool.connect();

    try {
      await client.query('BEGIN');

      for (const item of batch) {
        await client.query(
          `INSERT INTO entities (tenant_id, name, metadata)
          VALUES ($1, $2, $3)`,
          [tenantId, item.name, JSON.stringify(item.metadata)]
        );
      }

      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
}
```

### Concurrent Batch Processing

**Pattern:** SHOULD use concurrent connections for better throughput

Source: Adapted from [aurora-dsql-samples/javascript](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript)

```javascript
// Split into batches and process concurrently
async function concurrentBatchInsert(pool, tenantId, items) {
  const BATCH_SIZE = 500;
  const NUM_WORKERS = 8;

  const batches = [];
  for (let i = 0; i < items.length; i += BATCH_SIZE) {
    batches.push(items.slice(i, i + BATCH_SIZE));
  }

  const workers = [];
  for (let i = 0; i < NUM_WORKERS && i < batches.length; i++) {
    workers.push(processBatches(pool, tenantId, batches, i, NUM_WORKERS));
  }

  await Promise.all(workers);
}

async function processBatches(pool, tenantId, batches, startIdx, step) {
  for (let i = startIdx; i < batches.length; i += step) {
    const batch = batches[i];
    const client = await pool.connect();

    try {
      await client.query('BEGIN');

      for (const item of batch) {
        await client.query(
          'INSERT INTO entities (tenant_id, name, metadata) VALUES ($1, $2, $3)',
          [tenantId, item.name, JSON.stringify(item.metadata)]
        );
      }

      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
}
```

---

## Migration Execution

**Pattern:** MUST execute each DDL statement separately (DDL statements execute outside transactions)

Source: Adapted from [aurora-dsql-samples/java/liquibase](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/liquibase)

```javascript
const migrations = [
  {
    id: '001_initial_schema',
    description: 'Create owner and pet tables',
    statements: [
      `CREATE TABLE IF NOT EXISTS owner (
         id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         name VARCHAR(30) NOT NULL,
         city VARCHAR(80) NOT NULL,
         telephone VARCHAR(20)
       )`,
      `CREATE TABLE IF NOT EXISTS pet (
         id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         name VARCHAR(30) NOT NULL,
         birth_date DATE NOT NULL,
         owner_id UUID
       )`,
    ]
  },
  {
    id: '002_create_indexes',
    description: 'Create async indexes',
    statements: [
      'CREATE INDEX ASYNC idx_owner_city ON owner(city)',
      'CREATE INDEX ASYNC idx_pet_owner ON pet(owner_id)',
    ]
  },
  {
    id: '003_add_columns',
    description: 'Add status column',
    statements: [
      'ALTER TABLE pet ADD COLUMN IF NOT EXISTS status VARCHAR(20)',
      "UPDATE pet SET status = 'active' WHERE status IS NULL",
    ]
  }
];

async function runMigrations(pool, migrations) {
  for (const migration of migrations) {
    for (const statement of migration.statements) {
      if (statement.trim()) {
        await pool.query(statement);
      }
    }
  }
}
```

---

## Multi-Tenant Isolation

ALWAYS include tenant_id in WHERE clauses; tenant_id is always first parameter.

```javascript
async function getOrders(pool, tenantId, status) {
  const result = await pool.query(
    'SELECT * FROM orders WHERE tenant_id = $1 AND status = $2',
    [tenantId, status]
  );
  return result.rows;
}

async function deleteOrder(pool, tenantId, orderId) {
  const check = await pool.query(
    'SELECT order_id FROM orders WHERE tenant_id = $1 AND order_id = $2',
    [tenantId, orderId]
  );

  if (check.rows.length === 0) {
    throw new Error('Order not found or access denied');
  }

  await pool.query(
    'DELETE FROM orders WHERE tenant_id = $1 AND order_id = $2',
    [tenantId, orderId]
  );
}
```

---

## Application-Layer Referential Integrity

SHOULD validate references for custom business rules (DSQL provides database-level integrity).

```javascript
async function createLineItem(pool, tenantId, lineItemData) {
  const orderCheck = await pool.query(
    'SELECT order_id FROM orders WHERE tenant_id = $1 AND order_id = $2',
    [tenantId, lineItemData.order_id]
  );

  if (orderCheck.rows.length === 0) {
    throw new Error('Order does not exist');
  }

  await pool.query(
    'INSERT INTO line_items (tenant_id, order_id, product_id, quantity) VALUES ($1, $2, $3, $4)',
    [tenantId, lineItemData.order_id, lineItemData.product_id, lineItemData.quantity]
  );
}

async function deleteProduct(pool, tenantId, productId) {
  const check = await pool.query(
    'SELECT COUNT(*) as count FROM line_items WHERE tenant_id = $1 AND product_id = $2',
    [tenantId, productId]
  );

  if (parseInt(check.rows[0].count) > 0) {
    throw new Error('Product has existing orders');
  }

  await pool.query(
    'DELETE FROM products WHERE tenant_id = $1 AND product_id = $2',
    [tenantId, productId]
  );
}
```

---

## Data Serialization

**Pattern:** MUST store arrays and JSON as TEXT (runtime-only types). Per [DSQL docs](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-supported-data-types.html), cast to JSON at query time.

```javascript
function toTextArray(values) {
  return values.join(',');
}

function fromTextArray(textValue) {
  return textValue ? textValue.split(',').map(v => v.trim()) : [];
}

function toTextJSON(object) {
  return JSON.stringify(object);
}

function fromTextJSON(textValue) {
  if (!textValue) return null;
  try {
    return JSON.parse(textValue);
  } catch (err) {
    console.warn('Invalid JSON in column:', err.message);
    return null;
  }
}

const categoriesText = toTextArray(['backend', 'api', 'database']);
await pool.query('INSERT INTO projects (project_id, categories) VALUES ($1, $2)', [projectId, categoriesText]);

const configText = toTextJSON({ theme: 'dark', notifications: true });
await pool.query('INSERT INTO user_settings (user_id, preferences) VALUES ($1, $2)', [userId, configText]);
```

Query-time operations:

```sql
SELECT user_id, preferences::jsonb->>'theme' as theme
FROM user_settings WHERE preferences::jsonb->>'notifications' = 'true';

SELECT project_id, string_to_array(categories, ',') as category_array FROM projects;
```

---

## References

- **Development Guide:** [development-guide.md](./development-guide.md)
- **Language Guide:** [language.md](./language.md)
- **Onboarding Guide:** [onboarding.md](./onboarding.md)
- **AWS Documentation:** [DSQL User Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- **Sample Code:** [aurora-dsql-samples](https://github.com/aws-samples/aurora-dsql-samples)
