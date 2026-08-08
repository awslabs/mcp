# Migrating to Timestream for InfluxDB v2

How to migrate **into** Timestream for InfluxDB v2 from common
sources. Pick the section that matches your source system. All of the tooling referenced
here lives in the [awslabs/amazon-timestream-tools](https://github.com/awslabs/amazon-timestream-tools)
repository.

> **Migrating off V2 to V3 instead?** See [`influxdb3/migrations.md`](../influxdb3/migrations.md).
> For the differences between the engines, see [`influxdb-2-vs-3.md`](../influxdb-2-vs-3.md).

## Source matrix

| Source | Tooling | Mechanism |
|--------|---------|-----------|
| InfluxDB **OSS 2.x** (self-managed) | [`tools/python/influx-migration`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influx-migration) | Backup/restore + v2 API (also moves dashboards, tasks, users) |
| InfluxDB **v1** | [`guides/influxdb_v1_to_v2_migration`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/guides/influxdb_v1_to_v2_migration) | `influxd upgrade` → `export-lp` → ingest |
| **Timestream for LiveAnalytics** | [`tools/python/liveanalytics_migration_scripts`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts) | Unload → transform to line protocol → ingest → validate |

---

## From InfluxDB OSS 2.x

This is the most direct path: both source and target run the same 2.x engine, so buckets,
dashboards, tasks, users, and other key-value data can all move across. Use the AWS
**InfluxDB migration script** ([`tools/python/influx-migration`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influx-migration),
`influx_migration.py`), which drives the Influx CLI `backup`/`restore` flow and the v2 API.

**Prerequisites**
- A machine (Linux/macOS/Windows) with Python 3.7+, the [Influx CLI](https://docs.influxdata.com/influxdb/v2/tools/influx-cli/) on `PATH`, and the `influxdb_client` + `boto3` Python libraries.
- Source operator token in `INFLUX_SRC_TOKEN`; destination (Timestream for InfluxDB) operator token in `INFLUX_DEST_TOKEN`.
- Network access to both source and destination.
- Enough local disk for the export, **or** an S3 bucket mounted via [Mountpoint for S3](https://aws.amazon.com/s3/features/mountpoint/)/rclone (`--s3-bucket`) to avoid local storage pressure.

**Migrate a single bucket**
```shell
python3 influx_migration.py \
    --src-host  https://<source endpoint>:8086 \
    --src-bucket <source bucket> \
    --dest-host https://<destination endpoint>:8086 \
    --dest-bucket <new bucket name>
```

**Migrate everything** (buckets, dashboards, tasks, users, tokens, key-value data):
```shell
python3 influx_migration.py \
    --src-host  https://<source>:8086 \
    --dest-host https://<your-instance>.timestream-influxdb.amazonaws.com:8086 \
    --full
```

Other useful flags: `--src-org`/`--dest-org`, `--csv` (CSV instead of native backup),
`--s3-bucket` (offload the backup to S3), `--retry-restore-dir` (resume). Run
`python3 influx_migration.py -h` for the full list.

**Validate** by listing buckets (`influx bucket list`) and counting records on the
destination (`SELECT COUNT(*) ...` via `influx v1 shell`, or a Flux `... |> count()`).

**Near-zero-downtime (live) migration:** the script itself incurs downtime while data
copies and while clients are re-pointed. For a live cutover, front both databases with an
**API Gateway → Kinesis → Lambda** dual-write pipeline (with endpoints held in Secrets
Manager), seed the target with a `--full` run, then flip the read endpoint once the target
catches up. Full architecture and Lambda samples:
[Use the AWS InfluxDB migration script to migrate your InfluxDB OSS 2.x data to Amazon Timestream for InfluxDB](https://aws.amazon.com/blogs/database/use-the-aws-influxdb-migration-script-to-migrate-your-influxdb-oss-2-x-data-to-amazon-timestream-for-influxdb/).

## From InfluxDB v1

There is no v1 write/restore path into the managed service, so v1 data has to be **upgraded
to the 2.x on-disk format first, exported to line protocol, then ingested**. The
[`influxdb_v1_to_v2_migration` guide](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/guides/influxdb_v1_to_v2_migration)
documents this for **read-replica clusters**, which is the case that *requires* line protocol
ingestion — read replicas do not support `restore`.

> If your target is a **single V2 instance** (not a read-replica cluster), the simpler path
> is to `influxd upgrade` locally and then use the **OSS 2.x migration script above** (native
> backup/restore is far more efficient than ingesting line protocol). Use the line-protocol
> route below when the target is a read-replica cluster.

1. **Upgrade v1 → 2.x on-disk format** with the InfluxDB 2 daemon (this copies data to a new
   directory and leaves the v1 instance intact):
   ```shell
   influxd upgrade            # set --engine-path if your v1 engine isn't in the default location
   ```
2. **Export each bucket to line protocol** with `influxd inspect export-lp` (parallelize per
   bucket; compress with `--compress`):
   ```shell
   influxd inspect export-lp \
       --bucket-id <bucket id> \
       --engine-path ~/.influxdbv2/engine \
       --output-path buckets/<bucket>/<bucket-id>.gz \
       --compress
   ```
   Bucket-name→ID mapping comes from `GET /api/v2/buckets?org=<org>` while the local daemon
   is running.
3. **Ingest into the read-replica cluster** with the Timestream ingestion script
   ([`...targets/timestream_for_influxdb/ingestion/influxdb_ingestion.py`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts/targets/timestream_for_influxdb/ingestion)).
   Set `INFLUXDB_V2_URL` / `INFLUXDB_V2_ORG` / `INFLUXDB_V2_TOKEN` for the cluster, create the
   target bucket, then point the script at the directory of `.gz` files:
   ```shell
   python3 influxdb_ingestion.py <bucket_name> <data_directory> --skip-bucket-check
   ```

## From Timestream for LiveAnalytics

Timestream for LiveAnalytics is in maintenance mode; Timestream for InfluxDB is a supported
migration target for **moderate-cardinality** workloads. Use the
[**LiveAnalytics migration tooling**](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts),
a four-stage pipeline orchestrated by `main.py --config <config.yaml>`:

1. **Cardinality assessment** — map your LiveAnalytics schema to an InfluxDB schema and check
   the series cardinality. **InfluxDB is the wrong target if cardinality exceeds ~10M series**
   (consider RDS for PostgreSQL instead). The
   [`cardinality.py`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts/cardinality)
   script computes it and recommends an instance type; high-cardinality dimensions (e.g. a
   unique `request_id`) can be demoted from **tags to fields** to bring cardinality down.
2. **Unload** — export the LiveAnalytics table(s) to S3 in **Parquet with no compression**
   (the format the ingestion stage expects).
3. **Transform** — Athena converts the Parquet to line protocol, applying the tag/field schema
   and adding an `la_unload=1` marker field.
4. **Ingest** — the same `influxdb_ingestion.py` loads the line protocol into the V2 instance.
5. **Validate** — compare logical row counts between source and target.

**Configure the V2 target** with environment variables:
```shell
export INFLUXDB_V2_URL="https://<your-instance>:8086"
export INFLUXDB_V2_ORG="<org>"
export INFLUXDB_V2_TOKEN="<token>"
```

The pipeline runs in two modes (set in the config):
- **`batch`** — migrate everything in a fixed `start_time`…`end_time` window. Use when there
  are no new writes to LiveAnalytics.
- **`live_replication`** — run continuously, backfilling and replicating new writes on an
  interval (`batch_sleep_min`) with optional `backfill_min_overlap` for late-arriving data and
  an optional `cutoff_time`. This is the basis for a near-zero-downtime cutover.

For the end-to-end live cutover (data replication → gradual application cutover → cleanup),
follow the
[Live Migration Guide](https://github.com/awslabs/amazon-timestream-tools/blob/mainline/tools/python/liveanalytics_migration_scripts/targets/timestream_for_influxdb/live_migration_guide.md).

---

## Things to get right (any source)

- **Schema / namespace mapping:** target data lands under an `org` + `bucket`; each source
  measurement becomes an InfluxDB measurement. Decide the bucket layout before you start.
- **Tags vs. fields:** the tag set defines series cardinality. Only index (tag) what you
  filter/group on; demote high-cardinality attributes to fields.
- **Cardinality ceiling:** keep well under **~10M series** per instance — it drives memory use
  and write/query performance. Size the instance from the cardinality assessment.
- **Timestamp precision:** carry the original precision through ingestion (`--precision`,
  default `ns`); a mismatch silently shifts every point.
- **Batching:** ingest **thousands of points per request**; many tiny writes cause replica lag
  (see [`gotchas.md`](./gotchas.md)).
- **Backfill order & instance sizing:** large historical loads benefit from a high-IOPS
  instance and a network-optimized EC2 box in the same Region as the target (see the ingestion
  script's performance notes).

## AWS migration tools and documentation
- **InfluxDB OSS 2.x → Timestream for InfluxDB** — [AWS InfluxDB migration script](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/influx-migration) and walkthrough: [Use the AWS InfluxDB migration script to migrate your InfluxDB OSS 2.x data to Amazon Timestream for InfluxDB](https://aws.amazon.com/blogs/database/use-the-aws-influxdb-migration-script-to-migrate-your-influxdb-oss-2-x-data-to-amazon-timestream-for-influxdb/).
- **InfluxDB v1 → Timestream for InfluxDB** — [InfluxDB v1 to v2 migration guide](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/guides/influxdb_v1_to_v2_migration).
- **Timestream for LiveAnalytics → Timestream for InfluxDB** — [LiveAnalytics migration tooling](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts) and its [Timestream for InfluxDB target guide](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/tools/python/liveanalytics_migration_scripts/targets/timestream_for_influxdb).
- **Service documentation** — [Amazon Timestream for InfluxDB developer guide](https://docs.aws.amazon.com/timestream/latest/developerguide/timestream-for-influxdb.html) and [Applying the AWS Well-Architected Framework for Amazon Timestream for InfluxDB](https://docs.aws.amazon.com/prescriptive-guidance/latest/timestream-for-influxdb-well-architected-framework/introduction.html).
