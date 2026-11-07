# Redshift Functions & Data Types

## Function mapping

| PostgreSQL (wrong on Redshift) | Redshift (correct) |
|---|---|
| `string_agg(col, ',')` | `LISTAGG(col, ',') WITHIN GROUP (ORDER BY col)` |
| `array_agg()` / `json_agg()` | Not supported — use SUPER type |
| `NOW()` | `GETDATE()` / `SYSDATE` |
| `regexp_matches()` | `REGEXP_SUBSTR()`, `REGEXP_COUNT()`, `REGEXP_INSTR()` |
| `FILTER (WHERE ...)` | `CASE WHEN ... END` inside the aggregate |
| `DISTINCT ON (col)` | `ROW_NUMBER() OVER (PARTITION BY col ORDER BY ...) = 1` |
| `LATERAL` join | Correlated subquery |
| `RETURNING` | Separate `SELECT` after the DML |
| `ON CONFLICT` | `MERGE INTO ... USING ... WHEN MATCHED / NOT MATCHED` |
| `SUBSTR(str, pos)` on a table | `SUBSTRING()` — `SUBSTR` is leader-node only |
| `generate_series()` for a date/number series joined to data | Recursive CTE — `generate_series` is unsupported (may appear to work only in queries referencing no tables); it errors the moment it's joined to table data |

Supported as-is (Oracle/T-SQL compat): `NVL(a,b)`, `NVL2()`, `DECODE()`,
`COALESCE()`, `ILIKE`, `WITH RECURSIVE`, window functions.

## Date/number series (gap-filling) — use a recursive CTE, not generate_series

`generate_series()` is unsupported (may appear to work only in queries referencing
no tables), so it fails when its output is joined against table data (the usual
gap-fill case). Use `WITH RECURSIVE`:

```sql
WITH RECURSIVE dates(d) AS (
  SELECT CAST('2024-01-01' AS DATE)
  UNION ALL
  SELECT CAST(DATEADD(day, 1, d) AS DATE) FROM dates WHERE d < CAST('2024-12-31' AS DATE)
)
SELECT d FROM dates;              -- then LEFT JOIN your table on d to fill gaps
```

The recursive term must **cast back to DATE** — `DATEADD` returns TIMESTAMP, and
Redshift requires the recursive column's type to match the anchor's exactly
(otherwise: "Datatype mismatch in recursive CTE").

## Data type mapping

| PostgreSQL (wrong) | Redshift (correct) | Why |
|---|---|---|
| `text` | `VARCHAR(max)` or `VARCHAR(N)` | A `text` column is converted to `VARCHAR(256)`. The DDL is accepted without error, but inserting more than 256 characters **fails** with `value too long for type character varying(256)` — it does not truncate. Specify the length you need |
| `SERIAL` / `BIGSERIAL` | `INT IDENTITY(1,1)` / `BIGINT IDENTITY(1,1)` | Auto-increment |
| `jsonb` / `json` | `SUPER` | Semi-structured, dot-notation access |
| `int[]` / `boolean[]` | Not supported | Use SUPER |
| `bytea` | `VARBYTE` (a.k.a. `VARBINARY`) | Binary |
| `uuid` | `CHAR(36)` | No native UUID type |

Synonyms — both spellings are valid on Redshift, no rewrite needed:

| Either form works | Canonical Redshift name | Note |
|---|---|---|
| `NUMERIC(p,s)` | `DECIMAL(p,s)` | Same type; max precision 38 |

## Date/time functions

Unit-first argument order:

```sql
SELECT DATEADD(<datepart, identifier, no quotes>, <interval, integer, no quotes>, <ts, timestamp, no quotes>);
SELECT DATEDIFF(<datepart, identifier, no quotes>, <start, timestamp, no quotes>, <end, timestamp, no quotes>);
```

- dateparts: `year, month, week, day, hour, minute, second, millisecond, microsecond`
- `DATEADD(day, -30, GETDATE())` — last 30 days; `DATEADD(month, 3, ship_date)`.
- `DATEDIFF(day, start_ts, end_ts)` returns a BIGINT count of crossed boundaries.
- `DATE_TRUNC('month', ts)`, `EXTRACT(year FROM ts)` / `DATE_PART('year', ts)` — same as PG.
- `GETDATE()`/`SYSDATE` return TIMESTAMP; use `TRUNC(GETDATE())` or `CURRENT_DATE` for DATE.

The left column below is leader-node-only and deprecated — it may still execute, but
use the right-column replacement.

| Instead of | Use |
|---|---|
| `AGE` | `DATEDIFF` |
| `CURRENT_TIME` / `CURRENT_TIMESTAMP` | `GETDATE()` or `SYSDATE` |
| `LOCALTIME` / `LOCALTIMESTAMP` | `GETDATE()` or `SYSDATE` |
| `NOW` | `GETDATE()` or `SYSDATE` |
| `ISFINITE` | (no replacement documented) |

`NOW()` inside a materialized view resolves to the MV's creation timestamp, not the
current time.

## Examples

```sql
-- LISTAGG (not string_agg)
SELECT customer_id, LISTAGG(product, ', ') WITHIN GROUP (ORDER BY order_date) AS products
FROM orders GROUP BY customer_id;

-- Last-N-days filter
SELECT * FROM events WHERE event_ts >= DATEADD(day, -7, GETDATE());
```
