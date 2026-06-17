# Troubleshooting in InfluxDB 2

Version-specific errors for **Timestream for InfluxDB** (the InfluxDB 2.x engine) and how
to resolve them. For cross-cutting connection/authorization problems (port, token prefix,
networking, namespace), start with the parent [troubleshooting.md](../troubleshooting.md).
For terminology, see [glossary.md](../glossary.md).

> V2 quick facts: default port **8086**, auth header `Authorization: Bearer <token>`,
> write/query namespace is `org` + `bucket`, Flux is primary (InfluxQL also supported).
> See [influxdb-2-vs-3.md](../influxdb-2-vs-3.md).

## Provisioning (instances & clusters)

- **Cluster/instance stuck in `CREATING` or `FAILED`** — run `get-db-cluster` /
  `get-db-instance` to read `status`. If `FAILED`: verify subnets and security groups are
  valid and in the same VPC, the security group allows inbound on **8086**, then delete
  and recreate with corrected parameters. Check CloudTrail for the create-event error.
- **`ValidationException` on `--password`** — the password accepts only `[a-zA-Z0-9]+`;
  special characters are rejected. Omit it to have one auto-generated and stored in
  Secrets Manager.
- **Parameter group name rejected** — `--name` for `create-db-parameter-group` accepts
  only `[a-zA-Z0-9]+`. Reference the group by its **ID** in
  `--db-parameter-group-identifier`.
- **`ResourceNotFoundException` on `--db-cluster-id`** — use the service-generated
  `dbClusterId` (from the create response or `list-db-clusters`), not the name you chose.

## Writing / ingestion

Status codes for the v2 write API (see the
[InfluxDB v2 write troubleshooting docs](https://docs.influxdata.com/influxdb/v2/write-data/troubleshoot/)):

- **`400` Bad request** — malformed line protocol; **all request data is rejected** and
  the response body contains the first malformed line. Validate syntax (see
  [line-protocol.md](../line-protocol.md)).
- **`401` Unauthorized** — missing/malformed `Authorization: Bearer` header or insufficient
  token permissions.
- **`404` Not found** — a resource such as the `org` or `bucket` wasn't found.
- **`413` Request entity too large** — reduce batch size.
- **`422` Unprocessable entity** — well-formed request, but some/all points were rejected
  for **semantic** reasons (schema/field-type conflict or retention-policy violation).
  Non-rejected points are still ingested (partial write); field types are **locked on
  first write**, so keep them consistent.
- **`503` Service unavailable** — server temporarily can't accept writes; retry per the
  `Retry-After` header.
- **Replica lag / slow writes** — batch **5,000+ points per request** instead of many
  tiny writes (see [`gotchas.md`](./gotchas.md)).

## Querying (Flux / InfluxQL)

Patterns and endpoints: [`query-guide.md`](./query-guide.md).

- **InfluxQL returns "no databases" / empty results** — InfluxQL needs a **DBRP mapping**
  (database/retention-policy → bucket). Without it, queries find nothing. Configure the
  mapping, or use Flux.
- **Queries are slow** — narrow the `range()`, filter on **tags before fields** (tags are
  indexed), use `aggregateWindow` for standard aggregations, and use `last()` after a
  short range for "current value" lookups (see the Query Performance section of
  [`query-guide.md`](./query-guide.md)).
- **Queries time out or OOM under load** — tune `queryConcurrency`,
  `queryMaxMemoryBytes`, and `httpReadTimeout` via the parameter group.

## Schema & cardinality

See [`schema-design.md`](./schema-design.md) and [`gotchas.md`](./gotchas.md).

- **Slow queries, high memory, compaction stalls** — classic **high series cardinality**.
  The TSM/TSI engine degrades above **~10M series**. Audit tags for high-uniqueness values
  (e.g. request IDs) and move them to **fields** instead of tags.
- **Expecting very high cardinality (1M+ unique tag combos)** — consider **V3** instead,
  which has no practical cardinality limit (see [influxdb-2-vs-3.md](../influxdb-2-vs-3.md)).

## Parameters & storage

See [`gotchas.md`](./gotchas.md).

- **Parameter change didn't take effect** — parameter groups are **immutable** and changes
  require a **reboot**. Create a new group and reassign with
  `update-db-cluster --db-parameter-group-identifier NEW_ID` (reboots automatically).
  There is no `UpdateDbParameterGroup` operation.

## Cost

- **Unexpectedly high bill** — V2 **read replicas add a license fee** on top of base
  instance cost; regional pricing multipliers apply (see [`gotchas.md`](./gotchas.md)).

## Migrating to V3

Planning a move off V2 to V3? See [influxdb3/migrations.md](../influxdb3/migrations.md) and
[influxdb-2-vs-3.md](../influxdb-2-vs-3.md) — note there is no turnkey query migration and
Flux must be rewritten to SQL/InfluxQL.

## Health check

`GET /health` is unauthenticated — use it to confirm the engine is reachable before
chasing auth or query issues:
```shell
curl https://<endpoint>:8086/health
```
