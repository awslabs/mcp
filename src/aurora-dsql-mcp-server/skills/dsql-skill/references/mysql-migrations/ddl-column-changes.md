# MySQL to DSQL: Column Changes

Part of [MySQL to DSQL DDL Migration](ddl-operations.md). See [Common Verify & Swap Pattern](ddl-operations.md#common-verify--swap-pattern) for the shared migration end-pattern.

---

## ALTER TABLE ... ALTER COLUMN (Change Column Type)

**MySQL syntax:**

```sql
ALTER TABLE table_name ALTER COLUMN column_name datatype;
-- or MySQL-specific:
ALTER TABLE table_name MODIFY COLUMN column_name new_datatype;
ALTER TABLE table_name CHANGE COLUMN old_name new_name new_datatype;
```

**DSQL:** MUST use **Table Recreation Pattern** — see [column-operations.md ALTER COLUMN TYPE](../ddl-migrations/column-operations.md#alter-column-type-migration) for the full step-by-step pattern including pre-migration validation and data type compatibility matrix.

---

## ALTER TABLE ... DROP COLUMN

**MySQL syntax:**

```sql
ALTER TABLE table_name DROP COLUMN column_name;
```

**DSQL:** MUST use **Table Recreation Pattern** — see [column-operations.md DROP COLUMN](../ddl-migrations/column-operations.md#drop-column-migration) for the full step-by-step pattern.

For tables > 3,000 rows, use [Batched Migration Pattern](ddl-batching.md).
