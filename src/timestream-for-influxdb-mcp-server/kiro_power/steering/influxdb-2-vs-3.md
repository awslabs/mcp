# InfluxDB 2 vs 3

Covers the differences between **Timestream for InfluxDB** (the InfluxDB 2.x engine) and **Timestream for InfluxDB 3** (the InfluxDB 3 engine). Load this when there is ambiguity about which version a user is on, or when planning a migration between the two.

## At-a-Glance Comparison

| Aspect | V2 (Timestream for InfluxDB) | V3 (Timestream for InfluxDB 3) |
|--------|----|----|
| Underlying engine | InfluxDB OSS 2.x branch (Go) | InfluxDB 3 (Rust) |
| Storage engine | TSM (Time-Structured Merge Tree) + TSI index | Apache Parquet on object storage |
| Query engine | InfluxDB built-in | Apache DataFusion |
| Storage layer | Influx IOPS Included volumes (local, block) | Amazon S3 (object storage) |
| Namespace | Organization → Bucket | Database → Table (no orgs) |
| Query language | Flux (primary), InfluxQL | SQL (primary), InfluxQL — **no Flux** |
| Query/network protocol | HTTP | Apache Arrow Flight SQL (gRPC) + HTTP |
| Default port | 8086 | 8181 |
| Write namespacing | `org` + `bucket` | `db` (database) |
| Cardinality | ~10M series practical limit | Virtually unlimited |
| **Deployment topology** | **Single node** (optionally + standby); **read-replica cluster** for multiple nodes | **Cluster only** (Core = single-node, Enterprise = multi-node) |
| Control-plane create op | `create-db-instance` or `create-db-cluster` | `create-db-cluster` only |
| Max storage | Up to 16 TiB provisioned | Elastic via S3 |
| Processing/automation | Tasks (Flux) | Processing engine (embedded Python VM) |
| Extra licensing | Read replicas add a license fee | Enterprise adds a per-node Marketplace license; Core has none |
| Table limit | No limit | For Core, 2,000 across all databases. For Enterprise, 10,000 across all databases |
| Bucket/database limit | 20, recommended for performance, not a hard limit | For core, 5. For Enterprise, 100 |

## Deployment Topology

This is the most commonly misunderstood difference. The two versions have fundamentally different deployment models.

### V2 — single node by default
A Timestream for InfluxDB **instance** (`create-db-instance`) is a **single node**. Availability options change this only slightly:

- **`SINGLE_AZ`** (default) — one node, one Availability Zone.
- **`WITH_MULTIAZ_STANDBY`** — a primary node plus a secondary **standby** in another AZ. The standby is for **failover only**; it does not serve reads or add throughput.

To get more than one serving node, you must create a **read-replica cluster** (`create-db-cluster` with `--deployment-type MULTI_NODE_READ_REPLICAS`). Only then does V2 run multiple nodes. **Without a read-replica cluster, V2 is a single node.**

### V3 — cluster only
Timestream for InfluxDB 3 is **always deployed as a cluster** (`create-db-cluster`). There is no single-instance API for V3. The cluster's topology is determined by the parameter group, not a `--deployment-type` flag (do **not** pass `--deployment-type` for V3):

- **Core** — a **single-node** cluster. Ingestion, querying, compaction, and the processing engine all run on one node and share compute. Core has **no dedicated compactor**, so it is best for recent data (typically the last 3–5 days). This can be adjusted by changing the `queryFileLimit` and `gen1Duration` configuration options in a cluster's parameter group. The default values of these options, `432` and 10 minutes, mean queries can access up to a maximum of 72 hours of data.
- **Enterprise** — a **multi-node** cluster, up to 15 nodes: 1–4 writer (ingest) nodes, 0–13 read-only (query) nodes, and 1 compactor node. Nodes can be assigned distinct roles to isolate ingest/query/compaction/processing. All multi-node deployments are spread across multiple AZs for availability.

**Summary:** V2 is single-node unless you build a read-replica cluster; V3 is only ever a cluster (single-node for Core, multi-node for Enterprise).

## Architecture & Storage

**V2** uses the InfluxDB 2.x **TSM** storage engine with a **TSI** (time-series index). Tags are indexed, which is what makes high cardinality expensive — every unique tag-value combination becomes a series key, and large indexes drive memory pressure and slow writes/queries. Practical guidance caps a V2 instance at **~10M series**. Storage is local **Influx IOPS Included** block volumes (up to 16 TiB).

**V3** is a ground-up redesign built on open formats:
- **Rust** core for performance.
- **Apache Arrow** for in-memory columnar processing (vectorized execution, predicate/projection pushdown).
- **Apache Parquet** for persisted columnar files.
- **Apache DataFusion** as the query optimizer/engine.
- **Apache Arrow Flight SQL** (gRPC) as the high-performance query protocol.
- **Amazon S3** as the core storage layer — 11 nines (99.999999999%) durability, multi-AZ, and effectively elastic capacity.

V3 also adds two in-memory caches that accelerate common patterns:
- **Last Value Cache (LVC)** — most recent value per field; millisecond "last point" lookups for dashboards.
- **Distinct Value Cache (DVC)** — unique tag/field values per table; fast metadata queries (e.g., listing host or sensor IDs).

## Query Languages

- **V2:** **Flux** is the primary language; **InfluxQL** is also supported, **SQL** is not.
- **V3:** **SQL** is the primary language (via DataFusion); a v1-compatible **InfluxQL** endpoint is provided for legacy apps. **Flux is not supported.**

There is **no automatic Flux-to-SQL conversion**. Migrating from V2 to V3 requires rewriting all Flux queries, tasks, and dashboards into SQL or InfluxQL.

## Data Model & API

- **V2** organizes data as **Organization → Bucket**. Writes specify `org` and `bucket`; default port **8086**.
- **V3** organizes data as **Database → Table** (no organizations). Tables are created automatically on first write (a measurement becomes a table). Writes specify `db`; data-plane auth uses the `Bearer` prefix; default port **8181**.
- **`422` HTTP status code meaning** - For v2, a status code of `422` means that some or all of the data was rejected. For v3, `422` means that writing the line protocol points would lead to the maximum number of databases, tables, columns, tags, or fields being exceeded.
- **`400` HTTP status code meaning** - For v2, a status code of `400` means that the `org` or `orgID` parameter doesn't match an existing organization. For v3, a status code of `400` means that some or all of the data was rejected.
**Backward compatibility:** V3 exposes v1- and v2-compatible write endpoints (including `/api/v2/write`), so existing line-protocol writers and Telegraf configs can keep writing without changes during a migration. Line protocol itself is unchanged across versions.

## Automation / Processing

- **V2** uses **Tasks** — scheduled Flux scripts for downsampling, alerting, and transforms.
- **V3** ships a **processing engine**: an embedded Python virtual machine that runs plugins on scheduled events or WAL-flush events (downsampling, alerting, anomaly detection) with zero-copy access to data. Timestream for InfluxDB 3 provides a curated, security-hardened set of plugins.
  - **Gotcha:** on multi-node Enterprise, scheduled triggers run on **every** node and can OOM small instances — target nodes with `node_spec` or scale up.

## Cost & Licensing

- **V2:** billed on instance hours + provisioned storage (per GiB) + data transfer. **Read replicas add a license fee**.
- **V3 Core:** compute + S3 storage only — **no license fee**.
- **V3 Enterprise:** compute + S3 storage **plus** an Enterprise license billed per node-hour via **AWS Marketplace** (InfluxData). The license is separate from AWS compute spend, and **EDP discounts do not apply** to Marketplace charges.

## Choosing / Migration Guidance

- **Choose V3** for high or unpredictable cardinality, SQL/BI integration, large historical retention (cheap S3), or when you need a multi-node solution for high ingest. V3 is also the forward path for workloads leaving Timestream for LiveAnalytics (in maintenance mode).
- **Stay on / choose V2** when you depend on **Flux**, existing v2 tooling/dashboards, or org/bucket semantics, and your cardinality stays well under ~10M series.
- **Migration checklist (V2 → V3):** rewrite Flux → SQL/InfluxQL; map orgs/buckets → databases/tables; switch port `8086` → `8181`; re-point writers (or use V3's v2-compatible write endpoint); re-provision as a cluster (Core or Enterprise).
- **Data migration tooling:** the engines share no storage format, so there is no snapshot/restore between them. Use the [**Amazon Timestream for InfluxDB v2 to v3 Migration Script**](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influxdb_v2_to_v3_migration), which automates `influx backup` → line-protocol translation (`influxd inspect export-lp`) → write to the V3 HTTP API (buckets → databases, measurements → tables). Full runbook: `influxdb3/migrations.md`.

## Retrieving tokens

To interact with your deployed Timestream for InfluxDB instance or cluster, creating buckets, executing queries, ingesting data, etc., using the InfluxDB v2 or v3 HTTP APIs, you must retrieve or create an InfluxDB token.

### V2

Once your v2 instance or cluster has been deployed, create a new operator token, using the [Influx v2 CLI](https://docs.influxdata.com/influxdb/v2/tools/influx-cli/?section=influxdb%252Fv2%252Ftools):

```shell
influx config create --config-name CONFIG_NAME1  --host-url "https://yourinstanceid.eu-central-1.timestream-influxdb.amazonaws.com:8086" --org [YOURORG]  --username-password [YOURUSERNAME] --active

influx auth create --org [YOURORG] --operator
```

### V3

After you have deployed a Timestream for InfluxDB v3 cluster, a secret in AWS Secrets Manager will be associated with your cluster. The ID of this secret will be returned as part of the `aws timestream-influxdb get-db-cluster` AWS CLI call and is visible in the AWS console.

Given the cluster ID, you can retrieve your token with the following command, replacing `<cluster ID>` with your cluster ID:
```shell
aws secretsmanager \
  get-secret-value \
  --secret-id READONLY-InfluxDB-auth-parameters-<cluster ID> \
  --query SecretString \
  --output text | jq -r '.token'
```

## Sources

- [What is Timestream for InfluxDB?](https://docs.aws.amazon.com/timestream/latest/developerguide/timestream-for-influxdb.html)
- [Amazon Timestream for InfluxDB 3](https://docs.aws.amazon.com/timestream/latest/developerguide/influxdb3.html)
- [Features and workflows with Amazon Timestream for InfluxDB 3](https://aws.amazon.com/blogs/database/features-and-workflows-with-amazon-timestream-for-influxdb-3/)
- [Timestream for InfluxDB 3 workload analysis and best practices](https://aws.amazon.com/blogs/database/timestream-for-influxdb-3-workload-analysis-and-best-practices/)
- [InfluxDB v2 HTTP API](https://docs.influxdata.com/influxdb/v2/api/?section=influxdb%252Fv2%252Fapi)
- [InfluxDB v3 HTTP API](https://docs.influxdata.com/influxdb3/enterprise/api/)
