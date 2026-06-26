# DSQL Wait Events Reference

Aurora DSQL exposes wait events via the `wait_event` label on `db.active_sessions.avg`. Each indicates where sessions spend time.

---

## Summary

| Wait Event | Category | Threshold | Description |
|---|---|---|---|
| OnCpu | Compute | AAS > 1.0 | Actively processing in QP, not waiting for any other resource |
| ClientRead | Network | AAS > 0.5 | QP is waiting for the next request (only reported when QP has an active transaction — idle in transaction) |
| ClientWrite | Network | AAS > 0.5 | QP is sending data to the application |
| SequentialScanRead | IO | AAS > 0.5 | QP has issued a scan of a contiguous range of tuples |
| ScatteredBatchRead | IO | AAS > 0.5 | QP has issued one or more non-contiguous tuple reads |
| SingleRead | IO | AAS > 1.0 | QP is reading a tuple returned by a streamed storage operation |
| FkExistenceCheck | Validation | AAS > 0.3 | Storage reads to validate foreign key existence |
| UniqueConstraintCheck | Validation | AAS > 0.3 | Storage reads to validate unique key constraints for non-primary columns |
| Commit | Transaction | AAS > 0.5 | Commit process has begun, and QP is waiting for a response |
| PgSleep | Application | Any | Session issued `pg_sleep()` and is waiting for the sleep period to complete |

---

## OnCpu

Actively processing in the Query Processor (QP), not waiting for any other resource.

**Problem signal:** AAS(OnCpu) > 1.0 sustained.

**Root causes:**
- Complex plans with nested loops or expensive expressions
- Sequential scans on large tables (check SequentialScanRead co-occurrence)
- High-frequency short queries from many connections

**Remediation:**
1. Identify top SQL: `topk(5, sum by (normalized_sql, query_id)(db.active_sessions.avg{wait_event="OnCpu", ...}))`
2. Compare against baseline — identify which queries have grown
3. Defer to `dsql` skill for EXPLAIN analysis — look for plan changes, sequential scans, nested loops

---

## ClientRead

QP is waiting for the next request. This is only reported when the QP has an active transaction (idle in transaction).

**Problem signal:** AAS(ClientRead) > 0.5 sustained.

**Root causes:**
- Client has an open transaction but is not sending the next query (idle in transaction)
- Application doing work between queries without closing the transaction
- Missing `COMMIT`/`ROLLBACK` after error paths
- Connection pool returning connections with open transactions
- Network latency (cross-region, VPN)

**Remediation:**
1. Identify role/app: `sum by (iam_role_arn, application_name)(db.active_sessions.avg{wait_event="ClientRead", ...})`
2. Set `idle_in_transaction_session_timeout` to limit idle transaction duration
3. Fix application error-handling to always close transactions
4. Audit connection pool configuration — ensure pools issue RESET or DISCARD on return
5. Move compute closer to the cluster (same region/AZ) to reduce network latency

---

## ClientWrite

QP is sending data to the application.

**Problem signal:** AAS(ClientWrite) > 0.5 sustained.

**Root causes:**
- Client slow processing result sets
- Large result sets saturating network buffers
- Client-side GC pauses or I/O blocking

**Remediation:**
1. Identify app: `sum by (application_name)(db.active_sessions.avg{wait_event="ClientWrite", ...})`
2. Add `LIMIT` or pagination to reduce result size
3. Implement server-side cursors for large fetches
4. Check client network throughput and TCP buffers

---

## SequentialScanRead

QP has issued a scan of a contiguous range of tuples.

**Problem signal:** AAS(SequentialScanRead) > 0.5.

**Root causes:**
- Missing index for the WHERE clause
- Plan regression — index exists but planner chose scan after statistics changed (e.g., bulk load, `ANALYZE` updated selectivity estimates)
- Intentional full-table aggregation

**Diagnosis — distinguish missing index from plan flip:**
- Compare AAS trend over time (Workflow 5). A sudden jump (not proportional to traffic growth) suggests plan regression.
- Run `EXPLAIN` on the query. If an index exists on the filtered columns but is not used, the planner has flipped.

**Remediation:**
1. Identify query: `topk(3, sum by (normalized_sql, query_id)(db.active_sessions.avg{wait_event="SequentialScanRead", ...}))`
2. Compare against baseline — a sudden jump (not proportional to traffic growth) suggests plan regression
3. Defer to `dsql` skill for EXPLAIN analysis: determine whether an index is missing, or an existing index is not being used due to statistics change
4. If intentional (analytics workload), accept or schedule off-peak

---

## ScatteredBatchRead

QP has issued one or more non-contiguous tuple reads.

**Problem signal:** AAS(ScatteredBatchRead) > 0.5.

**Root causes:**
- Query lacks a partition-key filter, touching all partitions
- Secondary index lookup followed by wide data fetch
- Batch operations with keys spread across partitions

**Remediation:**
1. Identify query: `topk(3, sum by (normalized_sql, query_id)(db.active_sessions.avg{wait_event="ScatteredBatchRead", ...}))`
2. Compare against baseline — has a specific query's ScatteredBatchRead grown?
3. Defer to `dsql` skill for EXPLAIN analysis to determine whether predicates can be narrowed or a covering index would help

---

## SingleRead

QP is reading a tuple returned by a streamed storage operation.

**Problem signal:** AAS(SingleRead) > 1.0. Many single-tuple reads accumulating.

**Root causes:**
- A query called at very high frequency (e.g., N+1 pattern — each call is fast but volume accumulates AAS)
- A query performing many streamed storage reads per execution
- ORM lazy-loading relationships triggering many individual lookups

**Note:** Because `normalized_sql` groups all executions of the same query shape, a single-key lookup called thousands of times per second will appear as a high-AAS query — indistinguishable from a slow query in this metric alone.

**Remediation:**
1. Identify query: `topk(5, sum by (normalized_sql)(db.active_sessions.avg{wait_event="SingleRead", ...}))`
2. Check if SingleRead AAS has grown vs baseline — may indicate increased call frequency or plan change
3. Defer to `dsql` skill — it can distinguish high-frequency calls from per-execution cost via EXPLAIN ANALYZE and `pg_stat_statements` call counts

---

## FkExistenceCheck

Storage reads to validate foreign key existence.

**Problem signal:** AAS(FkExistenceCheck) > 0.3.

**Root causes:**
- High-throughput INSERT/UPDATE on child tables with foreign key references
- Parent table lookups becoming a bottleneck under concurrent writes
- Wide fan-out of FK checks across distributed partitions

**Remediation:**
1. Identify query: `sum by (normalized_sql)(db.active_sessions.avg{wait_event="FkExistenceCheck", ...})`
2. Batch child-row inserts to amortize FK lookup cost
3. Ensure parent table primary key is well-distributed (UUID recommended)
4. Consider application-layer referential integrity for extreme throughput

---

## UniqueConstraintCheck

Storage reads to validate unique key constraints for non-primary columns.

**Problem signal:** AAS(UniqueConstraintCheck) > 0.3.

**Root causes:**
- High-throughput INSERT on a table with unique constraints (hot key space)
- Large batch INSERTs forcing many uniqueness checks
- Conflict-heavy upsert patterns (`INSERT ... ON CONFLICT`)

**Remediation:**
1. Identify query: `sum by (normalized_sql)(db.active_sessions.avg{wait_event="UniqueConstraintCheck", ...})`
2. Reduce batch size for inserts on constrained tables
3. Pre-validate uniqueness at the application layer when possible
4. Use UUID primary keys to distribute insert load and avoid hot keys

---

## Commit

Commit process has begun, and QP is waiting for a response.

**Problem signal:** AAS(Commit) > 0.5.

**Root causes:**
- Increased transaction volume (legitimate load growth)
- Increased OCC (optimistic concurrency control) conflicts (write-write contention)
- Large transactions modifying many rows (more commit coordination)

**Diagnosis — distinguish volume from conflicts:**
- Query standard CloudWatch metrics: `AuroraDSQL` namespace, `ClusterId` dimension
- Compare `TotalTransactions` (commit rate) and `OccConflicts` (conflict rate) over the same period
- If OccConflicts grows faster than TotalTransactions → conflict problem
- If TotalTransactions grows proportionally to Commit AAS → legitimate load

**Remediation:**
1. Identify if Commit AAS change is proportional to transaction volume via CW metrics
2. If OCC conflicts are growing: identify conflicting writes via `sum by (normalized_sql)(db.active_sessions.avg{wait_event="Commit", ...})`
3. Defer to `dsql` skill for transaction pattern analysis and conflict mitigation

---

## PgSleep

Session issued `pg_sleep()` and is waiting for the sleep period to complete.

**Problem signal:** Rarely a real problem. AAS(PgSleep) > 0 means intentional sleeping.

**Root causes:**
- Application-level polling or throttling
- Health-check queries with built-in delay
- Intentional rate limiting

**Remediation:**
1. Verify intentional: `sum by (application_name)(db.active_sessions.avg{wait_event="PgSleep", ...})`
2. If unintentional, remove the `pg_sleep()` call
3. If consuming too many connections, move the delay to the application layer
