# Redshift Materialized Views

Redshift MVs differ from PostgreSQL in auto-refresh, concurrency, and scope.
Base models don't know `AUTO REFRESH YES` or `SYS_MV_REFRESH_HISTORY` — show them.

## Create with auto-refresh

```sql
CREATE MATERIALIZED VIEW <schema, identifier, no quotes>.daily_revenue_mv
AUTO REFRESH YES
AS
SELECT DATE_TRUNC('day', order_ts) AS order_day,
       region,
       SUM(amount) AS total_revenue,
       COUNT(*) AS order_count
FROM <schema, identifier, no quotes>.orders
GROUP BY 1, 2;
```

## Manual refresh

```sql
REFRESH MATERIALIZED VIEW <schema, identifier, no quotes>.daily_revenue_mv;
```

- Does NOT support `CONCURRENTLY` (PostgreSQL does; Redshift does not).
- Redshift automatically chooses incremental or full refresh based on the MV's defining query.

## Check refresh history

```sql
SELECT schema_name, mv_name, status, start_time
FROM SYS_MV_REFRESH_HISTORY
WHERE schema_name = '<schema, string, single quotes>'
ORDER BY start_time DESC;
```

`status` shows the refresh outcome; `start_time` is when the refresh ran. For
staleness use `SVV_MV_INFO` (`is_stale`). Prefer these two — they work on both
Serverless and provisioned (the `STV_MV_*`/`STL_MV_*`/`SVL_MV_*` monitoring views
are provisioned **single-AZ** only — disabled on Multi-AZ, absent on Serverless).

## Show definition

```sql
SHOW VIEW <schema, identifier, no quotes>.daily_revenue_mv;
```

Works for regular views, MVs, and late-binding views.

## Key differences from PostgreSQL MVs

| PostgreSQL | Redshift |
|---|---|
| No auto-refresh (manual/cron) | `AUTO REFRESH YES` — automatic on base-table change (default is NO) |
| `REFRESH ... CONCURRENTLY` | Not supported |
| `pg_matviews` for state | Not present — use `SYS_MV_REFRESH_HISTORY` (`status`, `start_time`) or `SVV_MV_INFO` (`is_stale`) |
| MV on any query | MV on local, data lake (Spectrum), federated, and datashare tables — but MVs over data lake tables can't use `AUTO REFRESH YES` |
| Can specify indexes on MV | No indexes — distribution defaults to EVEN unless DISTSTYLE/DISTKEY specified |
| `CREATE ... WITH DATA / NO DATA` | Always created with data |

## Common mistakes agents make

- Generating `REFRESH MATERIALIZED VIEW CONCURRENTLY` — errors on Redshift.
- Relying on `pg_matviews` — it does not exist on Redshift (`ERROR: relation
  "pg_matviews" does not exist`); use `SYS_MV_REFRESH_HISTORY` or `SVV_MV_INFO`.
- Adding `ORDER BY` inside the MV definition — not allowed; sort via SORTKEY on the MV.
- Forgetting `AUTO REFRESH YES` — the default is `NO`, so queries keep returning data
  from the last refresh with no error (check `is_stale` in `SVV_MV_INFO`). But
  `AUTO REFRESH YES` is **rejected** when the definition reads
  data lake tables (Spectrum/federated) or uses a mutable function, or when the MV is
  built on another MV — those need an explicit `REFRESH MATERIALIZED VIEW` (manual or
  scheduled).
