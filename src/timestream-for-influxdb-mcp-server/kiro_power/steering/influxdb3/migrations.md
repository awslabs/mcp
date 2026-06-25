# Migrating to Timestream for InfluxDB 3

How to migrate **into** Timestream for InfluxDB v3 from common sources. Pick the section that
matches your source system. For the differences
between the engines, see [`influxdb-2-vs-3.md`](../influxdb-2-vs-3.md).

> **Migrating to V2 instead?** See [`influxdb2/migrations.md`](../influxdb2/migrations.md).

## What carries over

V3 is a different engine from V2/OSS/v1: storage is **Apache Parquet on S3**, the data model
is **Database → Table** (no orgs/buckets), and the query language is **SQL/InfluxQL — there is
no Flux**. Consequences for every migration path:

- **Time-series data** moves via **line protocol**. V3 exposes **v1- and v2-compatible write
  endpoints** (`/api/v2/write` on port **8181**), so any tool that writes line protocol to V2
  can target V3 by re-pointing the URL.
- **Metadata does *not* port.** Dashboards, **Flux** tasks, and v2 key-value data have no V3
  equivalent. Rewrite Flux queries/tasks into **SQL or InfluxQL**, and replace Flux tasks with
  the V3 **processing engine** (embedded Python plugins) for downsampling/alerting.
- **Namespace mapping:** V2 `org`/`bucket` (and v1 database) → V3 **database**; each source
  measurement → a V3 **table** (created automatically on first write).

| Source | Tooling | Mechanism |
|--------|---------|-----------|
| **Timestream for LiveAnalytics** | [`tools/python/liveanalytics_influxdb3_migration_plugin`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_influxdb3_migration_plugin) (`influxdb_version: v3`) | Unload to S3 → ingest using processing engine → validate |
| **Timestream for InfluxDB v2** | [`tools/python/influxdb_v2_to_v3_migration`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influxdb_v2_to_v3_migration) | `influx backup` → translate to line protocol → write to V3 HTTP API |
| **InfluxDB v1** | No direct tool | Two-hop: `influxd upgrade` → `export-lp` → write line protocol to V3 |
| **InfluxDB OSS 2.x** | Export line protocol | Write line protocol to V3's v2-compatible endpoint |

---

## From Timestream for LiveAnalytics

Use the same [**LiveAnalytics migration tooling**](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts)
as the V2 path — it targets **both V2 and V3**. The four stages are identical (unload to S3 in
Parquet → Athena transform to line protocol → ingest → validate), orchestrated by
`main.py --config <config.yaml>` in either `batch` or `live_replication` mode.

To target **V3**, make two changes versus the V2 setup:

1. Set `influxdb_version: v3` in the config (remember *buckets* become *databases*).
2. Configure the V3 endpoint via environment variables — port **8181**, and **omit
   `INFLUXDB_V2_ORG`** (V3 has no organizations); ingestion uses V3's V2-compatible write API:
   ```shell
   export INFLUXDB_V2_URL="https://<your-v3-cluster>:8181"
   export INFLUXDB_V2_TOKEN="<token>"
   ```

Cardinality is far less of a concern on V3 than on V2 (Parquet/columnar storage, no TSI), so
the strict ~10M-series ceiling does not apply — though a sensible tag/field design still helps
query performance.

> **Large datasets (≥1 TB):** line-protocol ingestion can be slow at terabyte scale. A
> Parquet-based V3 ingestion path is in development; if you are moving terabytes, check the
> repo for its availability before committing to the line-protocol route.

For the end-to-end live cutover (continuous replication → gradual application cutover →
cleanup), follow the
[Live Migration Guide](https://github.com/awslabs/amazon-timestream-tools/blob/mainline/tools/python/liveanalytics_migration_scripts/targets/timestream_for_influxdb/live_migration_guide.md).

---

## From Timestream for InfluxDB v2

Use the [**Amazon Timestream for InfluxDB v2 to v3 Migration Script**](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influxdb_v2_to_v3_migration)
(`influxdb_v2_to_v3_migration.py`). It is the purpose-built, turnkey path between the two
managed engines and runs the whole migration end to end:

1. **Backs up** the selected V2 buckets to local storage with `influx backup` (the InfluxDB v2 CLI).
2. **Translates** the backup to line protocol with the InfluxDB v2 daemon (`influxd inspect export-lp`).
3. **Writes** the line protocol to V3 via the [InfluxDB v3 HTTP API](https://docs.influxdata.com/influxdb3/enterprise/api/v3/).

Buckets map to **databases** and measurements map to **tables** during the migration.

The script is available **standalone**, or as an **automated solution** that provisions an EC2
instance with the script and all prerequisites pre-installed — see the
[`automated_deployment/` README](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influxdb_v2_to_v3_migration/automated_deployment).

### Prerequisites
- **Python 3.13+** (3.12 will not work).
- The **InfluxDB v2 CLI** installed, and the **InfluxDB v2 daemon (`influxd`) on your `PATH`**.
  The daemon does **not** need to be running — it is used in isolation to extract line protocol
  (extraction cannot be done over a network, which is why the daemon is required locally).
- Network connectivity to both instances — V2 on **8086** (`influx ping --host`), V3 on **8181**
  (`curl <v3-url>/health -H "Authorization: Bearer <token>"`).
- Enough local disk to hold all migrated data **uncompressed** (backed up under `~/engine`).
- A **V2 operator token** and a **V3 token** (the V3 token lives in the AWS Secrets Manager
  secret associated with the instance). Store both in a single Secrets Manager secret:
  ```shell
  aws secretsmanager create-secret \
    --region us-west-2 \
    --name influxdb_v2_to_v3_migration \
    --secret-string '{"INFLUXDB_V2_TOKEN": "<v2 token>", "INFLUXDB_V3_TOKEN": "<v3 token>"}'
  ```

### Run the migration
Provide the source/destination URLs, the buckets (or whole orgs) to migrate, and the secret name:
```shell
python3.13 influxdb_v2_to_v3_migration.py \
    --source-url "https://<v2-instance>:8086" \
    --destination-url "https://<v3-cluster>:8181" \
    --source-buckets-and-orgs "bucket-one:org-one,bucket-two:org-two" \
    --tokens-secret-name "influxdb_v2_to_v3_migration"
```
Use `--source-orgs` instead of `--source-buckets-and-orgs` to migrate **all** buckets from the
named organizations. When finished, remove the local backup (`rm -rf ~/engine`).

> **Already have a backup?** A companion `influxdb_v3_ingestion.py` script ingests pre-backed-up
> V2 data (organized under `engine/data/<bucket-id>/<bucket>.lp`) straight into V3 — useful if
> you have already run `influx backup` + `export-lp` yourself.

> **Cutoff behavior:** only points written **before the migration begins** are migrated; points
> written during or after are not (a consequence of how the V2 CLI backup works). For a live
> cutover, dual-write or replay the gap after the bulk migration completes.

### Verify
Buckets become databases and measurements become tables, so compare counts per table. On V2,
count a measurement with Flux (`from(bucket:"...") |> range(start: 0) |> filter(...) |> group() |> count()`)
or `wc -l ~/engine/data/<bucket-id>/<bucket>.lp`; on V3, run `SELECT COUNT(*) FROM <table>` for
each table in the database.

> The same script can also migrate **V2 → V2** (e.g. into a read-replica cluster, which does not
> support `backup`/`restore`) by passing `--destination-org <existing org>`.

---

## From InfluxDB v1

There is no direct v1 → V3 tool. Take a **two-hop** approach:

1. **Upgrade and export v1 to line protocol** exactly as in the
   [v1 → v2 path](../influxdb2/migrations.md#from-influxdb-v1): `influxd upgrade` to the 2.x
   on-disk format, then `influxd inspect export-lp` per bucket (compressed).
2. **Write the line protocol to V3** through its **v2-compatible write endpoint** (port 8181,
   `Authorization: Bearer <token>`, no org). You can re-point the Timestream
   [`influxdb_ingestion.py`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts/targets/timestream_for_influxdb/ingestion)
   script at the V3 endpoint (set `INFLUXDB_V2_URL` to the `:8181` URL, omit
   `INFLUXDB_V2_ORG`), since V3 accepts the V2 write API.

Alternatively, migrate **v1 → managed V2 first** (see [`influxdb2/migrations.md`](../influxdb2/migrations.md))
and then run the **[V2 → V3 migration script](#from-timestream-for-influxdb-v2)** above — useful
if you also want a V2 instance, or want to validate on V2 before going to V3.

---

## From InfluxDB OSS 2.x

The AWS [`influx-migration`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influx-migration)
script uses **backup/restore**, which is **V2-only** — it cannot target V3. For V3:

1. **Export** OSS 2.x data to line protocol locally (`influxd inspect export-lp`, since you
   control the host), or query it out as a DataFrame with the v2 client.
2. **Write** to V3's v2-compatible endpoint (`/api/v2/write` on 8181), or use the InfluxDB 3
   Python client's `write_file()` / `write_dataframe()`.

Note again that **dashboards and Flux tasks do not carry over** — rebuild them as SQL/InfluxQL
and processing-engine plugins on V3.

---

## Validate (any source)
After loading, compare per-table row counts and cardinality between source and target, and
spot-check a few time ranges (`SELECT count(*)`, min/max timestamps, sample rows) before
decommissioning the source. Note that `SELECT count(*)` is an expensive query and if the data range
hasn't reached compaction then a timeout may occur.

## AWS migration tools and documentation
- **Timestream for InfluxDB v2 → v3** — [Amazon Timestream for InfluxDB v2 to v3 Migration Script](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influxdb_v2_to_v3_migration) (standalone or [automated EC2 deployment](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influxdb_v2_to_v3_migration/automated_deployment)).
- **Timestream for LiveAnalytics → Timestream for InfluxDB 3** — [LiveAnalytics migration tooling](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts) (set `influxdb_version: v3`) and its [Timestream for InfluxDB target guide](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts/targets/timestream_for_influxdb).
- **InfluxDB v1 → v2 (first hop)** — [InfluxDB v1 to v2 migration guide](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/guides/influxdb_v1_to_v2_migration).
- **Other migration tools and guides** — see the [awslabs/amazon-timestream-tools](https://github.com/awslabs/amazon-timestream-tools) repository.
- **Service documentation** — [Amazon Timestream for InfluxDB 3 developer guide](https://docs.aws.amazon.com/timestream/latest/developerguide/influxdb3.html), [Features and workflows with Amazon Timestream for InfluxDB 3](https://aws.amazon.com/blogs/database/features-and-workflows-with-amazon-timestream-for-influxdb-3/), and the [InfluxDB v3 compatibility (v1/v2) write APIs](https://docs.influxdata.com/influxdb3/enterprise/write-data/compatibility-apis/).
