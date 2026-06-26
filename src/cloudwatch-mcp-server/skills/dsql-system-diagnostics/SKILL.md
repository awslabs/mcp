---
name: dsql-system-diagnostics
description: Diagnose Aurora DSQL performance issues using PromQL queries against CloudWatch OTel metrics. Detect anomalies in wait event distribution, identify regression points, and hand off to the dsql skill for live database investigation.
---

# DSQL System Diagnostics

Diagnose Aurora DSQL cluster performance by querying Active Average Sessions (AAS) via PromQL, detecting temporal anomalies in wait event distribution, and handing off to the `dsql` skill for root cause analysis.

**Key capabilities:**
- Temporal trend analysis of AAS via `db.active_sessions.avg` metric
- Wait event distribution shift detection
- Top-SQL regression identification (new or growing queries)
- Automatic handoff to `dsql` skill for live database investigation

**Important principles:**
- There is no upper bound to AAS in DSQL — absolute values are not inherently problematic
- What matters is **change over time**: shifts in wait event distribution, new queries appearing, or existing queries consuming disproportionately more time
- This skill observes via CloudWatch only — it does **not** recommend schema changes, indexing strategies, or query rewrites. Those require live database access via the `dsql` skill.

---

## Prerequisites

**MUST** have before starting:
1. A specific `cluster_id` to investigate — never proceed without one. Ask the user if not provided.
2. The CloudWatch MCP server configured with PromQL access (see [mcp-setup.md](mcp/mcp-setup.md))

---

## Reference Files

### MCP:
#### [mcp-setup.md](mcp/mcp-setup.md)
**When:** ALWAYS load before starting a diagnostic session
**Contains:** CloudWatch MCP server configuration for PromQL access

#### [.mcp.json](mcp/.mcp.json)
**When:** Load when setting up MCP servers for the first time
**Contains:** Sample MCP configuration for the CloudWatch MCP server

### [wait-events.md](references/wait-events.md)
**When:** ALWAYS load when interpreting AAS results
**Contains:** DSQL wait events with canonical descriptions and investigation guidance

### [promql-patterns.md](references/promql-patterns.md)
**When:** Load when constructing PromQL queries
**Contains:** Reusable PromQL query templates for all workflows

---

## Core Concept: Active Average Sessions (AAS)

The primary metric is `db.active_sessions.avg` — the average number of sessions actively executing or waiting at a given instant.

**Normalized SQL and AAS interpretation:** All SQL in the metric is normalized (parameterized). The `normalized_sql` label groups all executions of the same query shape. A query with high AAS could mean either:
- A slow query (high per-execution cost)
- A fast query called at very high frequency (volume accumulates AAS)

This skill cannot distinguish between these — the `dsql` skill can via call counts and per-execution timing.

| Label | Purpose |
|-------|---------|
| `wait_event` | Which wait the session is in (OnCpu, ClientRead, Commit, etc.) |
| `normalized_sql` | SQL fingerprint — groups identical query shapes |
| `query_id` | Correlates with DSQL `EXPLAIN` Query Identifier |
| `application_name` | Client application identifier |
| `iam_role_arn` | IAM role used for the connection |
| `session_state` | Session state (active) |
| `@resource.aws.auroradsql.cluster_id` | Cluster identifier for filtering |
| `@resource.cloud.resource_id` | Full cluster ARN |

---

## Workflow 1: Quick Health Check

**Goal:** Detect whether the cluster's wait event distribution has changed compared to historical baselines.

**Steps:**
1. Confirm you have a specific `cluster_id` — do not proceed without one
2. Query AAS by `wait_event` for the **current hour** in 10-minute chunks (step=60s) — compare the chunks against each other to detect recent shifts
3. Query AAS by `wait_event` for the **same hour yesterday** (baseline 1)
4. Query AAS by `wait_event` for the **same hour last week** (baseline 2)
5. Compute the distribution (% each wait event contributes to total AAS) for each period
6. Flag any wait event where the proportion changed by >30% vs either baseline
7. Load [wait-events.md](references/wait-events.md) and interpret flagged changes

**Critical rules:**
- **MUST** have a specific `cluster_id` before proceeding
- **MUST** filter by cluster using `"@resource.aws.auroradsql.cluster_id"`
- **MUST** compare against temporal baselines — do NOT report absolute AAS values as inherently problematic
- **MUST** split the current hour into 10-minute chunks and compare them to detect intra-hour shifts
- A >30% change in a wait event's share of total AAS warrants flagging to the user
- If total AAS increased but distribution is unchanged, this may be legitimate load growth — report but do not alarm

**Example:**
```promql
# Current hour (split into chunks for intra-hour comparison)
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="NOW-1h", end="NOW", step="60s"
)

# Same hour yesterday
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="NOW-25h", end="NOW-24h", step="60s"
)

# Same hour last week
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="NOW-169h", end="NOW-168h", step="60s"
)
```

---

## Workflow 2: Top-SQL Regression Detection

**Goal:** Identify SQL statements that have become more prominent compared to baseline periods.

**Steps:**
1. Query top-N SQL by AAS for the current period
2. Query top-N SQL for the same period yesterday and last week
3. Identify queries that are **new** in the top-N or have **grown** significantly vs baseline
4. Note which `wait_event` dominates for the regressed queries

**Critical rules:**
- **MUST** include `query_id` in grouping — stable identifier for handoff to `dsql` skill
- **MUST** compare top-N across periods — a query being #1 is only notable if it wasn't before
- **MUST NOT** recommend indexing or schema changes — defer to `dsql` skill

**Example:**
```promql
# Top 5 SQL for current period
execute_promql_query(query='topk(5, sum by (normalized_sql, query_id)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"}))')

# Top 5 SQL with wait event context
execute_promql_query(query='topk(10, sum by (normalized_sql, query_id, wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"}))')
```

---

## Workflow 3: Triage Decision Tree

**Goal:** Guide investigation based on which wait event has shifted.

**Steps:**
1. Run Workflow 1 to identify which wait event(s) have changed
2. Branch on the wait event showing the largest shift:

| Changed Wait Event | Investigation |
|---|---|
| **OnCpu** | Identify which queries grew via Workflow 2. Hand off to `dsql` skill. |
| **ClientRead** | Top IAM role + application. Indicates idle-in-transaction growth — client-side issue. |
| **ClientWrite** | Top application. Client is slow consuming results — check client health. |
| **SequentialScanRead** | Identify query via Workflow 2. Hand off to `dsql` skill — may be plan regression or missing index. |
| **ScatteredBatchRead** | Identify query. Hand off to `dsql` skill. |
| **SingleRead** | Identify query. Hand off to `dsql` skill. |
| **FkExistenceCheck** | Identify query. Check whether insert volume increased. |
| **UniqueConstraintCheck** | Identify query. Check whether insert/upsert patterns changed. |
| **Commit** | Run Workflow 6 (Commit Analysis) to distinguish volume increase from OCC conflicts. |
| **PgSleep** | Identify application. Verify intentional — may indicate new polling behavior. |

3. Load [wait-events.md](references/wait-events.md) for detailed investigation guidance

---

## Workflow 4: IAM Role and Application Attribution

**Goal:** Identify which roles or applications are driving anomalous changes.

**Critical rules:**
- **MUST** compare against baseline — an application being dominant is only noteworthy if it has changed
- Report the delta: "application X increased from 30% to 55% of total AAS"

**Example:**
```promql
# Top IAM roles
execute_promql_query(query='topk(5, sum by (iam_role_arn)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"}))')

# Top applications
execute_promql_query(query='topk(5, sum by (application_name)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"}))')
```

---

## Workflow 5: Time-Series Investigation

**Goal:** Identify when a change occurred and pinpoint the inflection point.

**Critical rules:**
- **SHOULD** use step: 60s (< 1h), 300s (1–6h), 900s (> 6h), 3600s (> 24h)
- **MUST** specify `start` and `end` in RFC 3339 format
- Maximum range per query is 7 days — split longer investigations into multiple queries
- Look for: inflection points, step-changes in specific wait events, distribution shifts

**Example:**
```promql
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="2024-01-15T10:00:00Z",
  end="2024-01-15T16:00:00Z",
  step="300s"
)
```

---

## Workflow 6: Commit Analysis

**Goal:** Distinguish between increased commit volume (legitimate) and OCC conflict growth (problematic).

**Steps:**
1. Confirm Commit wait has shifted (from Workflow 1 comparison)
2. Query standard CloudWatch metrics for the same period:
   - `AuroraDSQL` namespace, dimension `ClusterId`
   - Metric: `TotalTransactions` — rate of committed transactions
   - Metric: `OccConflicts` — rate of optimistic concurrency conflicts
3. Compare the ratios:
   - If TotalTransactions increased proportionally to Commit AAS → legitimate load growth
   - If OccConflicts increased disproportionately → write-write conflict problem
   - If Commit AAS increased but TotalTransactions did not → transactions are taking longer to commit

**Example (standard CW metrics):**
```
get_metric_data(
  namespace="AuroraDSQL",
  metric_name="TotalTransactions",
  dimensions=[{name: "ClusterId", value: "CLUSTER_ID"}],
  statistic="Sum"
)

get_metric_data(
  namespace="AuroraDSQL",
  metric_name="OccConflicts",
  dimensions=[{name: "ClusterId", value: "CLUSTER_ID"}],
  statistic="Sum"
)
```

---

## Idle Cluster Detection

A cluster is idle when there is no AAS data for a period. Use a range query and look for gaps (missing timestamps) in the time series.

**Pattern: Sporadic workload** — periods of no data interspersed with periods of AAS > 0 indicate a cluster performing scheduled or batch work.

```promql
execute_promql_range_query(
  query='sum({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="NOW-24h", end="NOW", step="300s"
)
```

---

## DSQL Skill Handoff

When investigation identifies a query that has become more prominent, hand off to the `dsql` skill for live database analysis. Do not provide specific diagnostics or recommendations — simply describe the observed anomaly.

### Automatic Handoff

Before handing off, verify the `dsql` skill's MCP server is configured for the cluster under investigation:

1. Check if the `aurora-dsql` MCP server is configured (look for it in the active MCP servers)
2. Verify the `--cluster_endpoint` in its args matches the cluster being investigated
3. If not configured or pointing to a different cluster, prompt the user:
   > "The Aurora DSQL MCP server needs to be configured for cluster `{CLUSTER_ID}` to proceed with live database investigation. Please add or update the `aurora-dsql` server in your MCP configuration with `--cluster_endpoint {CLUSTER_ENDPOINT}`."

### Handoff Format

When handing off, describe only the observed anomaly — do not suggest causes or fixes:

> "Query `{NORMALIZED_SQL}` (query_id: `{QUERY_ID}`) is using significantly more system time than it did {TIMEFRAME} ago. Its share of cluster AAS on `{WAIT_EVENT}` has grown from {OLD}% to {NEW}%. Please diagnose what is happening with this query."

### When to Hand Off

- Any query identified in Workflow 2 as newly prominent or significantly grown
- SequentialScanRead, OnCpu, ScatteredBatchRead, or SingleRead shifts where a specific query is responsible
- OCC conflict growth confirmed in Workflow 6

---

## Error Handling

| Situation | Action |
|-----------|--------|
| No cluster_id provided | Ask the user — never proceed without a specific cluster |
| No series found | Verify cluster ID with `get_promql_label_values`. Check region. |
| Empty result (no data) | Cluster is idle for that period. Widen time window. |
| `query_id` missing | Not all queries emit it. Filter by `normalized_sql` instead. |
| PromQL timeout | Reduce cardinality — fewer labels or shorter time range. |
| Range > 7 days | Split into multiple 7-day range queries. |
| `dsql` skill not available | Prompt user to install from `awslabs/agent-plugins` (plugin: `databases-on-aws`) |
