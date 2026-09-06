# Troubleshooting in DSQL

This file contains common additional errors encountered while working with DSQL and
guidelines for how to solve them.

Before referring to any listed error, use the routing below and consult
[Additional Resources](#additional-resources).

## Table of Contents

1. [Connection and Authorization](#connection-and-authorization)
2. [Cluster Lifecycle](#cluster-lifecycle)
3. [Foreign Key Addition or Validation Fails](#foreign-key-addition-or-validation-fails)
4. [Incompatibility](#incompatibility)
5. [Protocol Compatibility](#protocol-compatibility)
6. [Additional Resources](#additional-resources)

## Connection and Authorization

### Token Expiration

### Error: "Token has expired"

**Cause:** Authentication token older than 15 minutes
**Solutions:**

- Auto-regenerate tokens per connection or query OR
- Use connection pool hooks to refresh before expiration OR
- Implement retry logic with token regeneration

**Additional Recommendations:**

- Refresh connections within 15 minutes
- Auto-reconnect after observing auth errors

### Connection Timeouts

**Problem**: Database connections time out after 1 hour.
**Solution**:

- Configure connection pool lifetime < 1 hour
- Implement connection health checks
- Handle disconnection gracefully with retries

### Schema Privileges

**Problem**: Non-admin users get permission denied errors.

**Solution**:

- Admin users must explicitly grant schema access to non-admin users
- Non-admin users must create and use custom schemas (not `public`)
- Link database roles to IAM roles for authentication

### SSL Certificate Verification

**Problem**: SSL verification fails with certificate errors.

**Solution**:

- Ensure system has Amazon Root CA certificates
- Use native TLS libraries (not OpenSSL 1.0.x)
- Set `server_name_indication` to cluster endpoint in SSL config

## Cluster Lifecycle

See [cluster lifecycle](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/cluster-lifecycle.html) for state definitions and behavior.

### Error: "FATAL: unable to accept connection, waking up cluster, please retry later"

The cluster is `INACTIVE` and waking up. Poll `aws dsql get-cluster --identifier <id> --region <region> --query status --output text` until `ACTIVE`, then retry.

### Error: `FailedPrecondition` when backing up an `IDLE` / `INACTIVE` cluster

Connect to the cluster to wake it, then retry the backup.

## Foreign Key Addition or Validation Fails

**Addition failure:** Aurora DSQL rejects `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY`
without `NOT VALID`. Add the post-creation constraint with `NOT VALID`.

**Validation-job failure:** Inspect `sys.jobs.status` and `sys.jobs.details` first. Repair
referencing rows only when `details` identifies a foreign key violation. For other failures,
address the reported cause before rerunning
`ALTER TABLE ASYNC ... VALIDATE CONSTRAINT`.

For SQLSTATE `40001` during concurrent referenced-row and referencing-row writes, retry the
complete transaction. For transaction-limit errors during cascades, assess per-parent fan-out.
When one parent can exceed transaction limits, use `NO ACTION` or `RESTRICT`, process child rows
in bounded transactions, then change the parent.

### Error: "... violates foreign key constraint"

SQLSTATE `23503` is not retryable. Correct the relationship or apply the intended referential
action; **MUST NOT** route it through the `40001` OCC retry loop.

## Incompatibility

When migrating from PostgreSQL, remember DSQL doesn't support:

- **SERIAL types** - Use `GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY` with sequences instead
- **Extensions** - No PL/pgSQL, PostGIS, pgvector, etc.
- **Triggers** - Implement logic in application layer
- **Temporary tables** - Use regular tables or application-level caching
- **TRUNCATE** - Use `DELETE FROM table` instead
- **Multiple databases** - Single `postgres` database per cluster
- **Custom types** - Limited type system support
- **Partitioning** - Manage data distribution in application

See [full list of unsupported features](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html).

### Error: "Datatype array not supported"

**Cause:** Using `TEXT[]` or other array column types
**Solution:** Serialize the array into a single column — DSQL has no array column type. PREFER `JSONB`; MAY use `TEXT` for opaque columns. ASK the user which format fits the access pattern.

- **PREFER `JSONB`** — the application queries inside the value (`@>`/`?`/`?|`/`?&`, `jsonb_array_elements_text`, or indexed JSONB paths); values are normalized on write. Insert: `INSERT INTO t (tags) VALUES ($1::jsonb)` with `JSON.stringify(arr)`. Query: `jsonb_array_elements_text(tags)`.
- **MAY use `TEXT`** — the column is opaque to the database (the app reads the whole value, parses it, and never queries inside). Insert raw: `INSERT INTO t (tags_csv) VALUES ($1)` with `arr.join(',')`.
- **`JSON` is valid** when writes dominate (no parse/sort overhead on write), byte-exact input matters (audit, replay, duplicate keys), or only `->`/`->>` is needed.
- **When migrating:** keep existing `JSON` columns as `JSON`; upgrade to `JSONB` only when JSONB-only operators or indexed paths are needed.

### Error: "Please use CREATE INDEX ASYNC"

**Cause:** Creating index without ASYNC keyword
**Solution:**

```sql
-- Wrong
CREATE INDEX idx_name ON table(column);

-- Correct
CREATE INDEX ASYNC idx_name ON table(column);
```

### Error: "Transaction exceeds 3000 rows"

**Cause:** Modifying too many rows in single transaction
**Solution:**

1. Batch operations into chunks of 500-1000 rows
2. Process each batch separately
3. Add WHERE clause to limit scope

### Error: "OC001 - Concurrent DDL operation"

**Cause:** Multiple DDL operations on same resource
**Solution:**

1. Wait for current DDL to complete
2. Retry with exponential backoff
3. Execute DDL operations sequentially

## Protocol Compatibility

**Problem**: Some PostgreSQL clients send unsupported protocol messages.

**Solution**:

- Use officially tested drivers from [aws-samples/aurora-dsql-samples](https://github.com/aws-samples/aurora-dsql-samples)
- Test client compatibility before production deployment

## Additional Resources

- [Aurora DSQL troubleshooting guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/troubleshooting.html#troubleshooting-connections)
- [Aurora DSQL PostgreSQL compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with.html)
