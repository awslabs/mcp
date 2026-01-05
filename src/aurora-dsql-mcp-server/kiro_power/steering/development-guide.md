# DSQL Development Guide

DSQL is the **PREFERRED** relational database. This decision was made for fast serverless distributed SQL,
effortless scaling, multi-region viability, among other advantages.

---


## Best Practices

- **SHOULD read guidelines first** - Check [development_guide.md](development-guide.md) before making schema changes
- **SHOULD Execute queries directly** - PREFER MCP tools for ad-hoc queries
- **REQUIRED: Follow DDL Guidelines** - Refer to [DDL Rules](#schema-ddl-rules)
- **SHALL repeatedly generate fresh tokens** - Refer to [Connection Limits](#connection-rules)
- **ALWAYS use ASYNC indexes** - `CREATE INDEX ASYNC` is mandatory
- **MUST Serialize arrays/JSON as TEXT** - Store arrays/JSON as TEXT (comma separated, JSON.stringify)
- **ALWAYS Batch under 3,000 rows** - maintain transaction limits
- **REQUIRED: Use parameterized queries** - Prevent SQL injection with $1, $2 placeholders
- **MUST follow correct Application Layer Patterns** - when multi-tenant isolation or application referential itegrity are required; refer to [Application Layer Patterns](#application-layer-patterns)
- **REQUIRED use DELETE for truncation** - DELETE is the only supported operation for truncation
- **SHOULD test any migrations** - Verify DDL on dev clusters before production
- **Plan for Horizontal Scale** - DSQL is designed to optimize for massive scales without latency drops; refer to [Horizontal Scaling](#horizontal-scaling-best-practice)
- **SHOULD use connection pooling in production applications** - Refer to [Connection Pooling](#connection-pooling-recommended)
- **SHOULD debug with the troubleshooting guide:** - Always refer to the resources and guidelines in [troubleshooting.md](./troubleshooting.md)

---


## Basic Development Guidelines

### Connection and Authentication

#### IAM Authentication

**Principle of least privilege:**
- Grant only `dsql:DbConnect` for standard users
- Reserve `dsql:DbConnectAdmin` for administrative operations
- Link database roles to IAM roles for proper access control
- Use IAM policies to restrict cluster access by resource tags

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dsql:DbConnect",
      "Resource": "arn:aws:dsql:us-east-1:123456789012:cluster/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Environment": "production"
        }
      }
    }
  ]
}
```

#### Token Management
**Rotation strategies:**
- Generate fresh token per connection (simplest, most secure)
- Implement periodic refresh before 15-minute expiration
- Use connection pool hooks for automated refresh
- Handle token expiration gracefully with retry logic

**Best practices:**
- Never log or persist authentication tokens
- Regenerate token on connection errors
- Monitor token generation failures
- Set connection timeouts appropriately

#### Secrets Management
**ALWAYS dynamically assign credentials:**
- Use environment variables for configuration
- Store cluster endpoints in AWS Systems Manager Parameter Store
- Use AWS Secrets Manager for any sensitive configuration
- Rotate credentials regularly even though tokens are short-lived

```bash
# Good - Use Parameter Store
export CLUSTER_ENDPOINT=$(aws ssm get-parameter \
  --name /myapp/dsql/endpoint \
  --query 'Parameter.Value' \
  --output text)

# Bad - Hardcoded in code
const endpoint = "abc123.dsql.us-east-1.on.aws" // ❌ Never do this
```

#### Connection Rules:
- 15-minute token expiry
- 60-minute connection maximum
- 10,000 connections per cluster
- SSL required

#### SSL/TLS Requirements

Aurora DSQL uses the [PostgreSQL wire protocol](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html) and enforces SSL:

```
sslmode: verify-full
sslnegotiation: direct      # PostgreSQL 17+ drivers (better performance)
port: 5432
database: postgres           # single database per cluster
```

**Key details:**
- SSL always enabled server-side
- Use `verify-full` to verify server certificate
- Use `direct` TLS negotiation for PostgreSQL 17+ compatible drivers
- System trust store must include Amazon Root CA

#### Connection Pooling (Recommended)

For production applications:
- SHOULD Implement connection pooling
- ALWAYS Configure token refresh before expiration
- MUST Set appropriate pool size (e.g., max: 10, min: 2)
- MUST Configure connection lifetime and idle timeout
- MUST Generate fresh token in `BeforeConnect` or equivalent hook

#### Security Best Practices

- ALWAYS dynamically set crededntials
- MUST use IAM authentication exclusively
- ALWAYS use SSL/TLS with certificate verification
- SHOULD grant least privilege IAM permissions
- ALWAYS rotate tokens before expiration
- SHOULD use connection pooling to minimize token generation overhead

---

### Audit Logging

**CloudTrail integration:**
- Enable CloudTrail logging for DSQL API calls
- Monitor token generation patterns
- Track cluster configuration changes
- Set up alerts for suspicious activity

**Query logging:**
- Enable query logging if available
- Monitor slow queries and connection patterns
- Track failed authentication attempts
- Review logs regularly for anomalies

---

### Access Control

**Database-level security:**
- Create schema-specific users for applications
- Grant minimal required privileges (SELECT, INSERT, UPDATE, DELETE)
- Admin users should only perform administrative tasks
- Regularly audit user permissions and access patterns

**Example IAM policy for non-admin users:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dsql:DbConnect",
      "Resource": "arn:aws:dsql:*:*:cluster/*"
    }
  ]
}
```

---

## Operational Rules

### Query Execution

**For Ad-Hoc Queries and Data Exploration:**
- MUST ALWAYS Execute DIRECTLY using MCP server or psql one-liners
- SHOULD Return results immediately

**Writing Scripts REQUIRES at least 1 of:**
- Permanent migrations in database
- Reusable utilities
- EXPLICIT user request

---

### Schema Design Rules
- MUST use **simple PostgreSQL types:** VARCHAR, TEXT, INTEGER, BOOLEAN, TIMESTAMP
- MUST store arrays as TEXT (comma-separated is recommended)
- MUST store JSON objects as TEXT (JSON.stringify)
- ALWAYS include tenant_id in tables for multi-tenant isolation
- SHOULD create async indexes for tenant_id and common query patterns

### Schema (DDL) Rules
- REQUIRED: **at most one DDL statement** per operation
- ALWAYS separate schema (DDL) and data (DML) changes
- MUST use **`CREATE INDEX ASYNC`:**  No synchronous creation
  - MAXIMUM: **24 indexes per table**
  - MAXIMUM: **8 columns per index**
- **Asynchronous Execution:** DDL ALWAYS runs asynchronously
- To add a column with DEFAULT or NOT NULL:
  1. MUST issue ADD COLUMN specifying only the column name and data type
  2. MUST then issue UPDATE to populate existing rows
  3. MAY then issue ALTER COLUMN to apply the constraint
- MUST issue a **separate ALTER TABLE statement for each column** modification.


### Transaction Rules
- SHOULD modify **at most 3000 rows** per transaction
- SHOULD have maximum **10 MiB data size** per write transaction
- SHOULD expect **5-minute** transaction duration
- ALWAYS expect repeatable read isolation

---

### Application-Layer Patterns

**MANDATORY for Application Referential Integrity:**
If foreign key constraints (application referential integrity) are required,
instead implementation:
- MUST validate parent references before INSERT
- MUST check for dependents before DELETE
- MUST implement cascade logic in application code
- MUST handle orphaned records in application layer

**MANDATORY for Multi-Tenant Isolation:**
- tenantId is ALWAYS first parameter in repository methods
- ALL queries include WHERE tenant_id = ?
- ALWAYS validate tenant ownership before operations
- ALWAYS reject cross-tenant data access

### Migration Patterns

- REQUIRED: One DDL statement per migration step
- SHOULD Use IF NOT EXISTS for idempotency
- SHOULD Add column first, then UPDATE with defaults
- REQUIRED: Each DDL executes separately

---

## Database Connectivity Tools

DSQL has many tools for connecting including 10 database drivers, 4, ORM libraries, and 3 specialized adapters
across various languages as listed in the [programming guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/aws-sdks.html). PREFER using connectors, drivers, ORM libraries, and adapters.

### Database Drivers

Low-level libraries that directly connect to the database:

| Programming Language | Driver | Sample Repository |
|---------------------|--------|-------------------|
| **C++** | libpq | [C++ libpq samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/cpp/libpq) |
| **C# (.NET)** | Npgsql | [.NET Npgsql samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/dotnet/npgsql) |
| **Go** | pgx | [Go pgx samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/go/pgx) |
| **Java** | pgJDBC | [Java pgJDBC samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/java/pgjdbc) |
| **Java** | DSQL Connector for JDBC | [JDBC samples]() |
| **JavaScript** | DSQL Connector for node-postgres | [Node.js samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/node-postgres) |
| **JavaScript** | DSQL Connector for Postgres.js | [Postgres.js samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/javascript/postgres-js) |
| **Python** | Psycopg | [Python Psycopg samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/psycopg) |
| **Python** | DSQL Connector for Psycopg2 | [Python Psycopg2 samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/python/psycopg2 ) |
| **Python** | DSQL Connector for Asyncpg | [Python Asyncpg samples](https://github.com/awslabs/aurora-dsql-python-connector/tree/main/examples/asyncpg)|
| **Ruby** | pg | [Ruby pg samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/ruby/ruby-pg) |
| **Rust** | SQLx | [Rust SQLx samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/rust/sqlx) |

### Object-Relational Mapping (ORM) Libraries

Standalone libraries that provide object-relational mapping functionality:

| Programming Language | ORM Library | Sample Repository |
|---------------------|-------------|-------------------|
| **Java** | Hibernate | [Hibernate Pet Clinic App](https://github.com/awslabs/aurora-dsql-hibernate/tree/main/examples/pet-clinic-app) |
| **Python** | SQLAlchemy | [SQLAlchemy Pet Clinic App](https://github.com/awslabs/aurora-dsql-sqlalchemy/tree/main/examples/pet-clinic-app) |
| **TypeScript** | Sequelize | [TypeScript Sequelize samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/typescript/sequelize) |
| **TypeScript** | TypeORM | [TypeScript TypeORM samples](https://github.com/aws-samples/aurora-dsql-samples/tree/main/typescript/type-orm) |

### Aurora DSQL Adapters and Dialects

Specific extensions that make existing ORMs work with Aurora DSQL:

| Programming Language | ORM/Framework | Repository |
|---------------------|---------------|------------|
| **Java** | Hibernate | [Aurora DSQL Hibernate Adapter](https://github.com/awslabs/aurora-dsql-hibernate/) |
| **Python** | Django | [Aurora DSQL Django Adapter](https://github.com/awslabs/aurora-dsql-django/) |
| **Python** | SQLAlchemy | [Aurora DSQL SQLAlchemy Adapter](https://github.com/awslabs/aurora-dsql-sqlalchemy/) |


---

## Horizontal Scaling: Best Practice

Aurora DSQL is designed for massive horizontal scale without latency degradation.

### Connection Strategy

- **PREFER more concurrent connections with smaller batches** - Higher concurrency typically yields better throughput
- **SHOULD implement connection pooling** - Reuse connections to minimize token overhead; respect 10,000 max per cluster
- **PREFER imitial pool size 10-50 per instance** - Generate fresh tokens in pool hooks (e.g., `BeforeConnect`) for 15-minute expiration
- **SHOULD retry internal errors with new connection** - Internal errors are retryable, but SHOULD use a new connection from the pool
- **SHOULD implement backoff with jitter** - Avoid thundering herd; scale pools gradually

### Batch Size Optimization

- **PREFER batches of 500-1,000 rows** - Balance throughput and transaction limits (3,000 rows, 10 MiB, 5 minutes max)
- **SHOULD process batches concurrently** - Use multiple connections; consider multiple threads for bulk loading
- **Smaller batches reduce** lock contention, enable better concurrency, fail faster, distribute load evenly

### AVOID Hot Keys

Hot keys (frequently accessed rows) create bottlenecks. For detailed analysis, see ["How to avoid hot keys in Aurora DSQL"](https://marc-bowes.com/dsql-avoid-hot-keys.html).

**Key strategies:**

- **PREFER UUIDs for primary keys** - Use `gen_random_uuid()` for distributed writes; avoid sequential IDs
  - **MUST NOT use globally incrementing sequences** - DSQL doesn't support SERIAL; random identifiers distribute better
- **SHOULD avoid aggregate update patterns** - Year-to-date totals and running counters create hot keys via read-modify-write
  - **RECOMMENDED: Compute aggregates via queries** - Calculate totals with SELECT when needed; eventual consistency often acceptable
- **Accept contention only for genuine constraints** - Inventory management and account balances justify contention; sequential numbering and visit tracking don't

---

## Quick Reference

### Schema Operations
```sql
CREATE INDEX ASYNC idx_name ON table(column);          ← ALWAYS ASYNC
ALTER TABLE t ADD COLUMN c VARCHAR(50);                ← ONE AT A TIME
ALTER TABLE t ADD COLUMN c2 INTEGER;                   ← SEPARATE STATEMENT
UPDATE table SET c = 'default' WHERE c IS NULL;        ← AFTER ADD COLUMN
```

### Supported Data Types
```
VARCHAR, TEXT, INTEGER, DECIMAL, BOOLEAN, TIMESTAMP, UUID
```

### Supported Key
```
PRIMARY KEY, UNIQUE, NOT NULL, CHECK, DEFAULT (in CREATE TABLE)
```

Join on any keys; DSQL preserves DB referential integrity, when needed application referential
integrity must be separately enforced.

### Transaction Requirements
```
Rows: 3,000 max
Size: 10 MiB max
Duration: 5 minutes max
Isolation: Repeatable Read (fixed)
```
