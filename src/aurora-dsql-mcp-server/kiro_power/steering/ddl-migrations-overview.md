# DSQL DDL Migration Guide

Use table recreation only for structural changes that Aurora DSQL cannot perform directly.

## Table of Contents

1. [Destructive Operations Warning](#destructive-operations-warning)
2. [Direct ALTER Operations](#direct-alter-operations)
3. [Table Recreation](#table-recreation)
4. [Common Verify & Swap Pattern](#common-verify--swap-pattern)
5. [Recovery — Row Counts Do Not Match](#recovery--row-counts-do-not-match)
6. [Best Practices Summary](#best-practices-summary)

For column changes, see [column-operations.md](column-operations.md).
For constraints and primary keys, see [constraint-operations.md](constraint-operations.md).

---

## Destructive Operations Warning

Table recreation drops the original table and is irreversible after the drop. Before any live
migration, **MUST** present the complete plan, confirm a backup or accepted data-loss risk, and
obtain explicit approval at each destructive checkpoint.

---

## Direct ALTER Operations

Use direct DDL for supported operations:

- `ALTER TABLE ... ALTER COLUMN ... DROP NOT NULL`
- `ALTER TABLE ... ALTER COLUMN ... SET/DROP DEFAULT`
- `ALTER TABLE ... ADD CONSTRAINT ... CHECK (...) NOT VALID`
- `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ... NOT VALID`
- `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE USING INDEX`
- `ALTER TABLE ASYNC ... VALIDATE CONSTRAINT`
- `ALTER TABLE ... DROP CONSTRAINT` for CHECK, UNIQUE, or foreign-key constraints
- `ALTER TABLE ... RENAME COLUMN`
- `ALTER TABLE ... RENAME TO`
- `ALTER TABLE ... ADD COLUMN`

Use table recreation for `ALTER COLUMN TYPE`, `SET NOT NULL`, `ADD PRIMARY KEY`, `MODIFY PRIMARY
KEY`, and transformations that lack a supported direct form.

---

## Table Recreation Pattern Overview

See [Table Recreation](#table-recreation).

---

## Table Recreation

Use this last-resort pattern only when DSQL cannot make the requested structural change in place:

1. **Plan and confirm** — identify the exact source schema, requested change, data conversion, and
   rollback boundary.
2. **Inspect dependencies** — check for inbound foreign keys and dependent views before creating
   the replacement table.
3. **Create and copy** — derive the complete replacement definition from the source, changing only
   the requested property. Copy data in bounded transactions.
4. **Verify and swap** — follow the [Common Verify & Swap Pattern](#common-verify--swap-pattern).
5. **Rebuild indexes** — create required secondary indexes with `CREATE INDEX ASYNC` and wait for
   readiness before relying on them.

If the table participates in a foreign key or has dependent views, **MUST** stop the generic
pattern and present a dedicated, user-approved migration plan. **MUST NOT** use
`DROP TABLE ... CASCADE` to bypass dependencies.

### Transaction Rules

- **MUST** batch migrations exceeding 3,000 row mutations.
- **PREFER** batches of 500–1,000 rows.
- **MUST** respect the 10 MiB write-data limit and 5-minute transaction duration.

---

## Pre-Create Relationship and Dependency Gate

Compatibility anchor for existing procedure links. Before table recreation, inspect dependencies and
use the [Table Recreation](#table-recreation) rules above.

---

## Common Verify & Swap Pattern

Use this pattern only after confirming the table has no foreign-key or view dependencies that need
a dedicated migration plan:

1. Stop writes to the target table, apply final data catch-up, and compare row counts and primary
   key sets.
2. **MUST** display: "The original and replacement tables have been verified. The next step
   permanently drops the original table and cannot be rolled back. Proceed? (yes/no)"
3. **MUST NOT** continue without an explicit `yes`.
4. Drop the original table and rename the replacement in separate DDL transactions:

   ```python
   transact(["DROP TABLE target_table"])
   transact(["ALTER TABLE target_table_new RENAME TO target_table"])
   ```

5. Recreate required secondary indexes with `CREATE INDEX ASYNC`, verify `pg_index.indisvalid =
   true`, then resume writes.

### Recovery — Row Counts Do Not Match

When `target_table_new` has fewer rows than `target_table`, the migration is incomplete. **MUST
NOT** drop the original table until counts match.

1. Diagnose missing rows by primary-key range or batch boundary.
2. Retry the missing batches.
3. Re-run the count comparison.
4. If diagnosis stalls, drop only `target_table_new` and restart; the original remains authoritative.

---

## Best Practices Summary

- **MUST** use direct ALTER forms when DSQL supports the requested operation.
- **MUST** inspect dependencies before table recreation.
- **MUST** use a dedicated, approved plan for foreign-key or view dependencies.
- **MUST** verify replacement data before dropping the original table.
- **MUST** recreate secondary indexes asynchronously after a generic swap.
- **MUST NOT** use `DROP TABLE ... CASCADE` to bypass a dependency plan.
