# Troubleshooting in DSQL

This file contains common additional errors encountered while working with DSQL and
guidelines for how to solve them.

Before referring to any listed errors, refer to the complete [DSQL troubleshooting guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/troubleshooting.html#troubleshooting-connections)

## Connection and Authorization

### Token Expiration

### Error: "Token has expired"
**Cause:** Authentication token older than 15 minutes
**Solutions:**
- Auto-regenerate tokens per connection or query OR
- Use connection pool hooks to refresh before expiration OR
- Implement retry logic with token regeneration

**Additional Recommendations:**
- Don't cache connections longer than 15 minutes
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

## Incompatibility
When migrating from PostgreSQL, remember DSQL doesn't support:

- **Foreign key constraints** - Enforce referential integrity in application code
- **Sequences** - Use `gen_random_uuid()` for primary keys
- **SERIAL types** - Use UUID or INTEGER with application-generated IDs
- **Extensions** - No PL/pgSQL, PostGIS, pgvector, etc.
- **Triggers** - Implement logic in application layer
- **Temporary tables** - Use regular tables or application-level caching
- **TRUNCATE** - Use `DELETE FROM table` instead
- **Multiple databases** - Single `postgres` database per cluster
- **Custom types** - Limited type system support
- **Partitioning** - Manage data distribution in application

See [full list of unsupported features](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html).

#### Error: "Foreign key constraint not supported"
**Cause:** Attempting to create FOREIGN KEY constraint
**Solution:**
1. Remove FOREIGN KEY from DDL
2. Implement validation in application code
3. Check parent exists before INSERT
4. Check dependents before DELETE

#### Error: "Datatype array not supported"
**Cause:** Using TEXT[] or other array types
**Solution:**
1. Change column to TEXT
2. Store as comma-separated: `"tag1,tag2,tag3"`
3. Or use JSON.stringify: `"["tag1","tag2","tag3"]"`
4. Deserialize in application layer

#### Error: "Please use CREATE INDEX ASYNC"
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
