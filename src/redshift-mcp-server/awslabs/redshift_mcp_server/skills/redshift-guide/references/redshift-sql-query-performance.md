# Redshift Query Performance — Time Decomposition First

Workflow for "a query that used to be fast is now slow" and similar
"why is this query slow?" questions. **Establish Serverless vs provisioned first**
(see STEP 0 in SKILL.md for the deployment split and which views are provisioned-only) —
the remediation differs by deployment.

## Decision tree (start here)

1. **Decompose** `elapsed_time` in `SYS_QUERY_HISTORY` (next section) and find the bucket
   that grew. First check that the "fast" run wasn't **served from the result cache**
   (`result_cache_hit = true`): then Redshift returned a stored result without running the query,
   so its time isn't a real baseline. Also confirm your fast/slow runs are the **same statement**
   (apples-to-apples) before comparing — an *unchanged*
   query can still degrade from data, stats, plan, or contention shifts.
2. Branch on the dominant bucket:
   - **`queue_time`** → WLM / concurrency contention; find concurrent long-runners (same queue under
     manual WLM, cluster-wide otherwise) → *When `queue_time` dominates — remediation.*
   - **`compile_time`** → first-run / post-patch recompile — expected and transient → *Segment compilation.*
   - **`planning_time`** → plan/query complexity, catalog, or datasharing elements; no deeper
     public telemetry, so if it dominates and you need more detail → **escalate to AWS.**
   - **`lock_wait_time`** → blocking transaction / concurrent DDL.
   - **`execution_time`** → real work; drill in by symptom:
     broadcast/redistribution or bad join → *Reading EXPLAIN*;
     `SELECT DISTINCT` / many LEFT JOINs → *Row multiplication (join fan-out)*;
     estimate ≠ actual → *Estimate divergence (stale/missing statistics)*;
     slow after a function on a join/dist key → *Functions on join/distribution keys*;
     one slice/node hot → *Distribution skew*;
     grew on an unchanged plan → *Stalled VACUUM.*
3. **Same query, slower, plan unchanged?** Check data-volume growth, then compare
   `redshift_version` across runs for a **patch** boundary → *Did the query change…* / escalate.

> **Escalating to AWS** = open an AWS Support case (Support Center → **Create case** →
> **Technical**, service *Amazon Redshift*) with your evidence: the `SYS_QUERY_HISTORY`
> bucket breakdown, the `query_id`(s), and `redshift_version` before/after. See
> [Creating support cases](https://docs.aws.amazon.com/awssupport/latest/user/case-management.html).

## Decompose the time before proposing any fix

When a query "got slow," do **not** jump to adding a DISTKEY/SORTKEY, rewriting the
query, or running VACUUM. First find **which time bucket regressed**. `elapsed_time` is
the total wall-clock; the other columns attribute time to individual phases (all in
**microseconds**), all available per query in `SYS_QUERY_HISTORY` (works on Serverless
*and* provisioned):

| Bucket | Column | What it means | If this bucket dominates |
|---|---|---|---|
| Queue wait | `queue_time` | Waiting for a WLM / concurrency slot | WLM config, concurrency scaling |
| Planning | `planning_time` | Time spent planning the query (parse, rewrite, plan) | Plan/query complexity (large join search space) or catalog/datasharing work. No public view decomposes `planning_time` further |
| Compile | `compile_time` | Segment compilation (see compilation below) | First-run only — warm cache expected |
| Lock wait | `lock_wait_time` | Waiting on a relation lock | Blocking transactions / concurrent DDL |
| Execution | `execution_time` | Actual work on compute nodes | Data volume, distribution skew, spill, or a stalled VACUUM (see below) |

These are separate metrics and need not add up exactly to `elapsed_time` — read them as
**attribution hints** to see which phase grew, not as a strict disjoint sum.

If **`planning_time`** is the dominant bucket, the public surface exposes only the single
`planning_time` value — there is **no further user-facing telemetry** to break it down. It
reflects plan/query complexity (large join search space, catalog work, possible datasharing
elements); if it dominates and more detail is needed, **escalate to AWS**.

```sql
-- Phase triage: where did the time go? Branch on whichever pct_* bucket dominates.
-- note: planning_time and lock_wait_time are independent metrics — lock wait is its own bucket.
SELECT query_id, user_id, database_name, query_type, status, start_time,
       service_class_id,                 -- WLM queue: needed for the queue_time branch
       compute_type,                     -- provisioned only: primary (main) / primary-scale (concurrency scaling) / secondary; not populated on Serverless
       elapsed_time, queue_time, planning_time, lock_wait_time, compile_time, execution_time,
       100.0 * queue_time     / NULLIF(elapsed_time,0) AS pct_queue,
       100.0 * planning_time  / NULLIF(elapsed_time,0) AS pct_planning,
       100.0 * lock_wait_time / NULLIF(elapsed_time,0) AS pct_lockwait,
       100.0 * compile_time   / NULLIF(elapsed_time,0) AS pct_compile,
       100.0 * execution_time / NULLIF(elapsed_time,0) AS pct_execution,
       result_cache_hit, query_text
FROM   sys_query_history
WHERE  user_id > 1                        -- drop system/internal noise
  AND  ( query_id = <query_id, integer, no quotes>
         OR query_text LIKE '%<tag_or_snippet, string, no quotes>%' )
ORDER  BY elapsed_time DESC
LIMIT  50;
```

The `pct_*` columns turn the raw buckets into shares of `elapsed_time` — read whichever is
largest to decide which phase to investigate.

Compare the buckets **across a fast run and a slow run of the same query** — the bucket
that grew is the one to investigate. Only then pick a fix, targeted at that bucket.

In particular, separate **queue wait from execution**: if the extra time is `queue_time`,
the query didn't get slower to *execute* — it waited behind other work. So investigate
**what it queued behind** (next paragraph), not the queued query itself: other concurrently
running queries were using the cluster's concurrency and memory, and tuning them often relieves
it. A large `execution_time` with small
`queue_time` instead points at the query's own work — data volume, distribution skew, or spill.

Confirm queue pressure by comparing `queue_time` to `elapsed_time` per query in
`SYS_QUERY_HISTORY` (a high queue-time share = WLM contention); on provisioned clusters, `query_priority` and
`compute_type` (`primary-scale` = the query ran on a concurrency-scaling cluster) show how
queuing and scaling are being applied.

To find *what* it queued behind, look in `SYS_QUERY_HISTORY` for concurrent **long-running
queries whose execution overlapped the slow query's queue window**, ordered by
`execution_time` desc. Scope depends on the WLM mode: under **Manual WLM** each queue
(`service_class_id`) has fixed slots and a fixed memory share, so filter to the **same
`service_class_id`** to find the slot-hogs. Under **Automatic WLM**, concurrency and
**memory are assigned dynamically per query across the whole cluster** — *not* partitioned
per service class — so don't restrict to one `service_class_id`; look at the heavy concurrent
queries **cluster-wide** in the overlap window. Either way, those long-runners are the
contention source.
Then treat the long-runner as the **new subject**: decompose *its* time and drill into its
dominant bucket (usually `execution_time` → spill / skew / plan / stats) and tune it —
fixing the hog at the source relieves the queue for everything behind it. Reprioritizing
(WLM slots/priority, QMR, separate queue) or scaling only *redistributes* the contention if
the query itself isn't addressed.

**When `queue_time` dominates — remediation.** The query queued because other concurrently
running queries were using the cluster's concurrency and memory. Find them (see the paragraph
above; the ready-to-run query is in the queries reference); tuning them is often what relieves the
queuing.

The levers below are configuration changes, so **recommend** them to the user rather than making
them. Automatic WLM, concurrency scaling, and SQA are *provisioned* levers; on Serverless, raise
capacity instead. WLM query queues and query monitoring rules (QMR) work on **both**
deployments, configured through the `wlm_json_configuration` parameter: in the cluster's
parameter group on provisioned, and in the workgroup's configuration parameters on Serverless.

- **Confirm Automatic WLM is on** — the slow query's `service_class_id` in `SYS_QUERY_HISTORY`
  tells you: 100–107 is automatic WLM, 6–13 is a manual WLM queue. If it's manual, recommend
  switching to automatic WLM so Redshift manages concurrency and memory from the workload rather
  than fixed manual slots.
- **Recommend enabling concurrency scaling** — adds transient clusters for spiky/bursty demand.
  Free-tier credits accrue per running day; confirm the current allowance on the Redshift
  concurrency-scaling pricing page rather than quoting a figure, and cap spend with a
  concurrency-scaling usage limit.
- **Confirm Short Query Acceleration (SQA) is on** (on by default; off only if
  `wlm_json_configuration` has `"short_query_queue": false`) — routes short queries past the
  queue, cutting their queue wait.
- **Separate WLM queues by workload** (BI / ETL / ad-hoc) and, on provisioned clusters, set
  **queue priorities** so critical queries aren't stuck behind heavy ones.
- **Add query monitoring rules (QMR)** to catch runaway queries (nested loops, long
  runtime, disk spill) before they clog a queue.
- **Serverless — scale capacity (no WLM mode or SQA to enable).** Two *alternative* approaches,
  not simultaneous knobs:
  - **AI-driven scaling (on by default for new workgroups).** The **Price-performance target** slider
    (Optimized for Cost ↔ Optimized for Performance; default *Balanced*) lets Redshift manage
    RPUs for you toward a cost/perf goal — you do **not** hand-set a base capacity in this
    mode. Bound the spend with **Max capacity** / Max RPU-hours. Best when you don't know the
    right base. Nudging the slider toward performance is the lever here.
  - **Manual base capacity.** Set a fixed **Base capacity (RPUs)** floor (plus a **Max
    capacity** ceiling) when you want a predictable, hand-tuned size instead of AI-driven scaling.

**Stalled VACUUM as an execution regression:** if `execution_time` (and `blocks_read` in
`SYS_QUERY_DETAIL`) grew while the *plan is unchanged*, suspect table maintenance. When
auto-vacuum stops, deleted rows linger as **ghost rows** (`tbl_rows − estimated_visible_rows`
in `SVV_TABLE_INFO`) and **`unsorted%`** climbs — both defeat sort-key zone-map pruning, so
the scan reads more blocks for the same post-filter result. Check **every** table the slow query
reads, one by one: take each `table_name` from `SYS_QUERY_DETAIL` for the slow `query_id` (it
covers tables behind views; `table_name` is `db.schema.table`), and look up each in
`SVV_TABLE_INFO`. Look first at the table whose scan sits in the segment whose `blocks_read` grew (`blocks_read` is
recorded on the segment row, not the step).
Confirm with `SYS_VACUUM_HISTORY`
(did auto-vacuum stop?) and `SVV_TABLE_INFO`, then pick the phase the evidence points to:
**ghost rows** → `VACUUM DELETE ONLY`; **unsorted rows** → `VACUUM SORT ONLY`, but only when
`vacuum_sort_benefit > 0` (high `unsorted%` alone is not a reason to sort).

For the per-step (operator-level) breakdown of the execution bucket, query `SYS_QUERY_DETAIL`
for the `query_id`. Columns are recorded at different levels:

- **Segment rows only** (0 on step rows): `blocks_read`, `spilled_block_local_disk` and
  `spilled_block_remote_disk`
- **Segment rows, copied onto each of their steps:** `duration` and `time_skewness`, so they can't
  tell a segment's steps apart
- **Step rows only:** `input_rows` and `output_rows`, `data_skewness` (how unevenly the step's rows
  were spread), and `alert` (missing stats, nested loop, large broadcast)

Find the slow segment first, then the expensive step inside it.

**A spill is a symptom, not a root cause.** When a segment spilled (the `spilled_block_local_disk` /
`spilled_block_remote_disk` columns on its segment row), its working set exceeded the memory it was granted, so
Redshift wrote intermediate data to disk. The goal is **not** zero spill: some steps spill even
when the query is well written. Check the step against these best practices, and once they're
met, treat any remaining spill as acceptable:

- **Reduce the data the step handles:** filter earlier, select only the columns needed (no
  `SELECT *`), pre-aggregate, and remove any join fan-out.
- **For a skewed spill** (one slice spills much more than the others), co-locate the join: align
  the `DISTKEY`s, or join on the distribution key, so rows aren't concentrated on one slice.
- **Refresh statistics:** a low row estimate gives the step too small a memory grant, so run
  `ANALYZE`.

Adding nodes or disk does **not** fix a skewed spill.

**Declared VARCHAR width matters only when the planner has no statistics.** Rows are stored at
their actual length, whatever the declared width. With statistics, the planner uses the column's
real average width and distinct-value count. Without them, it estimates width from the declared
width (larger for wider declarations, up to a cap). That oversizes memory grants and can
misestimate join row counts. Run `ANALYZE` to give the planner statistics — except on columns
declared very wide (e.g. `VARCHAR(65535)`), which `ANALYZE` skips; right-size those instead.

## Segment compilation (first run)

Redshift compiles optimized code for each query plan and keeps the compiled segments in a
**compiled-code cache**, locally and in a remote cache that **persists across reboots**, so later
runs skip compilation. For a query whose segments aren't in that cache yet, **composition** (on by
default) starts it immediately with pre-existing logic while the optimized code compiles in the
**background**, so first-run `compile_time` is rarely on the critical path
([Compiled code](https://docs.aws.amazon.com/redshift/latest/dg/c_challenges_achieving_high_performance_queries.html)).

To confirm compilation is the cause, check whether `compile_time` is the bucket that grew in
`SYS_QUERY_HISTORY` (`SVL_COMPILE` gives per-segment detail, provisioned only). If it is, a rerun
should be fast.

**Patch caveat.** A version upgrade / patch clears the compiled-code cache (a plain reboot does
*not*), so first runs after a patch *can* recompile — but since composition keeps that off the
critical path, **don't assume post-patch slowness is "just recompile."** Confirm it's
`compile_time` that grew and that it **vanishes on rerun**; if it's in `execution_time` / the
plan or persists after reruns, treat it as a **real regression** (compare `redshift_version`,
buckets, plan).

## Rule out result-cache hits before comparing runs

If `result_cache_hit = true`, Redshift returned a **cached result** — `execution_time`
is near-zero and tells you nothing about the query's real cost. A benchmark where the
"fast" run was a cache hit is **not** a valid measurement, and a fast→slow comparison
against a cached baseline is comparing a cache return to real compute.

- Confirm with `result_cache_hit` in `SYS_QUERY_HISTORY`.
- To measure real (uncached) cost, disable the result cache for the session:

  ```sql
  SET enable_result_cache_for_session TO off;
  ```

  or compare only cache-miss executions (`result_cache_hit = false`).

## Reading EXPLAIN: distribution and join strategy

Two things in an `EXPLAIN` plan explain most "execution bucket" slowness — data
movement and join strategy.

**Data distribution operators** (the `DS_*` labels):

| Label | Meaning | Good/bad |
|---|---|---|
| `DS_DIST_NONE` | No movement — both sides already co-located on the join key | Ideal |
| `DS_DIST_ALL_NONE` | No movement — the inner is `DISTSTYLE ALL`, already on every node | Ideal |
| `DS_DIST_INNER` | Inner table redistributed on the join key | Costly for a large inner |
| `DS_DIST_OUTER` | Outer table redistributed on the join key | Costly for a large outer |
| `DS_DIST_BOTH` | Both tables redistributed on the join key | Costly — the most data movement |
| `DS_DIST_ALL_INNER` | Entire inner redistributed to a single slice (outer is `DISTSTYLE ALL`) | Usually a distribution mismatch |
| `DS_BCAST_INNER` | The **whole inner table is broadcast to every node** | **Not inherently bad** — a cheap fan-out the planner picks on purpose when the inner is *small*; costly only when the inner is large |

**Join strategy:**

- **Merge Join** — fastest; both tables distributed *and* sorted on the join key, and less than
  20% of each table unsorted (`SVV_TABLE_INFO.unsorted`).
- **Hash Join** — the common case; builds a hash table on the inner side.
- **Nested Loop** — the correct (and only) strategy for non-equi joins (inequality /
  range conditions like `a.x < b.y`) and intentional cross joins. It is a red flag **only**
  when it shows up for what should be an equi-join — usually a missing or mistyped join
  predicate producing an accidental near-Cartesian product (a huge estimated cost is the
  tell). Check the join condition.

Fix broadcast/redistribution by **co-locating** the join: set a matching `DISTKEY` on
the join column of both tables, or `DISTSTYLE ALL` for a small, slow-moving dimension table.
`ALL` copies the whole table to every node, which multiplies its storage and slows every load
and update. There's no fixed size cutoff; when unsure, use `DISTSTYLE AUTO`, which starts a
small table as `ALL` and changes it as the table grows. To see the *executed* plan (not just the estimate), read `SYS_QUERY_DETAIL`
(`step_name` values like `hashjoin`, `nestloop`, `broadcast`, `distribute`, `scan`) or
`SYS_QUERY_EXPLAIN`.

## Row multiplication (join fan-out)

A `SELECT DISTINCT` or aggregate over many `LEFT JOIN`s can be slow because the joins
**fan out** — one row matches many in a dimension/lookup table, so an intermediate join
step processes billions of rows that `DISTINCT` then collapses back to a few million.

- Spot it in `SYS_QUERY_DETAIL`: a join step's `output_rows` is **far larger** than the
  query's final returned rows (huge join row count vs small result). Broadcast
  (`DS_BCAST_INNER`) on those joins compounds it.
- Find the offending join by testing each `LEFT JOIN` incrementally with `COUNT(*)`.
- Fix (**only when the query's semantics permit it** — i.e. the multiplied rows aren't actually
  needed): **pre-aggregate or deduplicate the lookup tables** in a `WITH` clause / subquery so each
  returns one row per key (restore the one-to-one relationship) *before* joining; and co-locate the
  joins on the distribution key.

## Diff the plan across the fast and slow run

Reading one plan shows the current shape; **diffing the fast run's plan against the slow
run's** shows *what changed*. Do this when the buckets point at execution/plan and you have
both a fast and a slow run of the same statement.

1. **Pair the two runs.** Get one fast and one slow `query_id` for the **same query** — group runs
   by the built-in `generic_query_hash` / `user_query_hash`, or by a **normalized SQL text**
   fingerprint (mask literal values, keep identifiers). Use whichever is handy.
2. **Fingerprint each plan to decide *whether* the shape changed — before eyeballing nodes.**
   Pull `SYS_QUERY_EXPLAIN` (populated **per child query**: `query_id` + `child_query_sequence`;
   a rewritten statement has several child plans). Raw plan text is noisy: `plan_info` embeds the
   WHERE **literals** (`Filter: (dt >= '2026-01-01'::date)`) and `plan_node` embeds volatile
   `cost=…`/`rows=…`/`width=…` — all vary run-to-run even when the shape is identical. So build a
   **normalized plan hash** per `child_query_sequence`:
   - Order rows by `plan_node_id`; concatenate `plan_node` + `plan_info`.
   - **Strip the volatile parts:** replace literal constants in `plan_info` (`'…'`, `…::type`,
     bare numbers) with a placeholder, and drop the `cost=`/`rows=`/`width=` numbers from `plan_node`.
   - **Keep the structure:** operator, `DS_*` label, join type, and the predicate *columns*.
   - Hash the result. **Equal fast-vs-slow hash → the plan shape did not change** — stop diffing
     the plan and go to the data/stats check (next section) or the other buckets. **Different →
     the plan flipped**; drop to the tree diff.

   > **Reading the plan as a tree.** `SYS_QUERY_EXPLAIN` returns nodes: `plan_node_id` identifies
   > each node and `plan_parent_id` points to its parent, so together they reconstruct the operator
   > tree. `plan_node_id` is *within-plan* — it also joins to `SYS_QUERY_DETAIL`
   > (`query_id` + `child_query_sequence` + `plan_node_id`) to show which execution segment/step ran a node — but it is
   > **not** a stable identity across two runs, so don't assume node N in the fast run is node N in
   > the slow run. Localize the change by walking parent→child and finding the subtree where
   > `plan_node` (operator / `DS_*` / join type) or `plan_info` (predicate columns) differs.

3. **Tree diff (only when the hashes differ), per `child_query_sequence`:**
   - **`plan_node`** — a `DS_DIST_NONE` / `DS_DIST_ALL_NONE` that became `DS_BCAST_INNER` /
     `DS_DIST_INNER` / `DS_DIST_BOTH`, or a Hash/Merge Join that became a Nested Loop, **is** the
     regression.
   - **`plan_info`** — join conditions and WHERE restrictions; a predicate that moved (e.g. a
     filter no longer applied at the `Seq Scan` but late in a join) shows **predicate placement**
     changed — often the cause of a redistribution flip.
   - `SYS_QUERY_EXPLAIN` also emits a `----- Tables missing statistics -----` node — a direct
     stale/missing-stats signal.
   - **Tie the flip back to the execution evidence — map node → segment.** A plan change that
     raised `execution_time` should be traceable to a specific segment, but the changed node isn't
     always the slowest one: a flip in an *earlier* segment (e.g. a redistribution that lands rows
     badly) can make a *later* segment the bottleneck. So map the changed `plan_node` to its
     segment, pull the slowest segments for the slow run from `SYS_QUERY_DETAIL` (order by
     `duration`), and check whether the slowest segment **is, or is fed by, the changed node** —
     comparing the same segments against a successful (fast) run. If the slowest segment can't be
     traced back to the plan change, the flip may not be the cause — re-check the other buckets.
4. **Estimate drift on the base-table scans (no separate hash — just read `rows=`).** For the
   **`Seq Scan` nodes on base tables**, compare the scan's `rows=` **estimate** between the fast
   and slow run. A `rows=` estimate that changed run-to-run — or a `----- Tables missing
   statistics -----` node — means the **stats/data moved under the query**, so the plan didn't have
   to change shape to get slower. Read the estimate off the scan node. To compare it with the actual rows, use the queries
   reference's plan-diff Step 4, which joins each step to its own plan node, so a table scanned
   several times is still matched correctly. This is the hand-off to the next section.

If the two plans are identical (same hash) but the timing still differs, the plan shape is **not**
the cause. Four common culprits: (a) the WHERE **literals select more rows** — same plan, but a
wider predicate reads/returns more data (see the data/stats section below); (b) **the base tables
grew** — same plan, but more input rows to scan/join means linearly more `execution_time`; confirm
by comparing the scan steps' `input_rows` (and `output_rows`) in `SYS_QUERY_DETAIL` between the
comparable runs, not `SVV_TABLE_INFO.tbl_rows` (current snapshot only, no history); or
(c) **concurrency contention** — more queries running concurrently during the slow run's window,
especially long-runners or heavy spillers competing for compute / memory / disk (this is *not*
queue-slot waiting, which shows up as `queue_time`; see the concurrent long-runner query in the
queue section); or (d) **duplicate data / join fan-out** — new duplicate keys (or an accidental
near-cartesian join) make an intermediate join step explode to far more rows even when the
**final** returned rows look close to the fast run, so the extra work is invisible in the result
count; confirm by comparing a join step's intermediate `output_rows` in `SYS_QUERY_DETAIL`
between the runs (see *Row multiplication (join fan-out)* above). If none fits, re-decompose the
time buckets (top of this doc) to see which one actually grew.

An identical plan doesn't guarantee identical row counts per step. On hash joins, Redshift can
build a **runtime (Bloom) filter** from the build side's join keys and apply it inside the
probe-side scan, dropping rows that can't match before they reach the join. EXPLAIN doesn't show
it, and `SYS_QUERY_DETAIL` gives it no step of its own. It shows only as that scan's
`output_rows`, which also reflects any filter in the plan, so the two can't be separated. Whether
the filter is used, and how much it removes, can vary between runs of the same plan. So when two
same-plan runs show different `output_rows` on a hash join's probe-side scan, a runtime filter
behaving differently is a candidate cause, not only a change in the data.

Across environments (e.g. a dc2→ra3 migration or a rebuilt table), also confirm the
underlying tables share the **same physical design** — compare `diststyle` / `distkey` /
`sortkey` via `SVV_TABLE_INFO` (or `SHOW TABLE`) on each side. `DISTSTYLE AUTO` /
`SORTKEY AUTO` can pick different keys per environment, which by itself changes the plan.

## Data changes flip the plan — even when no `ANALYZE` has run

The optimizer builds each plan from the row counts and statistics it holds **at plan time**.
Those inputs change without any change to the query: data loads and deletes change row counts,
and `ANALYZE` (manual or automatic) refreshes the statistics. So the *same* SQL can get a new
plan (or the same plan, run slower) with **no query-text change**. When the plan hash changed, or the base-table scan's `rows=`
estimate differed between the runs (above), work this checklist to find *what moved underneath
the query*:

1. **Statistics were refreshed between the runs.** An `ANALYZE` — **manual or auto** — updates
   the statistics, which alone can flip the plan. Confirm one ran **between** the two runs in
   `SYS_ANALYZE_HISTORY` (`is_automatic` tells you which; check for *either*).
2. **Row counts grew (feeds the cost model).** A larger table raises estimated scan/join cost, so
   a co-located `DS_DIST_NONE` join can flip to `DS_BCAST_INNER` / redistribution past a threshold. The signal is the base-table scan's **`rows=` estimate differing between
   the comparable runs** (above). Don't try to prove growth from `SVV_TABLE_INFO.tbl_rows` — it is
   only the *current* row count (a snapshot, no history), and a `WHERE` predicate would filter the
   scan estimate below the full-table count anyway, so the two aren't comparable.
3. **Stats went stale.** As data changes, the planner's whole-table estimate drifts from reality.
   Read staleness from `SVV_TABLE_INFO.stats_off` (`0` = current, `100` = fully stale), and check
   whether **DML has landed since the last `ANALYZE`** (last-analyze time is in `SYS_ANALYZE_HISTORY`).
   Use `SVV_TABLE_INFO` (`stats_off`, `tbl_rows`) for this — not `pg_class.reltuples`, which is only a
   rough estimate. A stale estimate flips the plan before you would think to run `ANALYZE`. Check
   **every** referenced table (see the next section).
4. **The physical design changed — auto *or* manual.** A dist/sort-key change alters the plan:
   Redshift can **auto**-apply dist/sort recommendations, and a **manual** `ALTER TABLE … ALTER
   DISTKEY/SORTKEY` (or a table rebuild) does the same. Check both: recent DDL history for manual
   changes, and `SYS_AUTO_TABLE_OPTIMIZATION` for automatic ones.
5. **Sort order / pruning degraded.** Appends raise `unsorted%`, weakening zone-map pruning so
   scans read more blocks for the same rows. This slows the query on an **unchanged plan**. The
   signal is the scan's segment `blocks_read` rising in `SYS_QUERY_DETAIL` while its `input_rows`
   stays comparable across the runs. Confirm with `SVV_TABLE_INFO.unsorted` and
   `vacuum_sort_benefit` for that table, and with `SYS_VACUUM_HISTORY` (did auto-vacuum stop or
   fall behind?). **Fix:** `VACUUM SORT ONLY <schema_table, identifier, no quotes>;`, but only when
   `vacuum_sort_benefit > 0`. See *Stalled VACUUM* above.

The common thread: a plan or timing change on unchanged SQL usually traces to **statistics,
row-count, physical-design, or sort-order movement**, not the query — verify these before rewriting the query
or forcing DDL.

## Estimate divergence: stale or missing statistics

When `EXPLAIN`'s estimated rows are wildly off from the actual rows, the optimizer is
planning on **stale or missing statistics**, and a bad estimate produces a bad plan. Not every gap
means bad statistics. For example, on a hash join's probe-side scan a runtime filter can make the
actual rows much lower than the estimate even when the statistics are current (see the
runtime-filter note under *Diff the plan across the fast and slow run*).

- Check staleness with `SVV_TABLE_INFO.stats_off` (`0` = current, `100` = fully stale).
- Fix by running `ANALYZE <schema_table, identifier, no quotes>;`. It refreshes both the
  row counts and the column statistics (distinct values, most common values) that filter
  and join estimates depend on. `ANALYZE`, **not** `VACUUM`, is what updates the planner
  statistics.
- Confirm the divergence by comparing the estimate (`EXPLAIN` `rows=`) to the **actual**
  `input_rows` / `output_rows` per step in `SYS_QUERY_DETAIL` (the **queries reference's** plan-diff Step 4 shows both
  side by side).
- Before recommending a **manual** `ANALYZE`, check `SYS_ANALYZE_HISTORY` — auto-analyze
  may already have refreshed the statistics.
- Check `stats_off` for **every** table the query references (all joined tables / CTE
  sources), not just the largest or most obvious one — a single stale table's bad estimate
  can flip the whole plan. `ANALYZE` each stale table.

## Functions on join / distribution keys slow the join

Wrapping a join or distribution key in a function or expression — `ON LOWER(a.id) =
LOWER(b.id)`, `a.id || '' = b.id || ''`, `CAST`, `SUBSTRING`, etc. — makes the join slower,
for two reasons:

1. **It defeats `DISTKEY` co-location.** The expression's value no longer matches the
   column's distribution, so Redshift must redistribute or broadcast instead of doing a
   co-located join.
2. **It defeats column statistics.** Statistics are collected on *columns*, not on
   expressions, so the optimizer can't estimate the expression's cardinality and falls
   back to a poor default — an underestimate that can flip a co-located join to broadcast
   or redistribution.

The expression isn't always in the SQL you're looking at. If the query reads from a **view**,
the function can come from the view's definition, and redefining the view changes the join
without any change to the query text. Check the join condition in the plan (`Hash Cond` in
`SYS_QUERY_EXPLAIN.plan_info`), not only the SQL.

Fix: join on the **raw column**. If the transformation is genuinely needed, persist it as
a materialized/precomputed column (and distribute/sort on that) so both the distkey and
the statistics stay usable.

## Distribution skew: one slice doing all the work

If one slice/node is doing far more work than the others while the rest sit idle, the
query has **skew**. Two distinct causes:

- **Table distribution skew** — a `DISTKEY` on a low-cardinality or heavily-repeated
  column piles disproportionate rows onto one slice; a fixed property of the table.
  Detect with `SVV_TABLE_INFO.skew_rows` — the ratio of the most-populated to
  least-populated slice (near `1.0` is even; large values are skewed).
- **Runtime (redistribution) skew** — a hash join or broadcast redistributes rows so one
  slice receives most of them *for a step*, even when the base tables are evenly
  distributed; per-query, not a table property.

Detect runtime skew with `SYS_QUERY_DETAIL`'s `data_skewness` and `time_skewness` (`0`–`100`%,
higher = more unbalanced), which report how unevenly work fell **across slices**. `data_skewness`
is per step (how unevenly the step's rows were spread); `time_skewness` is the segment's value,
repeated on each of its steps. They flag *that* a step or segment is skewed, not where the skew
sits; you don't need that to fix it. Tell table skew from runtime skew (`SVV_TABLE_INFO.skew_rows`
vs `SYS_QUERY_DETAIL.data_skewness`), then apply the remediation below.

Remediation depends on the case: **table skew** is typically addressed by a better
distribution (a higher-cardinality `DISTKEY`, or `DISTSTYLE EVEN`); **runtime redistribution
skew** by co-locating the join (aligning `DISTKEY`s / joining on the distribution key). Whether a
distribution change is worth it depends on the query mix, table size, and how other queries join
the table — so prefer `DISTSTYLE AUTO`, which chooses the distribution from the observed
workload, and check `SVV_ALTER_TABLE_RECOMMENDATIONS` for a pending recommendation before
choosing a key by hand. Resizing the cluster or adding nodes does **not** fix skew — it just
spreads the same skewed data across more slices, so one slice still carries the
disproportionate load.

## Did the query change, or something around it?

Before assuming "the query got slower," confirm whether the **SQL text** even changed:

- `SYS_QUERY_HISTORY` exposes `user_query_hash` (same text including literals) and
  `generic_query_hash` (same text ignoring literals). If the hash is unchanged across the
  fast and slow runs, **the query did not change** — look elsewhere.
- If the text is unchanged, investigate what changed *around* it: data-volume growth
  (compare the base-table scan steps' `input_rows` in `SYS_QUERY_DETAIL` between the fast and
  slow runs), stale stats, or a plan change. Compare the fast vs slow executions with `SYS_QUERY_HISTORY` (time buckets) and
  `SYS_QUERY_DETAIL` (per-step rows and the `alert` column for plan-quality warnings).
- **Patch/version regression:** only after ruling out buckets, data volume, stats, plan,
  and spill/skew, compare `redshift_version` across the before/after runs in
  `SYS_QUERY_HISTORY` — a version change lining up with the regression points at a patch.
  A patch is far more credible when the regression **affects many unrelated queries across the
  cluster** at the same date boundary — plans flipping across multiple queries at comparable
  row counts and stats — not just this one; a single query regressing usually has a local
  cause, so confirm the symptom spans multiple queries across the cluster first. Patch internals and restart reasons are **not**
  public, so conclude "a patch caused it" only once the above are eliminated, and **escalate
  with the bucket + version + multi-query evidence** rather than blaming the patch from timing
  alone.
