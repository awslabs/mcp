# Glossary

Terms used across Amazon Timestream for InfluxDB (v2 and v3). Where a term differs
between versions, the version is noted. For a fuller treatment of version
differences, see [influxdb-2-vs-3.md](./influxdb-2-vs-3.md).

## Version & terminology map

InfluxDB 2 (Timestream for InfluxDB) and InfluxDB 3 (Timestream for InfluxDB 3)
name several concepts differently:

| InfluxDB 2 | InfluxDB 3 | Notes |
|---|---|---|
| Organization (`org`) | — (no orgs) | V3 has no organization concept |
| Bucket | Database (`db`) | Top-level write/query namespace |
| Measurement | Table | A measurement becomes a table in V3 (auto-created on first write) |
| Flux / InfluxQL | SQL / InfluxQL | V3 has no Flux; SQL is primary |
| Tasks (Flux) | Processing engine (Python) | Scheduled automation |
| TSM + TSI | Parquet on S3 + DataFusion | Storage + query engine |
| Port 8086 | Port 8181 | Default endpoint port |

## Data model

- **Line protocol** — InfluxDB's text format for writing data:
  `measurement,tag=val field=1.0 timestamp`. Unchanged across versions. See
  [line-protocol.md](./line-protocol.md).
- **Point** — a single data record: a measurement + tag set + field set + timestamp.
- **Measurement** (V2) / **Table** (V3) — logical container for points of the same
  kind (e.g. `cpu`).
- **Tag** — indexed key/value metadata (e.g. `host=server01`), used for filtering and
  grouping. High tag cardinality is the main driver of V2 performance limits.
- **Tag set** — the unique combination of all tag key/values on a point.
- **Field** — the measured value(s) (e.g. `usage=42.0`). Not indexed. Field type is
  inferred on first write and then locked.
- **Field set** — all field key/values on a point.
- **Timestamp** — the time of a point; default precision is nanoseconds. Always specify
  precision explicitly to avoid silent shifts.
- **Series** — a unique combination of measurement + tag set + field key.
- **Series cardinality** — the number of unique series. V2 (TSM/TSI) degrades above
  ~10M series; V3 is effectively unbounded.

## Namespaces & auth

- **Organization (org)** — V2-only top-level tenant that groups buckets.
- **Bucket** — V2 named container for data with a retention period; the write/query
  target (`bucket`).
- **Database (db)** — V3 top-level namespace (replaces org/bucket).
- **Retention period / policy** — how long data is kept before it expires.
- **Token** — data-plane credential. V2 and V3 use `Authorization: Bearer <token>`.
  Operator/all-access tokens differ in scope.
- **Control plane vs data plane** — the control plane (create/manage instances and
  clusters) uses AWS SigV4/IAM; the data plane (read/write) is authorized only by the
  engine token (IAM does not gate it).

## Engines & storage

- **TSM (Time-Structured Merge Tree)** — V2's on-disk storage engine.
- **TSI (Time-Series Index)** — V2's index over tags; large indexes drive memory use
  and the cardinality limit.
- **Apache Parquet** — V3's columnar on-disk (S3) file format.
- **Apache DataFusion** — V3's SQL query engine/optimizer.
- **Apache Arrow / Arrow Flight SQL** — Arrow is V3's in-memory columnar format; Flight
  SQL is its high-performance gRPC query protocol.
- **WAL (write-ahead log)** — durability buffer for recent writes before they are
  persisted to Parquet.
- **Compaction** — background merging of files for query efficiency; V3 Enterprise can
  use a dedicated compactor node.
- **Last Value Cache (LVC)** — V3 cache of the most recent value per field (fast
  "last point" lookups).
- **Distinct Value Cache (DVC)** — V3 cache of unique tag/field values (fast metadata
  lookups, e.g. template-variable queries).

## Query & automation

- **Flux** — V2's functional data-scripting language (primary in V2; absent in V3).
- **InfluxQL** — SQL-like legacy language; supported in both V2 and V3 (via a
  compatibility endpoint).
- **SQL** — V3's primary query language (DataFusion).
- **Tasks** — V2 scheduled Flux scripts (downsampling, alerting).
- **Processing engine** — V3's embedded Python VM that runs plugins on schedule, HTTP invocation, or on
  WAL-flush events (replaces V2 Tasks).
- **Telegraf** — InfluxData's plugin-based metrics collection agent; writes line
  protocol to either version.

## Deployment

- **Instance** — V2 single-node deployment (`create-db-instance`); optionally with a
  multi-AZ standby (failover only, does not serve reads).
- **Read-replica cluster** — V2 multi-node deployment that adds read-serving nodes
  (adds a license fee).
- **Cluster** — V3's only deployment shape (`create-db-cluster`).
- **Core** — single-node V3 cluster; no dedicated compactor; best for
  recent data. Uses an open-source binary with more limitations than Enterprise.
- **Enterprise** — multi-node V3 cluster (up to 15 nodes) with
  role separation; adds a per-node AWS Marketplace license.
- **Parameter group** — immutable named set of engine parameters; change by creating a
  new group and reassigning it (which triggers a reboot).
