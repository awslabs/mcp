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

For tables > 3,000 rows, use [Batched Migration Pattern](ddl-batching.md).

---

## ALTER TABLE ... DROP COLUMN

**MySQL syntax:**

```sql
ALTER TABLE table_name DROP COLUMN column_name;
```

**DSQL:** identical — the statement translates 1:1 and needs no batching, because DSQL drops the
column as a metadata-only change.

```sql
ALTER TABLE table_name DROP COLUMN column_name;
```

Two differences from MySQL:

- Dropping a primary key column is unsupported. That case MUST use the **Table Recreation Pattern**.
- A column that a view, foreign key, or `GENERATED ... STORED` column depends on requires `CASCADE`,
  which drops those dependents too — MUST confirm the dependency list with the user first.

See [column-operations.md DROP COLUMN](../ddl-migrations/column-operations.md#drop-column) for the
full rule set, including the 255-active/1,600-lifetime column budget.
