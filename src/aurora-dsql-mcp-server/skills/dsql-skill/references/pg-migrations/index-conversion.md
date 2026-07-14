# Index Conversion for DSQL

Run `dsql_lint(fix=true)` first — it handles most index conversions automatically (ASYNC,
USING gin/gist/brin/hash → btree, CONCURRENTLY removal, INCLUDE preservation, sort order).

This file covers only the patterns `dsql_lint` flags as **unfixable** and cannot auto-convert:

- Partial indexes (WHERE clause) — `index_partial`
- Expression indexes — `index_expression`
- Operator class removal — `text_pattern_ops`

Sources:

- [Asynchronous Indexes](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-indexes.html)
- [DSQL SQL Dialect Blog](https://aws.amazon.com/blogs/database/dsql-sql-dialect-how-amazon-aurora-dsql-differs-from-single-instance-postgresql/)

## Table of Contents

1. [GIN Index Conversion](#gin-index-conversion)
2. [GiST Index Conversion](#gist-index-conversion)
3. [BRIN Index Conversion](#brin-index-conversion)
4. [Partial Index Conversion](#partial-index-conversion)
5. [Expression Index Conversion](#expression-index-conversion)
6. [Index Limits](#index-limits)
7. [Monitoring Async Index Status](#monitoring-async-index-status)
8. [Conversion Decision Flowchart](#conversion-decision-flowchart)

---

## GIN Index Conversion

GIN indexes are used for full-text search, JSONB containment, and array operations.
DSQL uses btree indexes exclusively — convert GIN to btree where possible.

### JSONB GIN → btree on Extracted Key

```sql
-- PostgreSQL: GIN index on JSONB column
CREATE INDEX idx_users_prefs ON users USING gin (preferences);
-- Used for: preferences @> '{"theme":"dark"}'

-- DSQL: No equivalent index. JSONB operators work at runtime without index.
-- The query still works, just without index acceleration:
SELECT * FROM users WHERE preferences @> '{"theme":"dark"}';

-- If you need indexed lookup on a specific JSON key, extract to a STORED generated column.
-- Use GENERATED ALWAYS AS (...) STORED so the column is always populated — an
-- ADD COLUMN + UPDATE backfill would leave rows inserted between the two statements
-- with NULL and the index would silently miss them.
ALTER TABLE users ADD COLUMN pref_theme text
  GENERATED ALWAYS AS (preferences->>'theme') STORED;
CREATE INDEX ASYNC idx_users_pref_theme ON users (pref_theme);
-- Query: SELECT * FROM users WHERE pref_theme = 'dark';
```

### Array GIN → Join Table

```sql
-- PostgreSQL: GIN index on array column
CREATE INDEX idx_posts_tags ON posts USING gin (tags);
-- Used for: tags @> ARRAY['database']

-- DSQL: Array column types not supported. Normalize tags into a join table for
-- indexed lookup, or store as jsonb if indexed lookup isn't needed.
CREATE TABLE post_tags (
  post_id uuid NOT NULL,
  tag text NOT NULL
);
CREATE INDEX ASYNC idx_post_tags_tag ON post_tags (tag);
CREATE INDEX ASYNC idx_post_tags_post ON post_tags (post_id);
-- Query: SELECT DISTINCT post_id FROM post_tags WHERE tag = 'database';
```

### Full-Text Search GIN → External Service

```sql
-- PostgreSQL: GIN index for full-text search
CREATE INDEX idx_articles_search ON articles USING gin (to_tsvector('english', title || ' ' || body));

-- DSQL: No equivalent. Use OpenSearch/Elasticsearch for full-text search.
-- Store the text in DSQL, index in OpenSearch, query OpenSearch for IDs, then fetch from DSQL.
-- Remove the index entirely from the DSQL schema.
```

### Trigram GIN (pg_trgm) → Application Layer

```sql
-- PostgreSQL: Trigram index for LIKE '%pattern%'
CREATE INDEX idx_users_name_trgm ON users USING gin (name gin_trgm_ops);

-- DSQL: No equivalent. Options:
-- 1. Use prefix matching (LIKE 'pattern%') with a btree index
CREATE INDEX ASYNC idx_users_name ON users (name);
-- 2. Use OpenSearch for fuzzy/substring matching
-- 3. Accept full scan for infrequent LIKE '%pattern%' queries
```

---

## GiST Index Conversion

GiST indexes are used for geometric data, range types, and exclusion constraints.

### Geometric GiST → No Index

```sql
-- PostgreSQL: GiST index on point column
CREATE INDEX idx_locations_coords ON locations USING gist (coords);

-- DSQL: Geometric types stored as text. No spatial indexing.
-- Option 1: Store lat/lng as separate numeric columns, index those
ALTER TABLE locations ADD COLUMN lat double precision;
ALTER TABLE locations ADD COLUMN lng double precision;
CREATE INDEX ASYNC idx_locations_lat ON locations (lat);
CREATE INDEX ASYNC idx_locations_lng ON locations (lng);
-- Bounding box queries: WHERE lat BETWEEN x1 AND x2 AND lng BETWEEN y1 AND y2

-- Option 2: Use a geohash text column for proximity queries
ALTER TABLE locations ADD COLUMN geohash text;
CREATE INDEX ASYNC idx_locations_geohash ON locations (geohash);
-- Prefix matching: WHERE geohash LIKE 'dr5ru%'
```

### Range GiST → Separate Columns

```sql
-- PostgreSQL: GiST index on range type
CREATE INDEX idx_events_during ON events USING gist (during);
-- Used for: during && '[2024-01-01, 2024-02-01)'

-- DSQL: Store range as two columns
CREATE TABLE events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  start_time timestamptz NOT NULL,
  end_time timestamptz NOT NULL
);
CREATE INDEX ASYNC idx_events_start ON events (start_time);
CREATE INDEX ASYNC idx_events_end ON events (end_time);
-- Overlap query: WHERE start_time < '2024-02-01' AND end_time > '2024-01-01'
```

---

## BRIN Index Conversion

BRIN indexes are used for large, naturally-ordered tables (time-series data).

```sql
-- PostgreSQL: BRIN index on timestamp column
CREATE INDEX idx_logs_created ON logs USING brin (created_at);

-- DSQL: Use btree. DSQL's PK-ordered storage provides similar benefits
-- if created_at correlates with PK order.
CREATE INDEX ASYNC idx_logs_created ON logs (created_at);

-- If the table is very large and you need to limit index size,
-- use a composite index with the most selective column first:
CREATE INDEX ASYNC idx_logs_tenant_created ON logs (tenant_id, created_at DESC);
```

---

## Partial Index Conversion

`dsql_lint` flags partial indexes (`index_partial`) as unfixable. The conversion is to
remove the WHERE clause and create a full index.

```sql
-- PostgreSQL: Partial index
CREATE INDEX idx_orders_pending ON orders (customer_id, created_at)
  WHERE status = 'pending';

-- DSQL: Full index (WHERE removed). Filter at query time.
CREATE INDEX ASYNC idx_orders_pending ON orders (customer_id, created_at);
-- The query still works, just scans more index entries:
-- SELECT * FROM orders WHERE customer_id = $1 AND status = 'pending' ORDER BY created_at;

-- Better alternative: Include status in the index for filtering
CREATE INDEX ASYNC idx_orders_customer_status ON orders (customer_id, status, created_at DESC);
-- Query: WHERE customer_id = $1 AND status = 'pending' ORDER BY created_at DESC
```

**Trade-off:** Full indexes are larger than partial indexes. If the partial condition is very
selective (e.g., only 1% of rows match), the full index will be significantly larger. Consider
whether the query pattern justifies the index at all, or if a composite index with the filter
column is better.

---

## Expression Index Conversion

`dsql_lint` flags expression indexes (`index_expression`) as unfixable. The conversion is to
create a computed column (GENERATED ALWAYS AS STORED) and index that column.

```sql
-- PostgreSQL: Expression index
CREATE INDEX idx_users_email_lower ON users (lower(email));

-- DSQL: Computed column + index
ALTER TABLE users ADD COLUMN email_lower text
  GENERATED ALWAYS AS (lower(email)) STORED;
CREATE INDEX ASYNC idx_users_email_lower ON users (email_lower);
-- Query: WHERE email_lower = lower($1)
```

```sql
-- PostgreSQL: Expression index on date extraction
CREATE INDEX idx_orders_year ON orders (extract(year FROM created_at));

-- DSQL: Computed column + index
ALTER TABLE orders ADD COLUMN created_year integer
  GENERATED ALWAYS AS (extract(year FROM created_at)::integer) STORED;
CREATE INDEX ASYNC idx_orders_year ON orders (created_year);
-- Query: WHERE created_year = 2024
```

```sql
-- PostgreSQL: Expression index on JSON field
CREATE INDEX idx_users_city ON users ((preferences->>'city'));

-- DSQL: Computed column + index
ALTER TABLE users ADD COLUMN pref_city text
  GENERATED ALWAYS AS (preferences->>'city') STORED;
CREATE INDEX ASYNC idx_users_city ON users (pref_city);
-- Query: WHERE pref_city = 'Seattle'
```

**Note:** DSQL supports `GENERATED ALWAYS AS (expr) STORED` — this is the correct approach
for expression indexes. The computed column is automatically maintained by the database.

---

## Index Limits

| Limit                 | Value |
| --------------------- | ----- |
| Max indexes per table | 24    |
| Max columns per index | 8     |
| Max PK/index key size | 1 KiB |

**Strategy when approaching 24 index limit:**

- Use composite indexes instead of multiple single-column indexes
- Use INCLUDE columns for covering indexes (avoids storage round-trips)
- Remove indexes for rarely-used query patterns
- Consider if the query can use an existing composite index with a prefix match

---

## Monitoring Async Index Status

Indexes created with ASYNC are not immediately usable. Monitor:

```sql
-- Check for indexes still being built
SELECT indexrelid::regclass AS index_name, indisvalid AS is_ready
FROM pg_index
WHERE NOT indisvalid;

-- If this returns rows, those indexes are still building.
-- Queries work but won't use the index until indisvalid = true.
```

**Do NOT rely on index performance until `indisvalid = true`.**

---

## Conversion Decision Flowchart

```
Is it a btree index?
├── Yes → CREATE INDEX ASYNC (preserve columns, INCLUDE, sort order)
│
├── Is it GIN?
│   ├── For JSONB containment → extract key to column + btree
│   ├── For array ops → normalize to join table + btree
│   ├── For FTS → remove (use OpenSearch)
│   └── For trigram → remove or use prefix btree
│
├── Is it GiST?
│   ├── For geometry → separate lat/lng columns + btree
│   ├── For ranges → separate start/end columns + btree
│   └── For exclusion → remove (enforce in application)
│
├── Is it BRIN?
│   └── Convert to btree (DSQL PK-order gives similar benefit)
│
├── Is it a partial index (WHERE)?
│   └── Remove WHERE, create full index (or add filter column to index)
│
├── Is it an expression index?
│   └── Add GENERATED ALWAYS AS STORED column + btree index on it
│
└── Is it CONCURRENTLY?
    └── Remove CONCURRENTLY, use ASYNC
```
