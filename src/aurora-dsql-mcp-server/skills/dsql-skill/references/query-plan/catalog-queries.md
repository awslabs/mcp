# Catalog Queries Reference

Exact SQL for interrogating optimizer statistics and actual cardinalities against the DSQL cluster.

## Table of Contents

1. [Table-Level Statistics (pg_class)](#table-level-statistics)
2. [Column Statistics (pg_stats)](#column-statistics)
3. [Index Definitions](#index-definitions)
4. [Actual Row Counts](#actual-row-counts)
5. [Actual Distinct Counts](#actual-distinct-counts)
6. [Value Distribution Analysis](#value-distribution-analysis)

---

## Table-Level Statistics

Retrieve optimizer's view of table size for all referenced tables:

```sql
SELECT
  schemaname,
  relname,
  reltuples::bigint AS estimated_rows,
  relpages
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = '{schema}'
  AND c.relname IN ('{table1}', '{table2}', '{table3}');
```

Compare `reltuples` against actual `COUNT(*)`. A divergence >20% on the table-stats snapshot indicates stale `reltuples` requiring `ANALYZE`. This is distinct from the row-estimate-vs-actual error thresholds used for plan findings (see plan-interpretation.md: 2x–5x minor, 5x–50x significant, 50x+ severe).

## Column Statistics

Retrieve statistics for columns involved in joins, WHERE clauses, and estimation errors:

```sql
SELECT
  tablename,
  attname,
  null_frac,
  n_distinct,
  most_common_vals,
  most_common_freqs,
  histogram_bounds,
  correlation
FROM pg_stats
WHERE schemaname = '{schema}'
  AND tablename = '{table}'
  AND attname IN ('{col1}', '{col2}');
```

**Key fields:**

| Field               | Use                                                    |
| ------------------- | ------------------------------------------------------ |
| `n_distinct`        | Negative = fraction of rows; Positive = absolute count |
| `most_common_vals`  | Values the optimizer considers frequent                |
| `most_common_freqs` | Corresponding frequencies (sum < 1.0)                  |
| `histogram_bounds`  | Equal-frequency bucket boundaries for non-MCV values   |
| `correlation`       | Physical row order correlation (-1 to 1)               |

## Index Definitions

Retrieve existing indexes on referenced tables. DSQL does not populate the cumulative `pg_stat_user_indexes` counters (`idx_scan`, `idx_tup_read`, `idx_tup_fetch`) that standard PostgreSQL exposes — infer index usage from the EXPLAIN plan instead.

```sql
SELECT
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname = '{schema}'
  AND tablename IN ('{table1}', '{table2}', '{table3}')
ORDER BY tablename, indexname;
```

## Actual Row Counts

Retrieve ground-truth row counts for comparison against `pg_class.reltuples`:

```sql
SELECT COUNT(*) AS actual_rows FROM {schema}.{table};
```

Run for each referenced table. Present results as:

| Table  | pg_class.reltuples | Actual COUNT(*) | Difference         |
| ------ | ------------------ | --------------- | ------------------ |
| table1 | N                  | M               | X% over/undercount |

## Actual Distinct Counts

Retrieve actual distinct values for columns in joins and WHERE predicates:

```sql
SELECT COUNT(DISTINCT {column}) AS distinct_count FROM {schema}.{table};
```

Compare against `pg_stats.n_distinct`:

- If `n_distinct` is positive: compare directly
- If `n_distinct` is negative: multiply absolute value by actual row count to get estimated distinct count

## Column Types for Predicate Columns

Retrieve the declared types for columns used in WHERE predicates and JOIN conditions, to detect type coercion index bypass (see plan-interpretation.md):

```sql
SELECT
  c.table_name,
  c.column_name,
  c.data_type,
  c.udt_name,
  c.is_nullable
FROM information_schema.columns c
WHERE c.table_schema = '{schema}'
  AND c.table_name IN ('{table1}', '{table2}')
  AND c.column_name IN ('{col1}', '{col2}');
```

Cross-reference the column type against predicate literals visible in the EXPLAIN output. When the types differ, check the implicit cast compatibility matrix in plan-interpretation.md to determine whether the mismatch prevents index usage.

## B-Tree Cross-Type Operator Support

Determine which type pairs the DSQL B-Tree access method supports for index scans. If a (predicate-type, column-type) pair has no registered operator, the index cannot be used for that comparison:

```sql
SELECT DISTINCT
  lt.typname AS left_type,
  rt.typname AS right_type
FROM pg_amop ao
JOIN pg_type lt ON lt.oid = ao.amoplefttype
JOIN pg_type rt ON rt.oid = ao.amoprighttype
WHERE ao.amopmethod = 10003
  AND ao.amoplefttype != ao.amoprighttype
ORDER BY lt.typname, rt.typname;
```

This returns only the cross-type pairs (where left and right types differ). Same-type pairs are always supported. Use this to confirm whether a suspected type mismatch actually prevents index usage — if the pair appears in the result, the index CAN be used and the issue lies elsewhere.

To check a specific pair:

```sql
SELECT EXISTS (
  SELECT 1
  FROM pg_amop ao
  JOIN pg_type lt ON lt.oid = ao.amoplefttype
  JOIN pg_type rt ON rt.oid = ao.amoprighttype
  WHERE ao.amopmethod = 10003
    AND lt.typname = '{predicate_type}'
    AND rt.typname = '{column_type}'
) AS index_usable;
```

## Indexed Column Types

Retrieve index definitions together with their column types to identify type coercion bypass candidates:

```sql
SELECT
  i.indexname,
  i.tablename,
  a.attname AS column_name,
  t.typname AS column_type,
  i.indexdef
FROM pg_indexes i
JOIN pg_class ic ON ic.relname = i.indexname
JOIN pg_index ix ON ix.indexrelid = ic.oid
JOIN pg_attribute a ON a.attrelid = ix.indrelid
  AND a.attnum = ANY(ix.indkey)
JOIN pg_type t ON t.oid = a.atttypid
JOIN pg_namespace n ON n.oid = ic.relnamespace
WHERE n.nspname = '{schema}'
  AND i.tablename IN ('{table1}', '{table2}')
ORDER BY i.tablename, i.indexname, a.attnum;
```

Use this when a Full Scan appears despite an apparently usable index — compare the index column's `column_type` against the predicate literal's inferred type.

## Value Distribution Analysis

For columns with suspected data skew, retrieve the actual top-N value frequencies:

```sql
SELECT
  {column},
  COUNT(*) AS freq,
  ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM {schema}.{table}), 5) AS fraction
FROM {schema}.{table}
GROUP BY {column}
ORDER BY freq DESC
LIMIT 20;
```

Compare results against `most_common_vals` and `most_common_freqs` from pg_stats. Flag:

- Values present in data but missing from `most_common_vals`
- Values whose actual frequency differs >2x from `most_common_freqs`
- Skewed distributions where top values account for >50% of rows

### Correlated Predicate Verification

To verify predicate correlation, measure the actual combined selectivity:

```sql
SELECT COUNT(*) AS combined_count
FROM {schema}.{table}
WHERE {predicate1} AND {predicate2};
```

Then compare against the independence assumption:

```
Expected (independent) = (count_pred1 / total_rows) × (count_pred2 / total_rows) × total_rows
Actual = combined_count
Error = actual / expected
```

An error >3x indicates significant predicate correlation.
