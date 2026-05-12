# DDL Migrations: Batched Migration Pattern

**REQUIRED for tables exceeding 3,000 rows.**

For the full Table Recreation Pattern and verify & swap steps, see [overview.md](overview.md).

---

## Batch Size Rules

- **PREFER batches of 500-1,000 rows** for optimal performance
- Smaller batches reduce lock contention and enable better concurrency

---

## OFFSET-Based Batching

```sql
readonly_query("SELECT COUNT(*) as total FROM target_table")
-- Calculate: batches_needed = CEIL(total / 1000)

-- Batch 1
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   ORDER BY id LIMIT 1000 OFFSET 0"
])

-- Batch 2
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   ORDER BY id LIMIT 1000 OFFSET 1000"
])
-- Continue until all rows migrated...
```

---

## Cursor-Based Batching (Preferred for Large Tables)

Better performance than OFFSET for very large tables:

```sql
-- First batch
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   ORDER BY id LIMIT 1000"
])

-- Get last processed ID
readonly_query("SELECT MAX(id) as last_id FROM target_table_new")

-- Subsequent batches
transact([
  "INSERT INTO target_table_new (id, col1, col2)
   SELECT id, col1, col2 FROM target_table
   WHERE id > 'last_processed_id'
   ORDER BY id LIMIT 1000"
])
```

---

## Progress Tracking

```sql
readonly_query(
  "SELECT (SELECT COUNT(*) FROM target_table_new) as migrated,
          (SELECT COUNT(*) FROM target_table) as total"
)
```

---

## Error Handling

### Pre-Migration Checks

1. **Verify table exists**

   ```sql
   readonly_query(
     "SELECT table_name FROM information_schema.tables
      WHERE table_name = 'target_table'"
   )
   ```

2. **Verify DDL permissions**

### Data Validation Errors

**MUST abort migration and report** when:

- Type conversion would fail
- Value truncation would occur
- NOT NULL constraint would be violated

```sql
-- Find problematic rows
readonly_query(
  "SELECT id, problematic_column FROM target_table
   WHERE problematic_column !~ '^-?[0-9]+$' LIMIT 100"
)
```

### Recovery from Failed Migration

```sql
-- Check table state
readonly_query(
  "SELECT table_name FROM information_schema.tables
   WHERE table_name IN ('target_table', 'target_table_new')"
)
```

- **Both tables exist:** Original safe → `DROP TABLE IF EXISTS target_table_new` and restart
- **Only new table exists:** Verify count, then complete rename
