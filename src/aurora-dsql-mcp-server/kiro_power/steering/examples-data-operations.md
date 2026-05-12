# DSQL Examples: Data Operations

Part of [Aurora DSQL Implementation Examples](../dsql-examples.md).

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

**Transaction Limits** (verify current limits via `awsknowledge`: `aurora dsql transaction limits`)**:**

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
