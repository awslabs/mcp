# Redshift Metadata Discovery & System Views

## Prefer SHOW commands

Prefer `SHOW` over broad system-view scans for schema discovery.

```sql
SHOW DATABASES;
SHOW SCHEMAS FROM DATABASE <db, identifier, no quotes>;
SHOW TABLES FROM SCHEMA <db, identifier, no quotes>.<schema, identifier, no quotes>;
SHOW COLUMNS FROM TABLE <db>.<schema>.<table, identifier, no quotes>;
SHOW TABLE <schema>.<table>;   -- full CREATE TABLE DDL
SHOW VIEW <schema>.<view, identifier, no quotes>;   -- view definition
```

- 10,000-row limit on the list commands (SHOW DATABASES / SCHEMAS / TABLES / COLUMNS) —
  filter with `SHOW TABLES FROM SCHEMA ... LIKE '%<pat, string, no quotes>%'` or `LIMIT`.
  `SHOW TABLE` / `SHOW VIEW` return a single definition and have no such limit.
- Fall back to `SVV_*` for what SHOW can't give: row counts/size/skew/stats staleness
  (`SVV_TABLE_INFO` — `stats_off`), OID lookups (`pg_class`).

## Use `SYS_` views — `STL_`/`STV_` are provisioned single-AZ only

`SYS_*` views work everywhere — Serverless, provisioned single-AZ, and provisioned
Multi-AZ. Always recommend them.

| View family | Provisioned single-AZ | Provisioned Multi-AZ | Serverless |
|---|---|---|---|
| `SYS_*` | ✅ | ✅ | ✅ |
| `SVV_*` | ✅ all | ✅ all | ⚠️ subset only |
| `STL_*` / `STV_*` / `SVL_*` / `SVCS_*` | ✅ | ❌ | ❌ |

- **The legacy families are single-AZ only.** `STL_*`/`STV_*`/`SVL_*`/`SVCS_*` are
  disabled on Multi-AZ as well as absent on Serverless, so any monitoring query built
  on them breaks on a single-AZ → Multi-AZ move, not just on a Serverless migration.
- On Multi-AZ, use `compute_type` in `SYS_QUERY_HISTORY` (`primary` / `secondary`) to
  see which AZ ran a query.
- **A subset of the `SVV_*` views on Serverless are queryable**, so some
  provisioned-only views error there — including `SVV_QUERY_STATE`
  (→ `SYS_QUERY_DETAIL`), `SVV_VACUUM_PROGRESS` and `SVV_VACUUM_SUMMARY`
  (→ `SYS_VACUUM_HISTORY`), `SVV_DISKUSAGE` (no equivalent — storage is managed), and
  `SVV_SCHEMA_QUOTA_STATE` (→ `SVV_REDSHIFT_SCHEMA_QUOTA`). Unlike the legacy families
  above, this is **per view, not per family** — most `SVV_*` views do work on
  Serverless, so check the individual view's reference page, which carries the note
  when it is provisioned-only (e.g. `SVV_DISKUSAGE`: "This view is only available when
  querying provisioned clusters"). For the full legacy → `SYS_` mapping, grouped by the
  replacement `SYS_` view, see
  [System view mapping for migrating to SYS monitoring views](https://docs.aws.amazon.com/redshift/latest/dg/sys_view_migration.html).

| Provisioned-only (use SYS_ instead) | Use instead |
|---|---|
| `stl_query` / `svl_qlog` | `sys_query_history` (query-level) |
| step/operator detail (e.g. `svl_query_summary`) | `sys_query_detail` (per-step metrics) |
| `stl_querytext` | `sys_query_text` |
| `stl_load_errors` | `sys_load_error_detail` |
| `stv_inflight` / `stv_recents` | `sys_query_history WHERE status='running'` |
| `stv_sessions` | `sys_session_history` |
| `stl_connection_log` | `sys_connection_log` |

For query analysis, `sys_query_history` gives per-query rows and `sys_query_detail`
gives the per-step (operator-level) breakdown. Use these `SYS_*` views — they are the
documented, customer-facing interface for query monitoring.

Common column-name mistakes on `sys_query_history`: use `query_text` (not `query`),
`start_time` (not `starttime`), `elapsed_time` (not `duration`). On `svv_table_info`
the table column is quoted: `"table"`; row count is `tbl_rows`.

## SVV_ families — pick the right scope

| Family | Scope | Use when |
|---|---|---|
| `SVV_REDSHIFT_*` | Local + datashare tables | Redshift-native objects only |
| `SVV_EXTERNAL_*` | Any external schema (data catalog, Hive metastore, federated PostgreSQL/MySQL, remote Redshift, streaming, …) — see `eskind` in `SVV_EXTERNAL_SCHEMAS` | Data-lake schemas: partitions, location, file format. Federated/streaming schemas: schema and table/column listing only |
| `SVV_ALL_*` | Union of the two | Everything in one query |
| `SVV_TABLE_INFO` | Local design details | diststyle, sortkey, size, skew, unsorted |

```sql
-- SVV_TABLE_INFO is visible only to superusers. A regular user gets
-- "permission denied for relation svv_table_info" until a superuser runs
-- GRANT SELECT ON svv_table_info TO <user>. SHOW TABLES lists a table only when
-- the current user is a superuser, owns the table, or has USAGE on the parent
-- schema plus SELECT on the table (or on any column of it). SVV_ALL_TABLES is
-- visible to all users, but regular users see only their own data.
SELECT "table", schema, diststyle, sortkey1, tbl_rows, size
FROM svv_table_info WHERE schema = '<schema, string, single quotes>';

-- Datashare discovery
SELECT share_name, share_type, source_database FROM svv_datashares;
SELECT object_type, object_name FROM svv_datashare_objects WHERE share_name = '<share, string, single quotes>';
```

## Datashare writes (consumer side)

Datashares support read and write operations — consumers can INSERT / UPDATE /
DELETE / MERGE / COPY / TRUNCATE / CTAS into shared tables once the producer grants
write privileges. So **treat "permission denied" on a datashare write as a missing
grant** — the fix is for the producer to grant the privilege, not to tell the user
writes are unsupported.

- Reference shared objects with 3-part notation (`database.schema.table`) or
  connect to the shared database — other notations are not supported for writes.
- Requirements: producer database uses snapshot isolation. Full list in the
  [datashare read/write considerations](https://docs.aws.amazon.com/redshift/latest/dg/considerations-datashare-reads-writes.html).
- `error: Your consumer size is not supported for multi-warehouse write queries. For
  more details, please refer to Amazon multi-warehouse write documentation.` — this is a
  producer/consumer **sizing** mismatch, not an unsupported node type. Send the user to
  the documentation above for sizing guidance; do not guess at a slice count or a
  supported node-type list.
- Not writable: views/MVs on datashare databases, interleaved-sort-key tables;
  multi-statement writes must be wrapped in explicit BEGIN...END. `COPY` is
  supported only **without** `COMPUPDATE`.

## Permission troubleshooting

```sql
-- Check what privileges current user has on a table
SELECT HAS_TABLE_PRIVILEGE('<user, string, single quotes>', '<schema.table, string, single quotes>', 'SELECT');

-- Table grants EXPLICITLY granted to a user/role/group in the CURRENT database
-- (grants inherited via nested roles or group membership are not listed here)
SELECT * FROM svv_relation_privileges
WHERE identity_name = '<user_or_role, string, single quotes>';

-- Roles granted directly to a user (explicit grants only — roles nested inside
-- those roles are not listed here; use svv_role_grants for role-to-role grants)
SELECT * FROM svv_user_grants WHERE user_name = '<user, string, single quotes>';

-- Grant SELECT on all tables in a schema (a bare name is a username; to target
-- a role or group the keyword is required: TO ROLE role_name / TO GROUP group_name)
GRANT SELECT ON ALL TABLES IN SCHEMA <schema, identifier, no quotes> TO <user, identifier, no quotes>;

-- Grant usage on schema (required before table grants take effect)
GRANT USAGE ON SCHEMA <schema, identifier, no quotes> TO <user, identifier, no quotes>;
```

- "permission denied for relation" → check `svv_relation_privileges` + `GRANT USAGE` on schema + `GRANT SELECT` on tables.
- `SVV_DEFAULT_PRIVILEGES` shows what new objects will inherit.

### `permission denied for database awsdatacatalog`

Queries against the auto-mounted AWS Glue Data Catalog fail with `ERROR: permission denied for
database awsdatacatalog`. Root cause: the connecting role/user lacks **database-level `USAGE`**
on **`awsdatacatalog`** (the Redshift database that exposes the Glue Data Catalog) — the same
database-level `USAGE` grant that datashare-created databases require on the consumer side. Fix:

```sql
GRANT USAGE ON DATABASE awsdatacatalog TO ROLE "<database_role, identifier, double-quoted>";
-- e.g. GRANT USAGE ON DATABASE awsdatacatalog TO ROLE "AWSIDC:hr";
```

where the role is the one mapped to the connecting identity — e.g. an IAM Identity Center role
(`awsidc:<permission-set-or-group>`) or an IAM-mapped identity (`IAMR:<role-name>` /
`IAM:<user-name>`). Double-quote the identity — these names contain a colon (e.g. `"IAMR:Admin"`),
so they must be quoted. Grant to the user instead (`GRANT USAGE ON DATABASE awsdatacatalog TO
"<database_user, identifier, double-quoted>";`) if roles aren't in use. Verify with
`svv_database_privileges`.

## "Relation does not exist" — diagnostic flow

1. **Confirm the object exists and find its schema** — the error often means "not found *where I looked*", not "gone":

   ```sql
   SHOW TABLES FROM SCHEMA <db, identifier, no quotes>.<schema, identifier, no quotes> LIKE '%<name, string, no quotes>%';
   SELECT schema_name, table_name FROM svv_all_tables WHERE table_name = '<table, string, single quotes>';
   ```

   A `LIKE` condition returns candidates, not an exact match — `_` is a metacharacter,
   so `'%user_data%'` also matches `userXdata`. Confirm identity with the `=` query above.
2. **Check the search path** — `SHOW search_path;`. search_path does not work at all
   for external schemas/tables or datashare schemas (datashares behave as external
   data) — these must always be explicitly qualified, not added to search_path.
3. **Fully qualify** — `schema.table` (or `database.schema.table` cross-database). Do not rely on search_path resolution.
4. `STL_*`/`STV_*`/`SVL_*`/`SVCS_*` don't exist on Serverless and are disabled on provisioned Multi-AZ; use the `SYS_*` equivalent. Some `SVV_*` are also unavailable on Serverless.

## Object notation: 2-part vs 3-part

- 2-part `schema.table` — current database.
- 3-part `database.schema.table` — cross-database / datashare.
- External schemas alias a remote db+schema to a local 2-part name (required for
  Spectrum — all external tables must be created in an external schema; optional
  for datashares, where they enable granular per-schema permissions).
- Don't rely on `search_path` — qualify explicitly. Debug "relation does not exist"
  with `SHOW search_path;`. External and datashare schemas can't be put in
  `search_path` at all — qualification is the only option for them.
