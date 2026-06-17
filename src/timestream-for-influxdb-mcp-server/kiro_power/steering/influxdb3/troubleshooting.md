# Troubleshooting in InfluxDB 3

Version-specific errors for **Timestream for InfluxDB 3** and how to resolve them. For
cross-cutting connection/authorization problems (port, token prefix, networking,
namespace), start with the parent [troubleshooting.md](../troubleshooting.md). For
terminology, see [glossary.md](../glossary.md).

> V3 quick facts: default port **8181**, auth header `Authorization: Bearer <token>`,
> write/query namespace is `db` (database), SQL is primary (**no Flux**). See
> [influxdb-2-vs-3.md](../influxdb-2-vs-3.md).

## Cluster provisioning

V3 is **cluster-only** (`create-db-cluster`; do not pass `--deployment-type`). Topology
is set by the parameter group (`InfluxDBV3Core` = single node, `InfluxDBV3Enterprise` =
multi-node).

- **Cluster stuck in `CREATING` or `FAILED`** — run `get-db-cluster` to read `status`.
  If `FAILED`: verify subnets and security groups are valid and in the same VPC, the
  security group allows inbound on **8181**, then delete and recreate with corrected
  parameters. Check CloudTrail for the `CreateDbCluster` event error details.
- **Passing the cluster name instead of the cluster ID** — `--db-cluster-id` expects the
  service-generated `dbClusterId` (from the create response or `list-db-clusters`), not
  the name you chose. Using the name returns `ResourceNotFoundException`.
- **Parameter group name rejected** — `--name` for `create-db-parameter-group` accepts
  only `[a-zA-Z0-9]+` (no hyphens/underscores). Reference the group by its **ID** in
  `--db-parameter-group-identifier`.

## Writing / ingestion

The native v3 write API (`/api/v3/write_lp`) returns these status codes (see the
[InfluxDB 3 write troubleshooting docs](https://docs.influxdata.com/influxdb3/core/write-data/troubleshoot/)):

- **`400` Bad request** — some or all of the data was rejected. With partial writes
  enabled (`accept_partial`, the default), valid points are still ingested and the
  response body lists the rejected lines (up to 100). **Field type conflicts** surface
  here: field types are inferred and **locked on first write**, so points whose field
  types don't match existing data are rejected. Validate syntax (see
  [line-protocol.md](../line-protocol.md)).
- **`401` Unauthorized** — missing/malformed `Authorization` header or a token without
  write permission.
- **`404` Not found** — database not found; verify the `db` name.
- **`422` Unprocessable entity** - Writing the line protocol points would lead to the maximum number of databases, tables, columns, tags, or fields being exceeded.
- **`503` Service unavailable** — the server is temporarily rejecting writes; retry per
  the `Retry-After` header.
- **Replica lag / slow writes** — caused by tiny writes from many concurrent
  writers. Batch **5,000+ points per request** (see [`gotchas.md`](./gotchas.md)).

## Querying (SQL / InfluxQL)

Patterns and endpoints: [`query-guide.md`](./query-guide.md).

- **`SELECT ... GROUP BY time(...)` fails** — that's InfluxQL syntax. In SQL use
  `date_bin($__interval, time)` with `GROUP BY` on the bucketed column.
- **Flux query rejected** — V3 has **no Flux**. Rewrite as SQL or InfluxQL; there is no
  automatic conversion (see [migrations.md](./migrations.md)).
- **InfluxQL function returns an error** — some InfluxQL functions aren't implemented in
  V3, including the `SAMPLE()` selector and **all** technical/predictive-analysis
  functions (e.g. `HOLT_WINTERS()`). The `SLIMIT`/`SOFFSET` clauses and cardinality
  metaqueries are also unsupported. Test before relying on them; prefer SQL. See
  [InfluxQL feature support](https://docs.influxdata.com/influxdb3/core/reference/influxql/feature-support/).
- **Queries time out or OOM under load** — increase the query memory pool
  (`execMemPoolBytes`) and the number of DataFusion query threads (`dataFusionNumThreads`)
  via the parameter group (see [`parameters.md`](./parameters.md)).

## Schema, cardinality & tables

See [`schema-design.md`](./schema-design.md) and [`gotchas.md`](./gotchas.md).

- **Hitting the ~10,000-tables limit (across all databases)** — this is the default cap
  (`--num-table-limit`, not exposed in the Timestream parameter group). Revisit your
  table/measurement split first; raising it has compaction/query-performance implications.
- **Unexpected field-type errors on write** — see `400` above; the first write fixes the
  type.

## Parameters & tuning

See [`parameters.md`](./parameters.md) and [`gotchas.md`](./gotchas.md).

- **Parameter change didn't take effect** — parameter groups are **immutable**. Create a
  new group and reassign it with `update-db-cluster --db-parameter-group-identifier
  NEW_ID` (this reboots). There is no `UpdateDbParameterGroup` SDK operation.
- **Need more query parallelism / throughput** — there is **no IO-threads parameter** in
  the v3 parameter group. Tune `dataFusionNumThreads` (DataFusion query threads) and the
  related `dataFusionRuntime*` settings, and `execMemPoolBytes` for memory.

## Processing engine, compaction & integrations

- **OOM (`HashAggSpill` / Memory Exhausted) on Enterprise** — scheduled processing-engine
  triggers run on **every** node. Target nodes with `node_spec` or scale up
  (see [`gotchas.md`](./gotchas.md)).
- **Compactor node OOM / growing file counts** — monitor `system.parquet_files`; consider
  a dedicated compactor node (Enterprise).
- **No QuickSight connector** — use **Grafana with Flight SQL / the InfluxDB SQL data
  source** instead (see [`dashboard-guide.md`](./dashboard-guide.md)).

## Health check

`GET /health` is unauthenticated — use it to confirm the engine is reachable before
chasing auth or query issues:
```shell
curl https://<endpoint>:8181/health
```

## Core vs. Enterprise

Timestream for InfluxDB Core has significant limitations compared to Enterprise. Specifically:

| Core                                    | Enterprise                                                           |
|-----------------------------------------|----------------------------------------------------------------------|
| Single node                             | Up to 15 total nodes                                                 |
| Default maximum query range of 72 hours | No limit on query range                                              |
| Maximum of 5 databases                  | Maximum of 100 databases                                             |
| Maximum of 2,000 total tables           | Maximum of 10,000 total tables                                       |
