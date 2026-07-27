# MySQL to DSQL: Batched Migration & Error Handling

Part of [MySQL to DSQL DDL Migration](ddl-operations.md). See [Common Verify & Swap Pattern](ddl-operations.md#common-verify--swap-pattern) for the shared migration end-pattern.

---

## Batched Migration Pattern

**REQUIRED for tables exceeding 3,000 rows.**

See [ddl-migrations/batched-migration.md](../ddl-migrations/batched-migration.md) for the full pattern including OFFSET-based batching, cursor-based batching, progress tracking, and error handling.

### MySQL-Specific Considerations

When migrating from MySQL, additional validation checks may be needed:

- **Type conversion failures:** Non-numeric VARCHAR to INTEGER (check with regex validation)
- **Value truncation:** TEXT to VARCHAR(n) where values exceed target length
- **UNSIGNED check:** Negative values in columns that were MySQL UNSIGNED types

```sql
-- Find values exceeding target VARCHAR length
readonly_query(
  "SELECT id, LENGTH(text_column) as len FROM target_table
   WHERE LENGTH(text_column) > 255 LIMIT 100"
)
```
