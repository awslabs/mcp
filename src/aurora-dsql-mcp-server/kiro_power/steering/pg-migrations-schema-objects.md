# Schema Object Conversion for DSQL

Conversion patterns for PostgreSQL schema objects that `dsql_lint` either doesn't handle
or flags as unfixable. Covers ENUM types, materialized views, extensions, roles/grants,
multi-schema flattening, and other structural conversions.

Sources:

- [Supported SQL Features](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-supported-sql-features.html)
- [Migration Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-migration-guide.html)
- [Database Roles and IAM](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)

## Table of Contents

1. [ENUM Types → CHECK Constraints](#enum-types--check-constraints)
2. [Composite Types → JSONB or Separate Columns](#composite-types--jsonb-or-separate-columns)
3. [Materialized Views → Regular Views](#materialized-views--regular-views)
4. [Temporary Tables → Regular Tables or CTEs](#temporary-tables--regular-tables-or-ctes)
5. [Partitioned Tables → Flat Tables](#partitioned-tables--flat-tables)
6. [Inherited Tables → Flat (Columns Merged)](#inherited-tables--flat-columns-merged)
7. [Extensions → Alternatives](#extensions--alternatives)
8. [Roles/GRANT → IAM Mapping](#rolesgrant--iam-mapping)
9. [Multi-Schema Handling](#multi-schema-handling)
10. [UNLOGGED Tables → Regular Tables](#unlogged-tables--regular-tables)
11. [CREATE DOMAIN → Preserved](#create-domain--preserved)
12. [GENERATED ALWAYS AS STORED → Preserved](#generated-always-as-stored--preserved)
13. [WITH (storage parameters) → Removed](#with-storage-parameters--removed)
14. [Conversion Checklist](#conversion-checklist)

---

## ENUM Types → CHECK Constraints

PostgreSQL ENUM types convert to varchar + CHECK constraint in DSQL.

**Before (PostgreSQL):**

```sql
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'resolved', 'closed');
CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TABLE tickets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  status ticket_status NOT NULL DEFAULT 'open',
  priority priority_level NOT NULL DEFAULT 'medium'
);
```

**After (DSQL):**

```sql
CREATE TABLE tickets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  status varchar(20) NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
  priority varchar(20) NOT NULL DEFAULT 'medium'
    CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);
```

**Important:** Define CHECK constraints at CREATE TABLE time in DSQL. Use the Table Recreation
Pattern to add CHECK constraints to existing tables.

**Conversion steps:**

1. Find all `CREATE TYPE ... AS ENUM` statements
2. Find all columns using those types
3. Replace the column type with `varchar(N)` where N fits the longest value
4. Add `CHECK (column IN ('val1', 'val2', ...))` inline in CREATE TABLE
5. Drop the `CREATE TYPE` statement entirely

---

## Composite Types → JSONB or Separate Columns

```sql
-- PostgreSQL
CREATE TYPE address AS (street text, city text, state text, zip text);
CREATE TABLE customers (id uuid PRIMARY KEY, home_address address);

-- DSQL Option 1: JSONB column (flexible)
CREATE TABLE customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  home_address jsonb  -- {"street":"...","city":"...","state":"...","zip":"..."}
);
-- Query: SELECT home_address->>'city' FROM customers;

-- DSQL Option 2: Separate columns (indexable)
CREATE TABLE customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  home_street text,
  home_city text,
  home_state text,
  home_zip text
);
CREATE INDEX ASYNC idx_customers_city ON customers (home_city);
```

**Decision:** Use JSONB if you rarely query individual fields. Use separate columns if you
need to index or filter on specific fields.

---

## Materialized Views → Regular Views

```sql
-- PostgreSQL
CREATE MATERIALIZED VIEW monthly_stats AS
  SELECT date_trunc('month', created_at) AS month, COUNT(*) AS total
  FROM orders GROUP BY 1;
-- Refreshed with: REFRESH MATERIALIZED VIEW monthly_stats;

-- DSQL: Regular view (always up-to-date, no refresh needed)
CREATE VIEW monthly_stats AS
  SELECT date_trunc('month', created_at) AS month, COUNT(*) AS total
  FROM orders GROUP BY 1;
```

**Trade-off:** Regular views compute on every query (no caching). For expensive aggregations:

- Use application-layer caching (Redis, ElastiCache)
- Pre-compute into a summary table updated by application logic
- Accept the query cost if the dataset is small

---

## Temporary Tables → Regular Tables or CTEs

```sql
-- PostgreSQL
CREATE TEMP TABLE staging_data (id serial, payload jsonb);
INSERT INTO staging_data SELECT ...;
-- Used within a session, auto-dropped on disconnect

-- DSQL Option 1: CTE (for single-query use)
WITH staging_data AS (
  SELECT id, payload FROM source_table WHERE ...
)
SELECT * FROM staging_data WHERE ...;

-- DSQL Option 2: Regular table with prefix (for multi-statement use)
CREATE TABLE _tmp_staging_data (
  id bigint GENERATED BY DEFAULT AS IDENTITY (CACHE 1),
  session_id uuid NOT NULL,  -- track which session owns the data
  payload jsonb
);
-- Clean up: DELETE FROM _tmp_staging_data WHERE session_id = $1;
```

---

## Partitioned Tables → Flat Tables

```sql
-- PostgreSQL
CREATE TABLE events (
  id uuid, tenant_id uuid, created_at timestamptz, data jsonb
) PARTITION BY RANGE (created_at);
CREATE TABLE events_2024_q1 PARTITION OF events FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

-- DSQL: Flat table (DSQL handles distribution internally via PK-ordered storage)
CREATE TABLE events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  data jsonb
);
CREATE INDEX ASYNC idx_events_tenant_created ON events (tenant_id, created_at DESC);
```

**Note:** DSQL's PK-ordered storage and distributed architecture handle data distribution
automatically. Manual partitioning is not needed and not supported.

---

## Inherited Tables → Flat (Columns Merged)

```sql
-- PostgreSQL
CREATE TABLE base_entity (id uuid PRIMARY KEY, created_at timestamptz, updated_at timestamptz);
CREATE TABLE users (email text, name text) INHERITS (base_entity);
CREATE TABLE products (sku text, price numeric) INHERITS (base_entity);

-- DSQL: Merge inherited columns into each child table
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  email text,
  name text
);

CREATE TABLE products (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  sku text,
  price numeric(10,2)
);
```

---

## Extensions → Alternatives

| PostgreSQL Extension   | DSQL Alternative           | Notes                                           |
| ---------------------- | -------------------------- | ----------------------------------------------- |
| uuid-ossp              | `gen_random_uuid()`        | Built-in, no extension needed                   |
| pgcrypto               | `gen_random_uuid()`        | For other crypto, use application layer         |
| pg_trgm                | None                       | Use OpenSearch for fuzzy search                 |
| postgis                | None                       | Store coords as numeric columns or geohash text |
| hstore                 | `jsonb` type               | Use jsonb column instead                        |
| citext                 | `varchar` + `lower()`      | Case-insensitive via application queries        |
| pg_stat_statements     | None                       | DSQL has own monitoring                         |
| btree_gin / btree_gist | None                       | Use btree indexes directly                      |
| tablefunc (crosstab)   | None                       | Pivot in application layer                      |
| ltree                  | `text` + application logic | Hierarchical queries in app                     |

**Conversion:**

```sql
-- PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SELECT uuid_generate_v4();

-- DSQL: Remove extension, replace function
-- DROP the CREATE EXTENSION statement
SELECT gen_random_uuid();  -- built-in replacement
```

---

## Roles/GRANT → IAM Mapping

DSQL supports `CREATE ROLE` and `GRANT/REVOKE` but they're linked to IAM.

```sql
-- PostgreSQL
CREATE ROLE app_reader WITH LOGIN PASSWORD 'secret';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_reader;

-- DSQL: Role creation works, but auth is IAM-based (no passwords)
CREATE ROLE app_reader;
GRANT USAGE ON SCHEMA public TO app_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_reader;
-- Authentication: IAM role mapped to database role via dsql:DbConnect policy
```

**Key differences:**

- Authentication is always IAM token-based (no `WITH LOGIN PASSWORD`)
- Use explicit GRANT per object (no `ALTER DEFAULT PRIVILEGES`)
- Implement Row-Level Security (RLS) in the application layer
- Remove `SECURITY DEFINER` from function definitions — after removal the function executes as the caller's role. Audit table-level GRANTs to every role that calls the function: missing GRANTs cause `permission denied` at runtime where the definer previously succeeded. Where the function gated row visibility (e.g., callers had no direct table GRANT and relied on the function's filter), removing `SECURITY DEFINER` requires re-granting access — typically via a view + RLS-in-application, since DSQL has no `SECURITY DEFINER` substitute.
- Admin role is predefined and immutable

**IAM mapping:**

```json
{
  "Effect": "Allow",
  "Action": "dsql:DbConnect",
  "Resource": "arn:aws:dsql:us-east-1:123456789012:cluster/cluster-id",
  "Condition": {
    "StringEquals": {
      "dsql:DbUser": "app_reader"
    }
  }
}
```

---

## Multi-Schema Handling

DSQL supports up to 10 schemas per database (DSQL service limit).

### ≤10 Schemas: Direct Migration

```sql
-- PostgreSQL schemas migrate directly
CREATE SCHEMA billing;
GRANT USAGE ON SCHEMA billing TO app_role;
CREATE TABLE billing.invoices (id uuid PRIMARY KEY, amount numeric(10,2));

CREATE SCHEMA support;
GRANT USAGE ON SCHEMA support TO app_role;
CREATE TABLE support.tickets (id uuid PRIMARY KEY, title text);
```

### >10 Schemas: Consolidate with Prefixes

```sql
-- PostgreSQL has 15 schemas — must consolidate to ≤10
-- Strategy: merge least-used schemas into 'public' with table name prefixes

-- Schema 'analytics' (overflow) → prefix tables
CREATE TABLE public.analytics_reports (id uuid PRIMARY KEY, ...);
CREATE TABLE public.analytics_dashboards (id uuid PRIMARY KEY, ...);

-- Update all references in application code:
-- FROM: analytics.reports → TO: public.analytics_reports
```

### search_path Behavior

```sql
-- DSQL supports search_path
SET search_path TO billing, public;
SELECT * FROM invoices;  -- resolves to billing.invoices

-- NOTE: After schema DDL, refresh connection for immediate visibility
```

---

## UNLOGGED Tables → Regular Tables

```sql
-- PostgreSQL: UNLOGGED for performance (data lost on crash)
CREATE UNLOGGED TABLE session_cache (key text PRIMARY KEY, value jsonb);

-- DSQL: All tables are durable. Remove UNLOGGED keyword.
CREATE TABLE session_cache (
  key text PRIMARY KEY,
  value jsonb
);
-- If you need non-durable caching, use ElastiCache/Redis instead.
```

---

## CREATE DOMAIN → Preserved

DSQL supports CREATE DOMAIN:

```sql
-- PostgreSQL
CREATE DOMAIN email_address AS varchar(255) CHECK (VALUE ~ '^[^@]+@[^@]+\.[^@]+$');

-- DSQL: Works as-is (DOMAIN is supported)
CREATE DOMAIN email_address AS varchar(255)
  CHECK (VALUE ~ '^[^@]+@[^@]+\.[^@]+$');
```

---

## GENERATED ALWAYS AS STORED → Preserved

DSQL supports computed columns:

```sql
-- PostgreSQL
CREATE TABLE products (
  price numeric(10,2),
  tax_rate numeric(4,2),
  total numeric(10,2) GENERATED ALWAYS AS (price * (1 + tax_rate)) STORED
);

-- DSQL: Works as-is
CREATE TABLE products (
  price numeric(10,2),
  tax_rate numeric(4,2),
  total numeric(10,2) GENERATED ALWAYS AS (price * (1 + tax_rate)) STORED
);
```

---

## WITH (storage parameters) → Removed

```sql
-- PostgreSQL
CREATE TABLE hot_data (id uuid PRIMARY KEY, data jsonb) WITH (fillfactor = 70);
ALTER TABLE hot_data SET (autovacuum_vacuum_threshold = 100);

-- DSQL: Remove all storage parameters. DSQL manages storage automatically.
CREATE TABLE hot_data (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), data jsonb);
-- No VACUUM needed — DSQL handles automatically.
```

---

## Conversion Checklist

- [ ] Find all `CREATE TYPE ... AS ENUM` → convert to CHECK constraints
- [ ] Find all `CREATE TYPE ... AS (composite)` → convert to jsonb or separate columns
- [ ] Find all `CREATE MATERIALIZED VIEW` → convert to regular VIEW
- [ ] Find all `CREATE TEMP TABLE` → convert to CTE or regular table with _tmp_ prefix
- [ ] Find all `PARTITION BY` → remove (DSQL handles distribution)
- [ ] Find all `INHERITS` → merge columns into child tables
- [ ] Find all `CREATE EXTENSION` → remove and use alternatives
- [ ] Find all `UNLOGGED` → remove keyword
- [ ] Find all `WITH (fillfactor=...)` → remove storage parameters
- [ ] Audit roles/grants → remove passwords, map to IAM
- [ ] Count schemas → consolidate if >10
- [ ] Run `dsql_lint(fix=true)` — auto-strips COLLATE clauses from all string columns
