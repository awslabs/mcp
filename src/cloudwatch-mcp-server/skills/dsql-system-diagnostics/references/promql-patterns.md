# PromQL Query Patterns for DSQL Diagnostics

Reusable PromQL templates for diagnosing Aurora DSQL via `db.active_sessions.avg`. Replace `CLUSTER_ID` with the actual `@resource.aws.auroradsql.cluster_id` value.

---

## Discovery Queries

### List available clusters

```promql
get_promql_label_values(metric="db.active_sessions.avg", label="@resource.aws.auroradsql.cluster_id")
```

### List wait events on a cluster

```promql
get_promql_label_values(metric="db.active_sessions.avg", label="wait_event", matchers='@resource.aws.auroradsql.cluster_id="CLUSTER_ID"')
```

### List applications connecting

```promql
get_promql_label_values(metric="db.active_sessions.avg", label="application_name", matchers='@resource.aws.auroradsql.cluster_id="CLUSTER_ID"')
```

### List IAM roles connecting

```promql
get_promql_label_values(metric="db.active_sessions.avg", label="iam_role_arn", matchers='@resource.aws.auroradsql.cluster_id="CLUSTER_ID"')
```

---

## Instant Queries

### Total AAS

```promql
execute_promql_query(query='sum(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"})')
```

### AAS by wait event

```promql
execute_promql_query(query='sum by (wait_event)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"})')
```

### Top 5 SQL by AAS

```promql
execute_promql_query(query='topk(5, sum by (normalized_sql, query_id)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"}))')
```

### Top 5 SQL for a specific wait event

```promql
execute_promql_query(query='topk(5, sum by (normalized_sql, query_id)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID", wait_event="WAIT_EVENT"}))')
```

### Top 5 IAM roles

```promql
execute_promql_query(query='topk(5, sum by (iam_role_arn)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"}))')
```

### Top 5 applications

```promql
execute_promql_query(query='topk(5, sum by (application_name)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"}))')
```

### AAS for a specific query ID

```promql
execute_promql_query(query='sum by (wait_event)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID", query_id="QUERY_ID"})')
```

### Cross-cluster comparison

```promql
execute_promql_query(query='sum by (@resource.aws.auroradsql.cluster_id)(db.active_sessions.avg)')
```

---

## Range Queries

**Step guidelines:** 60s (< 1h), 300s (1–6h), 900s (6–24h), 3600s (> 24h).

### AAS by wait event over time

```promql
execute_promql_range_query(
  query='sum by (wait_event)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"})',
  start="START_TIME", end="END_TIME", step="60s"
)
```

### Total AAS over time

```promql
execute_promql_range_query(
  query='sum(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"})',
  start="START_TIME", end="END_TIME", step="60s"
)
```

### Top SQL over time

```promql
execute_promql_range_query(
  query='topk(5, sum by (normalized_sql, query_id)(db.active_sessions.avg{@resource.aws.auroradsql.cluster_id="CLUSTER_ID"}))',
  start="START_TIME", end="END_TIME", step="300s"
)
```

### Commit wait trend

```promql
execute_promql_range_query(
  query='sum({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID", wait_event="Commit"})',
  start="START_TIME", end="END_TIME", step="60s"
)
```

---

## Temporal Comparison Patterns

### Current hour vs same hour yesterday vs same hour last week

```promql
# Current hour
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="CURRENT_HOUR_START", end="CURRENT_HOUR_END", step="60s"
)

# Same hour yesterday (24h ago)
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="YESTERDAY_HOUR_START", end="YESTERDAY_HOUR_END", step="60s"
)

# Same hour last week (168h ago)
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="LAST_WEEK_HOUR_START", end="LAST_WEEK_HOUR_END", step="60s"
)
```

### Deployment regression detection

```promql
# Compare wait event distribution before and after deploy
execute_promql_range_query(
  query='sum by (wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="BEFORE_DEPLOY", end="AFTER_DEPLOY", step="60s"
)
```

---

## Diagnostic Scenarios

### Has the cluster's behavior changed?

Compare the wait event distribution across temporal baselines. Flag any wait event where
the proportion of total AAS changed by >30% vs either baseline.

### Which workload drives an anomaly?

```promql
execute_promql_query(query='sum by (iam_role_arn, wait_event)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})')
```

### Commit analysis — volume vs conflicts

Use standard CloudWatch metrics alongside PromQL:
```
# PromQL: Commit wait AAS trend
execute_promql_range_query(
  query='sum({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID", wait_event="Commit"})',
  start="START_TIME", end="END_TIME", step="60s"
)

# CW Metrics: TotalTransactions and OccConflicts (detect conflict rate vs volume)
get_metric_data(namespace="AuroraDSQL", metric_name="TotalTransactions", dimensions=[{name:"ClusterId", value:"CLUSTER_ID"}])
get_metric_data(namespace="AuroraDSQL", metric_name="OccConflicts", dimensions=[{name:"ClusterId", value:"CLUSTER_ID"}])
```

### SequentialScanRead growth — identify query

```promql
execute_promql_query(query='topk(5, sum by (normalized_sql, query_id)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID", wait_event="SequentialScanRead"}))')
```

### Client-side bottleneck (idle in transaction)

```promql
execute_promql_query(query='sum by (application_name, iam_role_arn)({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID", wait_event="ClientRead"})')
```

### Idle or sporadic cluster detection

```promql
# Look for gaps in the time series — missing timestamps indicate no active sessions
execute_promql_range_query(
  query='sum({__name__="db.active_sessions.avg", "@resource.aws.auroradsql.cluster_id"="CLUSTER_ID"})',
  start="NOW-24h", end="NOW", step="300s"
)
```
