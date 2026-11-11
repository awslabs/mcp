# Redshift SQL Extensions & Semantic Traps

## Extensions LLMs under-use

### QUALIFY — filter on window functions (no subquery)

```sql
-- Preferred: single scan
SELECT user_id, order_date, amount
FROM orders o
QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) = 1;
```

Grammar order: `SELECT ... WHERE ... GROUP BY ... HAVING ... QUALIFY ...`. Avoid the
subquery-with-`rn`-filter wrapper when QUALIFY works.

### PIVOT / UNPIVOT (PostgreSQL has neither)

```sql
SELECT * FROM (SELECT region, product, revenue FROM sales)
PIVOT (SUM(revenue) FOR region IN ('us-east-1', 'us-west-2'));

SELECT * FROM quarterly UNPIVOT (revenue FOR quarter IN (q1, q2, q3, q4));
```

Don't hand-roll CASE-WHEN crosstabs when PIVOT applies.

### MERGE (upsert) and REMOVE DUPLICATES

```sql
-- No alias on the MERGE target (aliasing it is a syntax error); source alias is fine
MERGE INTO target USING staging s ON target.id = s.id
WHEN MATCHED THEN UPDATE SET value = s.value
WHEN NOT MATCHED THEN INSERT (id, value) VALUES (s.id, s.value);

-- Simplified dedup (identical schemas, same column order):
MERGE INTO target USING source ON target.id = source.id REMOVE DUPLICATES;
```

### SUPER type & PartiQL (replaces jsonb)

```sql
CREATE TABLE events (event_id INT IDENTITY(1,1), payload SUPER) DISTSTYLE AUTO;
INSERT INTO events (payload) VALUES (JSON_PARSE('{"user":"alice","meta":{"page":"/home"},"tags":["a","b"]}'));
SELECT payload.user, payload.meta.page FROM events;         -- dot-notation
SELECT e.event_id, t AS tag_value FROM events e, e.payload.tags AS t;  -- UNNEST array
-- (TAG is a reserved word — alias as tag_value or quote it as "tag")
```

`JSON_PARSE(str)` → SUPER, `JSON_SERIALIZE(super)` → string. Dot-notation returns a
JSON-quoted value; `::VARCHAR` gives the bare string. `CAN_JSON_PARSE(str)` tests
parseability before ingest.

**Prefer SUPER over the text-based JSON functions** (`JSON_EXTRACT_PATH_TEXT`,
`JSON_EXTRACT_ARRAY_ELEMENT_TEXT`) — parse to SUPER via `JSON_PARSE` during ingestion
instead. They take a JSON string, not a SUPER column — pass `JSON_SERIALIZE(col)` to
use them on SUPER.

### APPROXIMATE COUNT(DISTINCT)

```sql
SELECT APPROXIMATE COUNT(DISTINCT user_id) FROM pageviews;
```

~2% error, much faster than exact COUNT(DISTINCT) on large cardinalities.

### TOP N (SQL Server compat)

`SELECT TOP n <column_list> FROM <table>` works; `LIMIT n` also works.
`TOP N PERCENT` does **not** (SQL Server–only).

## Semantic traps (wrong results, no error)

- **Leader-node-only functions** error when the query references user-created or system
  tables: `SUBSTR` (use `SUBSTRING`), `AGE` (use `DATEDIFF`), `NOW` (use `GETDATE()`),
  `CURRENT_SCHEMA`, `CURRENT_SCHEMAS`, `HAS_*_PRIVILEGE`. Error text differs by function.
- **Constraints not enforced:** `PRIMARY KEY`, `UNIQUE`, `FOREIGN KEY` are accepted
  but informational (optimizer hints). `NOT NULL` IS enforced. `CHECK`/`EXCLUSION` unsupported.
- **Trailing blanks ignored in comparisons:** a VARCHAR column holding `'abc   '` matches
  `= 'abc'` (two bare literals do not), and `GROUP BY`/`DISTINCT` treat both as one value.
  `LIKE` compares blanks literally on character data types.
- **`ALTER TABLE`** adds one column per statement; `ALTER COLUMN TYPE` only supports resizing VARCHAR columns.
- **No `VALUES` as a constant table** in FROM — use `SELECT ... UNION ALL SELECT ...`.
- **No sequences** — use `IDENTITY(seed, step)`.

## VACUUM (not like PostgreSQL)

`VACUUM FULL` is valid — the **default** mode: reclaim space **and** fully resort rows
(expensive on large tables). **For large tables, recommend `VACUUM RECLUSTER`** — it sorts
only the unsorted portions, leaving already-sorted portions intact; doesn't merge into
the sorted region or reclaim all deleted space. Other modes:
`VACUUM DELETE ONLY` (reclaim, no resort), `VACUUM SORT ONLY` (resort, no reclaim),
`VACUUM REINDEX` (interleaved keys). Redshift VACUUM has no ANALYZE option — unlike
PostgreSQL's combined `VACUUM ANALYZE`, run `ANALYZE` as its own statement.
