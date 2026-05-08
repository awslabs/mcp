# Query Rewrites Reference

Generic SQL rewrites that can improve query performance. When a plan reveals inefficiency traceable to query structure (rather than missing indexes or stale statistics), recommend the applicable rewrite below.

## Table of Contents

1. [OR to IN](#or-to-in)
2. [LEFT JOIN with Null-Rejecting Predicate to INNER JOIN](#left-join-with-null-rejecting-predicate-to-inner-join)
3. [Propagate Filter to JOIN Columns](#propagate-filter-to-join-columns)
4. [Subquery Unnesting — Uncorrelated](#subquery-unnesting--uncorrelated)
5. [Subquery Unnesting — Correlated](#subquery-unnesting--correlated)
6. [Subquery Unnesting — Scalar](#subquery-unnesting--scalar)
7. [Push Computation to Constant Side](#push-computation-to-constant-side)
8. [Replace IN-Subquery with EXISTS](#replace-in-subquery-with-exists)
9. [Push GROUP BY into Subquery](#push-group-by-into-subquery)
10. [Replace NOT IN with NOT EXISTS](#replace-not-in-with-not-exists)
11. [Flatten Nested UNION ALL](#flatten-nested-union-all)

---

## OR to IN

If a query contains multiple OR clauses comparing the same column to different constant values, rewrite them into a single IN clause. This enables more efficient index lookups and reduces redundant OR evaluations.

**When to apply:** All OR comparisons target the same column using equality (`=`) with constant values.

**Do not apply:** OR clauses compare different columns or involve non-constant expressions.

```sql
-- Original
SELECT *
FROM R
WHERE R.key = c1 OR R.key = c2;

-- Rewritten
SELECT *
FROM R
WHERE R.key IN (c1, c2);
```

```sql
-- Additional example
SELECT name, age
FROM employees
WHERE department_id = 1 OR department_id = 2 OR department_id = 3;

-- Rewritten
SELECT name, age
FROM employees
WHERE department_id IN (1, 2, 3);
```

```sql
-- Not applicable: different columns involved
SELECT name, age
FROM employees
WHERE department_id = 1 OR location_id = 2;
```

---

## LEFT JOIN with Null-Rejecting Predicate to INNER JOIN

If a query uses LEFT JOIN but the WHERE clause rejects NULLs on the joined table, rewrite as INNER JOIN. This enables a simpler, more efficient join plan.

**When to apply:** The WHERE clause rejects NULLs from the right-hand side of a LEFT JOIN (e.g., `IS NOT NULL`, equality comparisons, or any predicate that cannot be true for NULL).

**Do not apply:** NULLs from the right-hand side are required in the result.

```sql
-- Original
SELECT *
FROM R1
LEFT JOIN R2
  ON R1.key = R2.key
WHERE R2.key IS NOT NULL;

-- Rewritten
SELECT *
FROM R1
JOIN R2
  ON R1.key = R2.key;
```

```sql
-- Not applicable: NULLs from R2 are required
SELECT *
FROM R1
LEFT JOIN R2
  ON R1.key = R2.key;
```

---

## Propagate Filter to JOIN Columns

If a query has an equality join condition and a filter predicate on one join attribute, propagate the filter to the corresponding attribute on the other table(s). This enables earlier filtering and reduces intermediate result sizes.

**When to apply:** The filter predicate is on a column involved in an equality join condition.

**Do not apply:** The predicate is on a non-join column.

```sql
-- Original
SELECT *
FROM R1, R2
WHERE R1.id = R2.id
  AND R1.id > 10;

-- Rewritten
SELECT *
FROM R1, R2
WHERE R1.id = R2.id
  AND R1.id > 10
  AND R2.id > 10;
```

```sql
-- Transitive propagation across multiple tables
SELECT *
FROM R1, R2, R3
WHERE R1.id = R2.id
  AND R2.id = R3.id
  AND R1.id > 10;

-- Rewritten
SELECT *
FROM R1, R2, R3
WHERE R1.id = R2.id
  AND R2.id = R3.id
  AND R1.id > 10
  AND R2.id > 10
  AND R3.id > 10;
```

```sql
-- Not applicable: predicate is on a non-join column
SELECT *
FROM R1, R2
WHERE R1.id = R2.id
  AND R1.other_column > 10;
```

---

## Subquery Unnesting — Uncorrelated

If a query contains an uncorrelated `IN (SELECT ...)` subquery, rewrite it as an explicit JOIN. This enables better join order optimizations and index usage.

**When to apply:** The subquery does not reference columns from the outer query.

**Do not apply:** The subquery is correlated (references outer query columns).

```sql
-- Original
SELECT *
FROM R
WHERE R.a IN (
  SELECT S.b
  FROM S
);

-- Rewritten
SELECT DISTINCT R.*
FROM R
JOIN S
  ON R.a = S.b;
```

```sql
-- Additional example
SELECT order_id
FROM orders
WHERE customer_id IN (
  SELECT customer_id
  FROM customers
  WHERE country = 'US'
);

-- Rewritten
SELECT DISTINCT orders.order_id
FROM orders
JOIN customers
  ON orders.customer_id = customers.customer_id
WHERE customers.country = 'US';
```

```sql
-- Not applicable: subquery is correlated
SELECT *
FROM R
WHERE R.a IN (
  SELECT S.b
  FROM S
  WHERE S.c = R.d
);
```

---

## Subquery Unnesting — Correlated

If a query contains a correlated EXISTS subquery, rewrite it as an explicit JOIN. This exposes the subquery to better join optimizations, especially when indexes exist on the join columns.

**When to apply:** The correlated subquery is inside an EXISTS clause and the correlation is expressible as a JOIN condition (typically equality).

**Do not apply:** The correlation cannot be expressed as a simple JOIN condition.

```sql
-- Original
SELECT *
FROM R
WHERE EXISTS (
  SELECT 1
  FROM S
  WHERE S.x = R.x
    AND S.y > 0
);

-- Rewritten
SELECT DISTINCT R.*
FROM R
JOIN S
  ON S.x = R.x
 AND S.y > 0;
```

```sql
-- Additional example
SELECT product_id
FROM products
WHERE EXISTS (
  SELECT 1
  FROM product_reviews
  WHERE product_reviews.product_id = products.product_id
    AND product_reviews.rating >= 4
);

-- Rewritten
SELECT DISTINCT products.product_id
FROM products
JOIN product_reviews
  ON product_reviews.product_id = products.product_id
 AND product_reviews.rating >= 4;
```

```sql
-- Not applicable: correlation cannot be expressed as a JOIN condition
SELECT *
FROM R
WHERE EXISTS (
  SELECT 1
  FROM S
  WHERE S.x + S.y = R.z
);
```

---

## Subquery Unnesting — Scalar

If a query contains a scalar subquery in the SELECT clause computing an aggregate correlated by equality, rewrite it as a LEFT JOIN with GROUP BY. This reduces repeated subquery executions and enables better join planning.

**When to apply:** The scalar subquery is correlated via equality and contains an aggregate function (MAX, MIN, COUNT, SUM).

**Do not apply:** The scalar subquery is uncorrelated.

```sql
-- Original
SELECT
  R.*,
  (SELECT MAX(S.y)
   FROM S
   WHERE S.x = R.x) AS max_y
FROM R;

-- Rewritten
SELECT
  R.*,
  Agg.max_y
FROM R
LEFT JOIN (
  SELECT x, MAX(y) AS max_y
  FROM S
  GROUP BY x
) AS Agg
  ON Agg.x = R.x;
```

```sql
-- Additional example
SELECT
  R.id,
  R.name,
  (SELECT COUNT(*)
   FROM S
   WHERE S.owner_id = R.id) AS s_count
FROM R;

-- Rewritten
SELECT
  R.id,
  R.name,
  Agg.s_count
FROM R
LEFT JOIN (
  SELECT owner_id, COUNT(*) AS s_count
  FROM S
  GROUP BY owner_id
) AS Agg
  ON Agg.owner_id = R.id;
```

```sql
-- Not applicable: scalar subquery is not correlated
SELECT
  R.*,
  (SELECT MAX(S.y) FROM S) AS global_max_y
FROM R;
```

---

## Push Computation to Constant Side

When a filter predicate applies invertible arithmetic to an indexed column, move the computation to the constant side so the column appears alone and indexes can be used.

**When to apply:** All operations on the column are mathematically invertible (addition, subtraction, multiplication/division by non-zero constant).

**Do not apply:** The computation involves non-invertible functions (substring, lower/upper, trigonometric functions) or moving the computation changes query semantics (precision loss, integer-division rounding).

```sql
-- Original
SELECT * FROM titles
WHERE emp_no * 100 / 5 = 10001;

-- Rewritten
SELECT * FROM titles
WHERE emp_no = 10001 * 5 / 100;
```

```sql
-- Additional example
SELECT * FROM orders
WHERE order_id + 5 > 100;

-- Rewritten
SELECT * FROM orders
WHERE order_id > 100 - 5;
```

```sql
-- Not applicable: non-invertible function
SELECT * FROM users
WHERE substring(username, 1, 3) = 'abc';
```

---

## Replace IN-Subquery with EXISTS

When a column is compared to a subquery using IN and the subquery may return many rows, rewrite as a correlated EXISTS to leverage short-circuit evaluation.

**When to apply:** The IN subquery returns a large or variable number of rows.

**Do not apply:** The IN list is a small static set of constants.

```sql
-- Original
SELECT *
FROM customers
WHERE customer_id IN (
  SELECT customer_id
  FROM orders
  WHERE order_date >= DATEADD(day, -30, GETDATE())
);

-- Rewritten
SELECT *
FROM customers c
WHERE EXISTS (
  SELECT 1
  FROM orders o
  WHERE o.customer_id = c.customer_id
    AND o.order_date >= DATEADD(day, -30, GETDATE())
);
```

```sql
-- Additional example
SELECT product_id
FROM products
WHERE product_id IN (
  SELECT product_id
  FROM inventory
  WHERE quantity > 0
);

-- Rewritten
SELECT product_id
FROM products p
WHERE EXISTS (
  SELECT 1
  FROM inventory i
  WHERE i.product_id = p.product_id
    AND i.quantity > 0
);
```

```sql
-- Not applicable: small static set of constants
SELECT *
FROM users
WHERE user_type IN ('admin', 'editor', 'viewer');
```

---

## Push GROUP BY into Subquery

When a query aggregates after joining a fact table to a dimension table, push the GROUP BY into a subquery on the fact table alone. This aggregates fewer rows and joins the smaller result to retrieve dimension columns.

**When to apply:** The aggregation is on the fact table and additional columns come from a dimension table joined on the grouping key.

**Do not apply:** No additional columns are needed beyond the grouping key.

```sql
-- Original
SELECT c.customer_id,
       c.first_name,
       c.last_name,
       COUNT(*) AS order_count
FROM customers c
JOIN orders o
  ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name;

-- Rewritten
SELECT c.customer_id,
       c.first_name,
       c.last_name,
       agg.order_count
FROM customers c
JOIN (
  SELECT customer_id,
         COUNT(*) AS order_count
  FROM orders
  GROUP BY customer_id
) AS agg
  ON c.customer_id = agg.customer_id;
```

```sql
-- Additional example
SELECT cat.category_name,
       cat.description,
       SUM(t.amount) AS total_amount
FROM categories cat
JOIN transactions t
  ON cat.id = t.category_id
GROUP BY cat.category_name, cat.description;

-- Rewritten
SELECT cat.category_name,
       cat.description,
       agg.total_amount
FROM categories cat
JOIN (
  SELECT category_id,
         SUM(amount) AS total_amount
  FROM transactions
  GROUP BY category_id
) AS agg
  ON cat.id = agg.category_id;
```

```sql
-- Not applicable: no additional columns needed
SELECT department_id,
       SUM(salary) AS total_salary
FROM employees
GROUP BY department_id;
```

---

## Replace NOT IN with NOT EXISTS

When a column is filtered with `NOT IN (subquery)`, rewrite as a correlated NOT EXISTS. This avoids building a large intermediate set and sidesteps NULL semantics issues with NOT IN.

**When to apply:** The NOT IN subquery returns many rows or may contain NULLs.

**Do not apply:** The exclusion list is a small static set of constants.

```sql
-- Original
SELECT *
FROM customers
WHERE customer_id NOT IN (
  SELECT customer_id
  FROM blacklisted_customers
);

-- Rewritten
SELECT *
FROM customers c
WHERE NOT EXISTS (
  SELECT 1
  FROM blacklisted_customers b
  WHERE b.customer_id = c.customer_id
);
```

```sql
-- Additional example
SELECT product_id
FROM products
WHERE product_id NOT IN (
  SELECT product_id
  FROM discontinued_products
  WHERE discontinued = true
);

-- Rewritten
SELECT p.product_id
FROM products p
WHERE NOT EXISTS (
  SELECT 1
  FROM discontinued_products d
  WHERE d.product_id = p.product_id
    AND d.discontinued = true
);
```

```sql
-- Not applicable: small static exclusion set
SELECT *
FROM items
WHERE item_type NOT IN ('typeA', 'typeB');
```

---

## Flatten Nested UNION ALL

When a query contains UNION ALL nested inside another UNION ALL, flatten all branches into a single UNION ALL to simplify the plan and reduce intermediate merge steps.

**When to apply:** All set operations are UNION ALL (no deduplication).

**Do not apply:** Any branch uses UNION (deduplicating), which must remain distinct.

```sql
-- Original
SELECT * FROM sales_q1
UNION ALL (
  SELECT * FROM sales_q2
  UNION ALL
  SELECT * FROM sales_q3
);

-- Rewritten
SELECT * FROM sales_q1
UNION ALL
SELECT * FROM sales_q2
UNION ALL
SELECT * FROM sales_q3;
```

```sql
-- CTE example
-- Original
WITH a AS (
  SELECT * FROM t1
  UNION ALL
  SELECT * FROM t2
)
SELECT * FROM a
UNION ALL
SELECT * FROM t3;

-- Rewritten
SELECT * FROM t1
UNION ALL
SELECT * FROM t2
UNION ALL
SELECT * FROM t3;
```

```sql
-- Not applicable: UNION (deduplicating) must stay distinct
SELECT * FROM t1
UNION
SELECT * FROM t2;
```
