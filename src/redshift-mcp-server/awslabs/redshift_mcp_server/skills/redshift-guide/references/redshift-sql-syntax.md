# Redshift SQL Syntax & Query Generation

Index of the 6 SQL-generation references plus the PostgreSQL-vs-Redshift
failure table. The SKILL.md routing table sends most SQL questions **directly**
to the specific leaf reference below; load this file only for a general dialect
question or when you need to pick which SQL reference applies.

## Redshift is NOT PostgreSQL — top failures

| Expect (PostgreSQL) | Reality (Redshift) | Fix |
|---|---|---|
| `string_agg()` | Not supported | `LISTAGG() WITHIN GROUP (ORDER BY ...)` |
| `text` type | A `text` column becomes `VARCHAR(256)`; a longer INSERT **errors** (`value too long for type character varying(256)`) — it does not truncate | `VARCHAR(max)` or explicit `VARCHAR(N)` |
| `CREATE INDEX` | Does not exist | SORTKEY in CREATE TABLE |
| `SERIAL` / `BIGSERIAL` | Not supported | `IDENTITY(1,1)` |
| `LATERAL` join | Not supported | Correlated subquery |
| `SUBSTR()` on a table | Leader-node only — errors on tables | `SUBSTRING()` |
| `stl_*` / `stv_*` views | Provisioned single-AZ only — absent on Serverless, disabled on Multi-AZ | Use `SYS_*` views instead |
| `pg_catalog` for stats | Incomplete | `SVV_TABLE_INFO`, `SYS_*` |
| `ON CONFLICT DO UPDATE` | Not supported | `MERGE INTO ... WHEN MATCHED` |
| `RETURNING` clause | Not supported | Separate `SELECT` after DML |
| `CREATE SEQUENCE` / `nextval()` | Not supported | `IDENTITY(seed, step)` |
| PK / FK / UNIQUE enforced | Informational only — NOT enforced | Application-layer integrity |
| `col = 'abc'` won't match `'abc   '` stored in `col` | Matches — comparison against a column ignores trailing blanks, and `GROUP BY`/`DISTINCT` collapse the two into one value. Two bare literals are NOT equal | For blank-sensitive matching use `LIKE` (it does not ignore them) — but only with a literal pattern, since `%`/`_` stay active. On VARCHAR, `LEN()` counts trailing blanks; on CHAR it does not |
| Multi-column `ADD COLUMN` | One `ADD COLUMN` per `ALTER TABLE` | Separate statements |

## Sub-topic references (load on demand)

- `redshift-sql-functions-types.md` — function map (LISTAGG, DATEADD/DATEDIFF,
  NVL/DECODE/ISNULL), type map (`text`, SUPER, VARBYTE, IDENTITY).
- `redshift-sql-ddl-copy.md` — CREATE TABLE (DISTKEY/SORTKEY/ENCODE), IDENTITY,
  late-binding views, COPY/UNLOAD full syntax, IAM_ROLE.
- `redshift-sql-metadata.md` — SHOW-first discovery, `SYS_` vs `STL_`/`STV_` (provisioned single-AZ only),
  SVV_ALL/SVV_REDSHIFT/SVV_EXTERNAL families, 2-part vs 3-part notation.
- `redshift-sql-extensions-semantics.md` — QUALIFY, PIVOT/UNPIVOT, MERGE, SUPER
  /PartiQL, TOP N + semantic traps (leader-node fns, constraints, VACUUM).
- `redshift-sql-recipes-load-api.md` — Working COPY recipe (with error handling,
  retry, sys_load_error_detail) + Data API poll loop (Python, production-grade).
- `redshift-sql-materialized-views.md` — CREATE MV with AUTO REFRESH, manual
  REFRESH (no CONCURRENTLY), SYS_MV_REFRESH_HISTORY, differences from PostgreSQL MVs.

## Principles

- `SYS_*` views for performance/audit (all deployment types). `SVV_*` for metadata.
  `SHOW` commands preferred for discovery. Do not generate `STL_*`/`STV_*` — use `SYS_*` instead.
- DISTKEY + SORTKEY are the highest-impact table-design choices, but AUTO is the
  default and the recommendation for most tables — omit them and let Redshift choose.
  Specify deliberately when the join/filter pattern is known (e.g. fact table joined
  on a known key, columns commonly range-filtered).
- COPY beats INSERT for bulk loads. COPY/UNLOAD always need authorization (`IAM_ROLE` recommended).
- Constraints (PK/FK/UNIQUE) are optimizer hints, not enforcement. `NOT NULL` IS enforced.
- Prefer `QUALIFY` over subquery wrappers for window-function filtering.
- Always qualify tables (`schema.table`) — don't rely on `search_path`.
- Redshift folds identifiers to lowercase — **quoting does NOT preserve case** (unlike
  PostgreSQL) unless `enable_case_sensitive_identifier` is on. Quote only to use a
  reserved word or an illegal character: `svv_table_info`'s column is `"table"`.
