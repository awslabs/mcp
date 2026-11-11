# Redshift Query Performance — Ready-to-run Diagnostic Queries

Ready-to-run diagnostic queries for `redshift-sql-query-performance.md` (start with the
phase-triage query there). All use portable `SYS_*`/`SVV_*` views (work on both Serverless
and provisioned). All `*_time` / `duration` columns are in **microseconds**; the queries return
them unconverted and unrounded. **Access:** without elevated access these queries fail or under-return. As a non-superuser,
**`SYS_*` views generally show only your own rows** (e.g. `SYS_QUERY_HISTORY`, `SYS_QUERY_DETAIL`),
and **some views are superuser-only** and return *permission denied* (e.g. `SVV_TABLE_INFO`,
`SYS_ANALYZE_HISTORY`, `SYS_AUTO_TABLE_OPTIMIZATION`). Grant the
[`sys:monitor` default role](https://docs.aws.amazon.com/redshift/latest/dg/r_roles-default.html):
it lifts the per-user filter and opens the superuser-only views.
`GRANT SELECT ON <view_name, identifier, no quotes> TO <user_name, identifier, no quotes>` only
fixes *permission denied* for one view; it doesn't lift the own-rows filter. Note the two views answer different questions:
`SVV_TABLE_INFO.stats_off` reports staleness **now**, while `SYS_QUERY_DETAIL` (the per-step
`alert` column, e.g. a missing-statistics alert — no superuser needed) tells you whether a
**specific run** was planned on stale stats when it ran.

**Identify the workload before searching.** A `query_id`, `session_id` or `transaction_id`
identifies it directly; filter on it. A time window, user or database only narrows the search:
combine them with something from the statement itself (a text snippet, a query label, or the
procedure name).

## Stored procedure — find the slow statement(s) (both deployments)

A `CALL` runs many statements, and each inner statement gets its own `query_id` in
`SYS_QUERY_HISTORY`. The `CALL` itself is logged as its own row whose `start_time`/`end_time`
span the whole procedure. Anchor on that CALL row, then rank the statements that ran **in
the same `session_id` inside the CALL's time window** — often *several* statements are slow,
so work down the ranked list (not just the top one) and drill into each with the execution
query below.

**Do not filter by `transaction_id` alone** — it is wrong in both directions:

- If the `CALL` sits inside an explicit `BEGIN…COMMIT`, the proc's statements share **one**
  xid with the surrounding non-proc statements, so an xid filter **over-captures** the siblings.
- A `NONATOMIC` proc that issues an internal `COMMIT`/`TRUNCATE` (or DDL) starts a **new** xid
  per statement, so the proc's statements span **several** xids and an xid filter
  **under-captures** everything after the first commit.

Scoping by `session_id` + the CALL's `[start_time, end_time)` window handles both: a session
runs statements serially, so nothing else executes in that window, and it captures the proc's
statements no matter how many transactions they span.

```sql
-- Step 1 — find the proc CALL and grab its session_id + start/end time window.
-- The CALL is logged as its own row with the invocation in its query text ('call <proc>...'),
-- so match on the query text.
-- Use the CALL row only for its session_id and time window. Don't decompose its time buckets;
-- decompose the inner statements (Step 2) instead.
SELECT query_id AS call_query_id, session_id, transaction_id, query_type, status,
       elapsed_time, start_time, end_time,
       query_text AS call_text
FROM sys_query_history
WHERE query_text ILIKE 'call %<proc_name, identifier, no quotes>%'
  AND query_text NOT ILIKE '%sys_query_history%'   -- don't match this lookup itself
ORDER BY elapsed_time DESC                         -- slowest CALLs first, wherever they fall in history
LIMIT 10;
```

```sql
-- Step 2 — rank every statement the proc ran, slowest-first, with each one's share of the
-- proc's total time (pct_of_proc). Scope by session_id + the CALL's [start_time, end_time)
-- window: this excludes sibling statements in the same explicit transaction AND still captures
-- inner statements when an internal COMMIT split them across xids. Drill into each slow
-- query_id with the "Execution drill-down" query below.
SELECT query_id, transaction_id, query_type, status,
       elapsed_time,
       100.0 * elapsed_time / NULLIF(SUM(elapsed_time) OVER (), 0) AS pct_of_proc,
       start_time, query_text
FROM sys_query_history
WHERE session_id = <session_id_from_step_1, integer, no quotes>
  AND start_time >= <call_start_time_from_step_1, timestamp, single quotes>   -- inclusive lower bound
  AND start_time <  <call_end_time_from_step_1, timestamp, single quotes>     -- exclusive: drops post-CALL siblings
  AND query_id <> <call_query_id_from_step_1, integer, no quotes>   -- exclude the CALL row itself
ORDER BY elapsed_time DESC
LIMIT 50;
```

## Execution drill-down — skew, spill, alerts (both deployments)

```sql
-- Once execution_time dominates, find the expensive segment, then the step inside it.
-- 1) Rank segments. duration, reads and spill are recorded per SEGMENT (step rows carry 0 for reads
--    and spill, and a copy of the segment's duration).
SELECT child_query_sequence, stream_id, segment_id, duration, time_skewness,
       blocks_read, spilled_block_local_disk, spilled_block_remote_disk
FROM sys_query_detail
WHERE user_id > 1 AND query_id = <query_id, integer, no quotes>
  AND metrics_level = 'segment'
ORDER BY duration DESC;

-- 2) Steps of the slowest segment(s): rows, row skew and alerts identify the expensive step.
--    Take child_query_sequence and segment_id from the top rows of query 1 — segment ids restart
--    in each child query, so filter on both (run once per child query if the top rows span several).
SELECT child_query_sequence, segment_id, step_id, step_name, table_name,
       input_rows, output_rows,
       data_skewness,                                -- high => the step's rows were spread very unevenly
       alert                                         -- missing stats / nested loop / large broadcast
FROM sys_query_detail
WHERE user_id > 1 AND query_id = <query_id, integer, no quotes>
  AND metrics_level = 'step'
  AND child_query_sequence = <child_query_sequence, integer, no quotes>
  AND segment_id IN (<segment_ids, integer list, comma-separated>)
ORDER BY segment_id, output_rows DESC;
```

## Plan shape + auto-optimization recommendations (both deployments)

```sql
-- System-generated EXPLAIN plan: look for DS_BCAST_INNER / DS_DIST_INNER / DS_DIST_BOTH and
-- nested-loop nodes. DS_DIST_BOTH (both sides redistributed) is the most data movement.
-- Data redistribution: https://docs.aws.amazon.com/redshift/latest/dg/c_data_redistribution.html
-- Then compare the planner's estimated rows here against actual input_rows/output_rows in the
-- execution drill-down above — a large gap points at stale/missing stats driving a bad plan.
SELECT query_id, child_query_sequence, plan_node_id, plan_parent_id, plan_node, plan_info
FROM sys_query_explain WHERE query_id = <query_id, integer, no quotes>
ORDER BY child_query_sequence, plan_node_id;

-- Pending Automatic Table Optimization dist/sort recommendations — defer to these before hand-rolling DDL.
SELECT type, "database", table_id, group_id, ddl, auto_eligible
FROM svv_alter_table_recommendations ORDER BY table_id;
```

### Plan diff — what changed between the fast and slow run (both deployments)

```sql
-- Step 1: pair one fast + one slow run of the SAME query. Two ways to group runs of the same
-- statement — use whichever is handy:
--   (a) the built-in generic_query_hash (same text ignoring literal VALUES) or user_query_hash
--       (same text including literals) in sys_query_history — simplest, no length limit; or
--   (b) the NORMALIZED SQL text fingerprint below — purely lexical, masks literal VALUES only, not
--       identifiers (a digit glued to a name like sales_2026 or col::int8 is kept). (Redshift
--       REGEXP_REPLACE uses POSIX word boundaries [[:<:]]/[[:>:]].)
WITH candidates AS (                                    -- runs of this statement only
    SELECT query_id, elapsed_time, start_time
    FROM sys_query_history
    WHERE user_id > 1
      AND start_time >= DATEADD(day, -7, GETDATE())     -- SYS_* history retention
      AND query_text ILIKE '%<tag_or_snippet, string, no quotes>%'
      AND result_cache_hit = false                      -- a cache hit isn't a real baseline
)
SELECT c.query_id, c.elapsed_time, c.start_time,
       MD5(LOWER(regexp_replace(regexp_replace(regexp_replace(
             LISTAGG(TRIM(t.text)) WITHIN GROUP (ORDER BY t.sequence),
             '''[^'']*''', '?'),                         -- string literals -> ?
           '[[:<:]][0-9]+([.][0-9]+)?[[:>:]]', '?'),     -- numeric literal VALUES -> ? (identifiers kept)
         '[[:space:]]+', ' '))) AS query_text_hash       -- collapse whitespace
FROM candidates c JOIN sys_query_text t USING (query_id)
WHERE t.sequence <= 15   -- LISTAGG caps at 65,535 chars; ~15 sys_query_text chunks fit under that.
                         -- Longer statements truncate here (small collision risk) — for very long
                         -- SQL, group on generic_query_hash (option a) instead, which has no limit.
GROUP BY c.query_id, c.elapsed_time, c.start_time
ORDER BY query_text_hash, c.elapsed_time;   -- within one query_text_hash: first row = fast, last = slow
```

```sql
-- Step 2: normalized PLAN HASH per child_query_sequence — decide WHETHER the plan shape changed
-- before diffing nodes. Strips volatile cost/rows/width and normalizes literals, and excludes the
-- "-----" missing-stats banner rows. Equal hash (fast vs slow) => shape unchanged (go to the
-- data/stats check below); different for a child => the plan flipped there, run Step 3.
SELECT query_id, child_query_sequence,
       MD5(LISTAGG(
             regexp_replace(
               regexp_replace(
                 regexp_replace(plan_node || '|' || COALESCE(plan_info,''),
                   'volt_[a-z0-9_]+', 'volt_tt'),                           -- normalize temp-table names
                 'cost=[0-9.]+\.\.[0-9.]+|rows=[0-9]+|width=[0-9]+', ''),  -- drop volatile estimates
               '''[^'']*''|[[:<:]][0-9]+([.][0-9]+)?[[:>:]]', '?')       -- normalize literal VALUES (names kept)
           , '~') WITHIN GROUP (ORDER BY plan_node_id, plan_node)) AS plan_hash
FROM sys_query_explain
WHERE query_id IN (<fast_query_id, integer, no quotes>, <slow_query_id, integer, no quotes>)
  AND plan_node NOT LIKE '-----%'
GROUP BY query_id, child_query_sequence
ORDER BY child_query_sequence, query_id;
```

```sql
-- Step 3 (only for a child whose hash differs): pull both plans and compare them as TREES, per
-- child_query_sequence. plan_node_id numbering follows the plan's shape: once the shape changes, ids
-- shift, so don't match nodes by id:
-- walk parent -> child (plan_parent_id) and find the subtree whose plan_node (DS_* redistribution /
-- join-type flip) or plan_info (predicate placement) differs. Watch for a "Tables missing statistics" node.
SELECT query_id, child_query_sequence, plan_node_id, plan_parent_id, plan_node, plan_info
FROM sys_query_explain
WHERE query_id IN (<fast_query_id, integer, no quotes>, <slow_query_id, integer, no quotes>)
ORDER BY query_id, child_query_sequence, plan_node_id;   -- one full plan per run, not interleaved
```

Step 4: once a child's plan flipped, drill into the **slow run's** expensive steps to see which
operator consumed the time. `SYS_QUERY_DETAIL` carries `plan_node_id`, so you **can join it to
`SYS_QUERY_EXPLAIN` on `query_id` + `child_query_sequence` + `plan_node_id`** to label each expensive step with its plan
operator — and because each scan of a repeated table gets its **own** `plan_node_id`, this
disambiguates the "same table appears in several scan steps" case. Treat it as **best-effort**, not a
complete 1:1 map: some plan nodes have no runtime row (coordinator / no-op nodes) and some steps have
a blank `table_name` (intermediate results). Drill from the slow steps and attach the operator label:

```sql
-- Estimate vs actual: plan_node carries the planner's rows= estimate; input_rows/output_rows are the
-- step's actual rows. One plan node can cover several steps (e.g. a scan and a distribute), so compare
-- the estimate with the node's last step. A runtime filter can lower a probe-side scan's actual rows
-- below its estimate without the statistics being wrong.
SELECT d.child_query_sequence, d.segment_id, d.step_id, d.step_name,
       d.duration, d.input_rows, d.output_rows,   -- actual rows, to compare with rows= in plan_node
       d.data_skewness, d.alert,   -- duration is the step's segment's; spill/reads are on segment rows only
       d.plan_node_id, e.plan_node   -- operator label + estimate (rows=); NULL if the step has no plan node
FROM sys_query_detail d
LEFT JOIN sys_query_explain e
  ON e.query_id = d.query_id
     AND e.child_query_sequence = d.child_query_sequence
     AND e.plan_node_id = d.plan_node_id
     AND e.query_id = <query_id, integer, no quotes>   -- filters sys_query_explain early
WHERE d.query_id = <query_id, integer, no quotes> AND d.step_id >= 0
ORDER BY d.duration DESC, d.output_rows DESC;
```

### Did the data / stats move under the query? (both deployments)

```sql
-- Same SQL, different plan (or slower) with no query change? Check what moved underneath,
-- using SVV_TABLE_INFO (current whole-table rows + staleness).

-- 1) did an ANALYZE (manual OR auto) run BETWEEN the two runs? refreshes stats -> plan can flip.
--    is_automatic distinguishes auto-analyze from a manual ANALYZE.
SELECT database_name, schema_name, table_name, table_id, is_automatic, status,
       start_time, end_time, rows, modified_rows, analyze_threshold_percent, last_analyze_time
FROM sys_analyze_history
WHERE start_time BETWEEN <earlier_run_start_time, timestamp, single quotes>
                     AND <later_run_start_time, timestamp, single quotes>
  -- only tables the slow query read (SYS_QUERY_DETAIL also lists internal ids with no name — skip those)
  AND table_id IN (SELECT table_id FROM sys_query_detail
                   WHERE query_id = <slow_query_id, integer, no quotes> AND TRIM(table_name) <> '')
ORDER BY start_time DESC;

-- 2) stale-stats check: high stats_off = a lot of DML has landed since the last ANALYZE, so the
--    planner is on stale/absent stats and can pick a bad plan. Use SVV_TABLE_INFO.stats_off
--    (staleness) and tbl_rows (current rows) — not pg_class.reltuples, which is only a rough estimate.
-- Same-named tables in other schemas also match; see the note on the table-health query.
SELECT ti."database", ti."schema", ti."table", ti.tbl_rows AS current_rows, ti.stats_off,
       ti.unsorted, ti.vacuum_sort_benefit, ti.skew_rows
FROM svv_table_info ti
WHERE ti."table" IN (<table_names, string list, single-quoted and comma-separated>)
ORDER BY ti.stats_off DESC;

-- 3) physical-design change (auto OR manual) that alters the plan:
--    a) AUTOMATIC dist/sort changes Redshift applied between the runs (Automatic Table
--       Optimization). alter_from shows the table's style/keys before the change.
SELECT o.event_time, q.table_name, o.table_id, TRIM(o.alter_table_type) AS alter_table_type,
       TRIM(o.status) AS status, TRIM(o.alter_from) AS alter_from
FROM sys_auto_table_optimization o
JOIN (SELECT DISTINCT table_id, table_name FROM sys_query_detail     -- only tables the slow query read
      WHERE query_id = <slow_query_id, integer, no quotes> AND TRIM(table_name) <> '') q
  ON q.table_id = o.table_id
WHERE o.status = 'Complete'
  AND o.event_time BETWEEN <earlier_run_start_time, timestamp, single quotes>
                       AND <later_run_start_time, timestamp, single quotes>
ORDER BY o.event_time;
--    b) MANUAL design change between the runs, on any table the slow query reads — an ALTER, or a
--       rebuild (DROP + CREATE, or CREATE TABLE AS + rename):
SELECT query_id, start_time, query_type, query_text AS ddl_text
FROM sys_query_history
WHERE query_type IN ('DDL', 'CTAS')
  AND start_time BETWEEN <earlier_run_start_time, timestamp, single quotes>
                     AND <later_run_start_time, timestamp, single quotes>
  -- One ILIKE per table the slow query reads: every table_name in SYS_QUERY_DETAIL for the slow
  -- query_id (includes tables behind views). table_name is 'db.schema.table' — match on the table
  -- part only (e.g. 'sales', not 'dev.public.sales'). Also add one ILIKE per VIEW named in the slow
  -- query's text: SYS_QUERY_DETAIL lists only base tables, so a CREATE OR REPLACE VIEW between the
  -- runs would otherwise be missed. ILIKE matches substrings ('sales' also hits 'sales_stg'), so
  -- confirm each hit in ddl_text. Add "OR query_text ILIKE '%<table_name, identifier, no quotes>%'" for each.
  AND (query_text ILIKE '%<table_name, identifier, no quotes>%')
ORDER BY start_time DESC LIMIT 20;
```

## Table health — skew / unsorted / stats / ghost rows (both deployments)

```sql
-- ghost_rows = deleted rows not yet reclaimed (fix: VACUUM DELETE ONLY). vacuum_sort_benefit > 0 is
-- required before recommending VACUUM SORT; it says nothing about the delete phase.
-- SYS_QUERY_DETAIL.table_name is database.schema.table: use its table part for this filter, and its
-- schema part to pick the right row when tables with the same name exist in other schemas ("schema"
-- column). SVV_TABLE_INFO covers only the database you're connected to.
SELECT "database","schema","table", diststyle, sortkey1, tbl_rows, estimated_visible_rows,
       (tbl_rows - estimated_visible_rows) AS ghost_rows,
       unsorted, vacuum_sort_benefit, stats_off, skew_rows, skew_sortkey1
FROM svv_table_info
WHERE tbl_rows > 0
  AND "table" IN (<table_names, string list, single-quoted and comma-separated>)   -- every table the slow query reads (table part of SYS_QUERY_DETAIL.table_name)
ORDER BY stats_off DESC, vacuum_sort_benefit DESC, skew_rows DESC;
```

## Did auto-analyze / auto-vacuum already act? (both deployments)

```sql
-- Confirm stats/maintenance freshness BEFORE recommending manual ANALYZE / VACUUM.
-- A 'Skipped' status is NORMAL for background auto-analyze (it judged stats still fresh enough) — not a failure.
SELECT schema_name, table_name, is_automatic, status, start_time, last_analyze_time
FROM sys_analyze_history
WHERE start_time >= DATEADD(day, -7, GETDATE())     -- SYS_* history retention
  -- only tables the slow query read (SYS_QUERY_DETAIL also lists internal ids with no name — skip those)
  AND table_id IN (SELECT table_id FROM sys_query_detail
                   WHERE query_id = <slow_query_id, integer, no quotes> AND TRIM(table_name) <> '')
ORDER BY start_time DESC;

SELECT schema_name, table_name, vacuum_type, is_automatic, status, start_time,
       reclaimable_rows, reclaimed_rows
FROM sys_vacuum_history
WHERE start_time >= DATEADD(day, -7, GETDATE())     -- SYS_* history retention
  -- only tables the slow query read (SYS_QUERY_DETAIL also lists internal ids with no name — skip those)
  AND table_id IN (SELECT table_id FROM sys_query_detail
                   WHERE query_id = <slow_query_id, integer, no quotes> AND TRIM(table_name) <> '')
ORDER BY start_time DESC;
```

## Result-cache loss for a recurring query (both deployments)

```sql
-- Group identical statements by user_query_hash (NOT query_hash). Find the last cache hit before the
-- slow run, then list it and every run after it: the first result_cache_hit = false row after the
-- hit is where the cache was invalidated (data changed or the cached result aged out). A miss with
-- high compile_time/execution_time after prior hits = cache invalidation, not a plan regression.
WITH last_hit AS (
  SELECT MAX(start_time) AS hit_time
  FROM sys_query_history
  WHERE user_id > 1 AND user_query_hash = <user_query_hash, string, single quotes>
    AND result_cache_hit = true
    AND start_time <= <slow_run_start_time, timestamp, single quotes>
)
SELECT h.query_id, h.result_cache_hit, h.elapsed_time, h.execution_time, h.compile_time, h.start_time
FROM sys_query_history h, last_hit l
WHERE h.user_id > 1 AND h.user_query_hash = <user_query_hash, string, single quotes>
  AND h.start_time >= COALESCE(l.hit_time, DATEADD(day, -7, GETDATE()))   -- no hit in retention: show all
ORDER BY h.start_time;
```

## Queue contention — what a query queued behind (both deployments)

```sql
-- High queue_time? List queries whose run overlapped the slow query's run — candidates for what it
-- queued behind. Overlap alone doesn't prove contention: a candidate's own start_time includes its
-- waiting, so check its queue_time (a row that was itself queued wasn't using concurrency or
-- memory), and a row that started after the slow query began executing can't have caused its
-- queuing. Replace <query_id>.
-- WLM scope: the service_class_id filter below is OFF by default (automatic WLM shares concurrency
-- and memory cluster-wide). Turn it ON only when the slow query's service_class_id is 6–13 (a
-- manual WLM queue) or 14 (short query acceleration): those compete only for their own slots.
WITH target AS (
  SELECT service_class_id, start_time, end_time
  FROM sys_query_history WHERE query_id = <query_id, integer, no quotes>
)
SELECT h.query_id, h.user_id, h.service_class_id,
       h.queue_time,
       h.execution_time,
       h.start_time, h.end_time, h.query_text
FROM sys_query_history h, target t
WHERE h.query_id <> <query_id, integer, no quotes>
  -- AND h.service_class_id = t.service_class_id   -- ON only for 6–14, see WLM scope above
  AND h.start_time <= t.end_time
  AND (h.end_time IS NULL OR h.end_time >= t.start_time)   -- overlaps the slow query's run (include still-running queries)
ORDER BY h.execution_time DESC
LIMIT 20;
```

## Lock wait — transaction history (both deployments)

```sql
-- The per-query wait on a lock is the lock_wait_time bucket in SYS_QUERY_HISTORY (that's what tells
-- you a query waited). This lists committed transactions that overlapped the slow query's run:
-- CANDIDATE lock holders, not a confirmed holder — the view records no table or lock. Narrow them
-- by looking up each transaction_id's statements in SYS_QUERY_HISTORY: one that wrote to a table
-- the slow query reads is the likely holder. Only transactions that wrote data appear here; a
-- holder that only read or took a lock without writing does not.
WITH target AS (
  SELECT start_time, end_time
  FROM sys_query_history WHERE query_id = <query_id, integer, no quotes>
)
SELECT th.user_id, th.transaction_id, th.isolation_level, th.status,
       th.transaction_start_time, th.commit_start_time, th.commit_end_time
FROM sys_transaction_history th, target t
WHERE th.user_id > 1
  AND th.transaction_start_time <= t.end_time
  AND (th.commit_end_time IS NULL OR th.commit_end_time >= t.start_time)
ORDER BY th.transaction_start_time;
```

```sql
-- Live locks right now, only on tables someone is waiting for: granted = false is a waiter; a
-- granted row on the same relation is the holder.
SELECT txn_owner, txn_db, xid, pid, txn_start, lock_mode, lockable_object_type, relation, granted
FROM svv_transactions
WHERE relation IN (SELECT relation FROM svv_transactions WHERE granted = false)
ORDER BY relation, granted DESC, txn_start;
```
