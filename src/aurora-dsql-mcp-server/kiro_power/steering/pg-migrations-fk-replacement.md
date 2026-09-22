# Foreign Key Constraints

Aurora DSQL supports foreign key constraints with familiar SQL syntax. Use foreign keys by default
for database-enforced referential integrity. Preserve foreign-key relationships during migration and
translate only unsupported source syntax or options.

## Table of Contents

1. [Default Pattern](#default-pattern)
2. [DSQL-Specific DDL](#dsql-specific-ddl)
3. [Operational Notes](#operational-notes)
4. [Table Recreation and Drops](#table-recreation-and-drops)
5. [Additional Resources](#additional-resources)

## Default Pattern

Create the referenced table before the referencing table and use standard `REFERENCES` or
`FOREIGN KEY ... REFERENCES` syntax. See
[Foreign Key Pattern](../mcp/tools/workflow-patterns.md#pattern-5-foreign-key) for executable
composite tenant-key DDL.

Use a unique referenced key and type-compatible referencing columns.

For a tenant-scoped relationship where the database must enforce tenant equality, the tenant key
**MUST** appear in both keys and be `NOT NULL` on both sides. Under the default `MATCH SIMPLE`,
optional relationship columns **MAY** remain nullable; a null relationship value means no
relationship. Use `MATCH FULL` when the application must reject partially populated composite
keys. Preserve ordinary foreign keys for shared or globally identified rows. A foreign key
enforces integrity, not caller authorization.

## DSQL-Specific DDL

Run every externally sourced or generated DDL statement through the complete
[dsql-lint workflow](dsql-lint.md#workflow-validate--migrate-sql-to-dsql). Surface every
diagnostic and the returned `fixed_sql`; stop on `unfixable` and obtain acknowledgement for
`fixed_with_warning`.

### Add to an existing table

Post-creation foreign keys **MUST** use `NOT VALID`. The add is synchronous, applies to new writes
immediately, skips the existing-row scan, and returns no `job_id`.

When referenced uniqueness comes from `CREATE UNIQUE INDEX ASYNC`, wait until
`pg_index.indisvalid = true` before adding the foreign key.

```sql
ALTER TABLE orders
  ADD CONSTRAINT orders_customers_customer_fkey
  FOREIGN KEY (tenant_id, customer_id)
  REFERENCES customers (tenant_id, customer_id)
  NOT VALID;
```

### Validate existing rows

`ASYNC` is **REQUIRED** for `VALIDATE CONSTRAINT` and applies only to this statement.

```sql
ALTER TABLE ASYNC orders
  VALIDATE CONSTRAINT orders_customers_customer_fkey;
```

Capture the returned `job_id`, poll `sys.jobs` through `submitted`, `processing`, `completed`, or
`failed`, inspect `details` on failure, and verify the catalog state:

```python
from safe_query import build, literal
import time

validation_result = transact([
    "ALTER TABLE ASYNC orders "
    "VALIDATE CONSTRAINT orders_customers_customer_fkey"
])
job_id = validation_result[0]["job_id"]
deadline = time.monotonic() + 300

while True:
    job = readonly_query(build(
        "SELECT status, details FROM sys.jobs WHERE job_id = {job_id}",
        job_id=literal(job_id),
    ))[0]
    if job["status"] == "completed":
        break
    if job["status"] == "failed":
        raise RuntimeError(f"Foreign key validation failed: {job['details']}")
    if time.monotonic() >= deadline:
        raise TimeoutError(f"Timed out waiting for validation job {job_id}")
    time.sleep(1)

validated = readonly_query(build(
    "SELECT convalidated FROM pg_constraint "
    "WHERE conrelid = 'orders'::regclass "
    "AND contype = 'f' "
    "AND conname = {constraint_name}",
    constraint_name=literal("orders_customers_customer_fkey"),
))[0]["convalidated"]
if not validated:
    raise RuntimeError("Validation job completed without validating the constraint")
```

Alternatively, call `sys.wait_for_job` through an autocommit database client and require its
`succeeded` result to be true. Use `sys.jobs` when the caller needs job status or failure details.

## Operational Notes

- Use default `MATCH SIMPLE`, or use `MATCH FULL` to require all-null or all-non-null composite
  keys.
- **SHOULD** default to `NO ACTION`. Use `CASCADE`, `SET NULL`, or `SET DEFAULT` only when the
  user explicitly intends the behavior and confirms its impact. Choose deferrability to match the
  transaction's validation point.
- Use `DEFERRABLE` for circular relationships or ORM flush orders that cannot satisfy each FK
  statement-by-statement. Run `SET CONSTRAINTS` in the same explicit transaction as the related
  DML; a separate MCP `transact` call commits independently. Deferred violations surface at
  `COMMIT`.
- Use relationship-specific constraint names such as `orders_billing_customer_fkey`; qualify the
  table name when a schema is required.
- For tenant-scoped relationships, referential actions **MUST** preserve the tenant key and the
  resulting tuple **MUST** remain in the same tenant.
- FK checks perform reads. A transaction can fail with `40001` when a concurrent referenced-key
  change commits after the transaction's snapshot; retry the complete transaction.
- Cascading actions count toward transaction limits. **MUST** assess per-parent fan-out; use
  `NO ACTION` or `RESTRICT` and process children in bounded transactions when one parent can
  exceed the limit.
- Surface foreign-key violation `23503` for relationship correction.

## Table Recreation and Drops

Use `ALTER TABLE ... DROP CONSTRAINT` to remove a foreign key directly. Before dropping, confirm
the named constraint with `pg_constraint.contype = 'f'`, explain the loss of database
enforcement, and obtain confirmation.

When a table-recreation request involves foreign keys or dependent views, stop the generic pattern
and present a dedicated, user-approved migration plan.

## Additional Resources

- [Working with foreign key constraints](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-foreign-key-constraints.html)
- [CREATE TABLE foreign key syntax](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/create-table-syntax-support.html#create-table-foreign-keys)
- [SET CONSTRAINTS](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/set-constraints-syntax-support.html)
