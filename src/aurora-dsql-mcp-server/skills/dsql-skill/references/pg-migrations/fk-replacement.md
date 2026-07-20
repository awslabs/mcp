# Foreign Key → Validation Function Replacement

`dsql_lint` removes FK declarations. Use application-layer referential integrity instead.

The basic pattern (check-then-insert in a transaction) is assumed knowledge. This file
provides the **tenant-scoped template** that ensures FK validation is scoped to the same
tenant — the key DSQL-specific pattern.

---

## Tenant-Scoped FK Validation Template

For multi-tenant schemas, FK validation MUST be scoped to the same tenant:

```sql
-- Template: validate_fk_{child_table}_{fk_column}
CREATE FUNCTION validate_fk_{child_table}_{fk_column}(
  p_tenant_id uuid,
  p_value {fk_type}
) RETURNS boolean
LANGUAGE sql AS $$
  SELECT EXISTS (
    SELECT 1 FROM {parent_table}
    WHERE {parent_column} = p_value AND tenant_id = p_tenant_id
  );
$$;
```

**Example:**

```sql
CREATE FUNCTION validate_fk_orders_customer_id(
  p_tenant_id uuid,
  p_customer_id uuid
) RETURNS boolean
LANGUAGE sql AS $$
  SELECT EXISTS (
    SELECT 1 FROM customers WHERE id = p_customer_id AND tenant_id = p_tenant_id
  );
$$;
```

## Cascade Delete Template

```sql
CREATE FUNCTION cascade_delete_{parent_table}(p_parent_id {pk_type}) RETURNS void
LANGUAGE sql AS $$
  DELETE FROM {child_table} WHERE {fk_column} = p_parent_id;
$$;
```

## Calling Points

| Original FK Action | When to Call                  | Function               |
| ------------------ | ----------------------------- | ---------------------- |
| REFERENCES         | Before INSERT/UPDATE of child | `validate_fk_*()`      |
| ON DELETE CASCADE  | Before DELETE of parent       | `cascade_delete_*()`   |
| ON DELETE SET NULL | Before DELETE of parent       | `cascade_set_null_*()` |

## Caller Pattern

`validate_fk_*` returns `boolean`. The application MUST act on the result — calling
the function and unconditionally inserting silently bypasses validation and violates
the tenant-scoping MUST clause above. DSQL only supports `LANGUAGE sql` for functions
(`LANGUAGE plpgsql` is rejected), so the `RAISE`-on-false enforcement happens in the
application layer, in the same transaction as the child INSERT/UPDATE.

```python
# psycopg3 example — validate then insert in one transaction.
# psycopg2 has no `conn.transaction()`; use `with conn:` (commits on exit) instead.
with conn.transaction():
    cur.execute(
        "SELECT validate_fk_orders_customer_id(%s, %s)",
        (tenant_id, customer_id),
    )
    if not cur.fetchone()[0]:
        raise ValueError(f"customer_id {customer_id} not in tenant {tenant_id}")
    cur.execute(
        "INSERT INTO orders (id, tenant_id, customer_id, ...) VALUES (%s, %s, %s, ...)",
        (order_id, tenant_id, customer_id, ...),
    )
```

The validation and INSERT MUST share a transaction. Because DSQL uses snapshot
isolation with OCC, the SELECT adds the parent row to the transaction's read
set; if a concurrent transaction deletes that parent and commits first, this
transaction's commit is rejected with SQLSTATE 40001.
