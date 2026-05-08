# Query Rewrites Reference — DSQL-Specific

SQL rewrites that address Aurora DSQL-specific behaviors and limitations. Apply these when the plan reveals inefficiency unique to DSQL's distributed architecture or optimizer constraints.

## Table of Contents

1. [Replace COUNT(*) with reltuples Estimate](#replace-count-with-reltuples-estimate)
2. [Split Large Joins to Enable Optimal Join Ordering](#split-large-joins-to-enable-optimal-join-ordering)

---

## Replace COUNT(*) with reltuples Estimate

When a query performs `COUNT(*)` on a large table, rewrite to use the `reltuples` value from `pg_class` for an approximate row count. This is a common workaround for cases where `COUNT(*)` is too slow or times out on large tables.

**When to apply:** An approximate count is acceptable and the table is large enough that `COUNT(*)` is prohibitively expensive.

**Do not apply:** The application requires an exact count.

```sql
-- Original
SELECT COUNT(*) AS exact_count
FROM big_table;

-- Rewritten (DSQL)
SELECT reltuples::bigint AS estimated_count
FROM pg_class
WHERE oid = 'public.big_table'::regclass;
```

```sql
-- Not applicable: exact count required
SELECT COUNT(*) AS exact_count
FROM big_table;
```

---

## Split Large Joins to Enable Optimal Join Ordering

If a query joins more tables than the optimizer's DP threshold (e.g., 10 joins for Aurora DSQL), rewrite it into multiple subqueries each joining no more tables than the threshold, then join the subquery results.

This allows the PostgreSQL-based DSQL engine to apply dynamic-programming (DP) join ordering within each smaller block, producing a better overall join plan than a greedy algorithm on many tables.

**When to apply:** The total number of joined tables exceeds the DP threshold (`join_collapse_limit` or `from_collapse_limit`). Partition the join into CTEs each with table count at or below the threshold, push down relevant filters, and join the CTE results.

**Do not apply:** The total table count is at or below the threshold, or splitting would prevent necessary cross-block optimizations.

```sql
-- Original
SELECT *
FROM R1
  JOIN R2 ON R1.id = R2.id
  JOIN R3 ON R2.id = R3.id
  JOIN R4 ON R3.id = R4.id
  JOIN R5 ON R4.id = R5.id
  JOIN R6 ON R5.id = R6.id
  JOIN R7 ON R6.id = R7.id
WHERE Filters;

-- Rewritten (DSQL)
WITH
  sub1 AS (
    SELECT *
    FROM R1
      JOIN R2 ON R1.id = R2.id
      JOIN R3 ON R2.id = R3.id
      JOIN R4 ON R3.id = R4.id
    WHERE <Filter 1>
  ),
  sub2 AS (
    SELECT *
    FROM R5
      JOIN R6 ON R5.id = R6.id
      JOIN R7 ON R6.id = R7.id
    WHERE <Filter 2>
  )
SELECT *
FROM sub1
JOIN sub2 ON sub1.id = sub2.id;
```

```sql
-- Not applicable: total tables ≤ DP threshold
SELECT *
FROM R1
  JOIN R2 ON R1.id = R2.id
  JOIN R3 ON R2.id = R3.id
  JOIN R4 ON R3.id = R4.id
WHERE Filters;
```
