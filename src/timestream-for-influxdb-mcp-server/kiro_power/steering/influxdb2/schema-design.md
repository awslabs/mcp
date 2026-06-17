# InfluxDB v2 Schema Design & Data Modeling

## V2 vs V3 Data Model

| Concept | V2 | V3 |
|---------|----|----|
| Top-level namespace | Organization | *(none)* |
| Data container | Bucket (with retention) | Database (with retention) |
| Logical grouping | Measurement | Table (auto-created from measurement) |
| Indexed metadata | Tags (string only) | Tags → columns (indexed) |
| Value storage | Fields | Fields → columns (non-indexed) |
| Retention config | `retentionRules[].everySeconds` | `retentionPeriod` (e.g. `"30d"`) |
| Series cardinality | ~10M typical threshold (varies by instance) | Virtually unlimited |
| Query language | Flux (primary), InfluxQL | SQL (primary), InfluxQL |

For key differences between InfluxDB v2 and v3, see [influxdb-2-vs-3.md](../influxdb-2-vs-3.md).

## Measurement Naming

Measurements are auto-created on first write — there is no explicit create step. In V3, each measurement becomes a table.

Rules:
- Use simple, descriptive names that describe the data: `cpu`, `memory`, `http_requests`, `sensor_reading`
- Do **not** encode data in the measurement name. `blueberries.plot-1.north` is wrong — use tags for `crop`, `plot`, `region` instead.
- Do not use dots, hyphens, or concatenated attributes in measurement names — they force regex queries and prevent filtering.
- Avoid Flux keywords (`from`, `to`, `filter`, `range`, `yield`) — they require quoting.
- Case-sensitive: `CPU` and `cpu` are different measurements.

When to use one measurement vs multiple:
- Use **one measurement** when data shares the same tags and fields (e.g., all CPU metrics in `cpu` with fields `usage_idle`, `usage_system`, `usage_user`).
- Use **separate measurements** when data has different tag/field schemas (e.g., `cpu` and `disk` have different fields and tags).
- Do **not** create a measurement per entity (e.g., `cpu_server01`, `cpu_server02`) — use a `host` tag instead.

## Tag vs Field Decision

| Criterion | Tag | Field |
|-----------|-----|-------|
| Indexed? | Yes — fast filtering | No — full scan |
| Data type | Strings only | Float, integer, string, boolean |
| Use for filtering? | Yes | Avoid if possible |
| Use for grouping? | Yes | No |
| Unique values | Low-to-moderate (< 100K distinct on V2) | Unlimited |
| Numeric data | No — store as field | Yes |

Rules:
- **Tags** store metadata shared across many points: `host`, `region`, `sensor_id`, `environment`.
- **Fields** store numeric measurements and unique/variable data: `temperature`, `usage_idle`, `request_count`.
- Never store continuously changing values (timestamps, UUIDs, log messages) as tags — this causes cardinality explosion on V2 and wastes index space on V3.
- Avoid duplicate names for a tag key and field key within the same measurement — query results become unpredictable.
- Sort tags alphabetically in line protocol for best write compression (both engines).

Cardinality considerations: Tags with high unique values directly increase series cardinality. Keep individual tags under ~100K distinct values. Total series cardinality above ~10M (varies by instance size) causes TSM degradation.

## Bucket Design

A bucket is a named container with a retention period. All data in a bucket shares the same retention policy.

Design principle: **one bucket per retention period**. If you need 7-day and 90-day retention, create two buckets.

Common patterns:

| Pattern | Buckets | Use case |
|---------|---------|----------|
| By retention | `raw-7d`, `downsampled-90d`, `archive-365d` | Different data lifetimes |
| By environment | `metrics-prod`, `metrics-staging` | Isolation + different retention |
| By team/tenant | `team-a-metrics`, `team-b-metrics` | Access control via scoped tokens |

Guidance:
- The initial bucket is created automatically by `create-db-instance` — use it for your primary workload.
- Create additional buckets via `POST /api/v2/buckets` for different retention needs.
- Scope tokens to specific buckets for access control — one token per bucket per application.
- Do **not** create a bucket per measurement or per host — this creates management overhead with no benefit.
- On Timestream for InfluxDB V2, **do not delete and recreate buckets** when using read replicas — the bucket ID mismatch breaks replication. Update the bucket instead.

### Bucket creation example

```bash
curl -X POST "https://<endpoint>:8086/api/v2/buckets" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "downsampled-90d",
    "orgID": "<org-id>",
    "retentionRules": [{ "type": "expire", "everySeconds": 7776000 }],
    "description": "90-day downsampled metrics"
  }'
```

## Retention Policy

Retention is configured per bucket via `retentionRules[].everySeconds`. The retention enforcement service runs every 30 minutes by default and deletes entire shard groups (not individual points) when the shard group's time range is fully beyond the retention period.

Common retention values:

| Duration | `everySeconds` | Use case |
|----------|---------------|----------|
| 1 hour | `3600` | Debugging / ephemeral data |
| 1 day | `86400` | Short-term operational metrics |
| 7 days | `604800` | Standard monitoring |
| 30 days | `2592000` | Default for most workloads |
| 90 days | `7776000` | Compliance / trend analysis |
| 1 year | `31536000` | Long-term capacity planning |
| Infinite | `0` | Never expire (use with caution — disk fills) |

When data is actually deleted:
- **Minimum**: after `retention-period` has elapsed
- **Maximum**: after `retention-period + shard-group-duration` has elapsed
- Shard group duration is auto-calculated from retention period. For a 7-day retention, shard group duration is typically 1 day, so data persists 7–8 days.
- Data remains queryable until the shard group is deleted.

Retention can be updated on an existing bucket via `PATCH /api/v2/buckets/{bucketID}`:

```bash
curl -X PATCH "https://<endpoint>:8086/api/v2/buckets/<bucketID>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "retentionRules": [{ "type": "expire", "everySeconds": 604800 }] }'
```

### Downsampling pattern

Use a Flux task to aggregate raw data into a longer-retention bucket:

1. Create `raw-7d` bucket (7-day retention) for high-resolution data
2. Create `downsampled-90d` bucket (90-day retention) for aggregated data
3. Schedule a task to downsample hourly:

```flux
option task = {name: "downsample-cpu", every: 1h}

from(bucket: "raw-7d")
  |> range(start: -task.every)
  |> filter(fn: (r) => r._measurement == "cpu")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
  |> to(bucket: "downsampled-90d")
```

## Field Type Conflicts

Field types are **locked on first write** per measurement per field key on both V2 and V3. Writing a different type to the same field causes an error and the conflicting points are dropped.

| First write | Subsequent write | Result |
|-------------|-----------------|--------|
| `temp=72.3` (float) | `temp=72i` (integer) | Error — `temp` is locked as float |
| `count=10i` (integer) | `count=10.0` (float) | Error — `count` is locked as integer |
| `status="ok"` (string) | `status=true` (boolean) | Error — `status` is locked as string |

InfluxDB v2 returns **422**. Conflicting points are dropped; valid points in the same batch succeed (partial write).

Prevention:
- Document your schema before writing. Agree on types per field across all writers.
- Use explicit type suffixes in line protocol: `i` for integer, `"quotes"` for string, bare number for float.
- Be careful with numeric fields — `10` is a float, `10i` is an integer. Mixing these is the most common conflict.
- Telegraf plugins have fixed output types — check plugin docs before adding new inputs.

Detection: use `SHOW FIELD KEYS FROM <measurement>` (InfluxQL) to check current field types.

Resolution:
- You **cannot change** a field's type after first write. Options:
  1. Write to a new field name (e.g., `temp_f` instead of `temp`) and update queries.
  2. Delete all data in the measurement and rewrite with the correct type.
  3. Create a new measurement with the correct schema and migrate data via a task.

## Series Cardinality

A **series** is a unique combination of measurement name + tag set. Series cardinality = total number of unique series across all measurements.

Example: `cpu,host=A,region=us` and `cpu,host=B,region=us` are 2 series.

V2 TSM engine: performance typically degrades above **~10M series**, depending on instance size and workload. Symptoms: slow queries, high memory, compaction stalls.

Measure cardinality with Flux:

```flux
import "influxdata/influxdb/schema"

schema.tagValues(bucket: "my-bucket", tag: "host")
  |> count()
```

Reduce cardinality:
- Move high-cardinality values from tags to fields
- Remove unnecessary tags
- Use bounded values (e.g., `region` not `ip_address`)
- Delete old high-cardinality data

## Schema Examples

### IoT sensor monitoring

```
sensor_reading,device_id=D001,location=warehouse-a,type=temperature value=22.5 1709251200000000000
sensor_reading,device_id=D001,location=warehouse-a,type=humidity value=45.2 1709251200000000000
sensor_reading,device_id=D002,location=warehouse-b,type=temperature value=19.8 1709251200000000000
```

- Measurement: `sensor_reading` (one measurement for all sensor types)
- Tags: `device_id` (bounded set of devices), `location`, `type`
- Field: `value` (numeric reading)
- Cardinality: devices × locations × types

### Infrastructure monitoring

```
cpu,host=web01,region=us-east-1 usage_idle=92.3,usage_system=3.1,usage_user=4.6 1709251200000000000
memory,host=web01,region=us-east-1 used_percent=67.2,available=8589934592i 1709251200000000000
disk,host=web01,region=us-east-1,device=sda1 used_percent=45.0,free=107374182400i 1709251200000000000
```

- Separate measurements for `cpu`, `memory`, `disk` (different field schemas)
- Tags: `host`, `region`, `device` (bounded)
- Fields: numeric metrics

### Application metrics

```
http_requests,method=GET,endpoint=/api/users,status=200 count=1523i,latency_ms=45.2 1709251200000000000
http_requests,method=POST,endpoint=/api/users,status=201 count=89i,latency_ms=120.5 1709251200000000000
```

- Tags: `method`, `endpoint`, `status` (all bounded)
- Fields: `count` (integer), `latency_ms` (float)
- Do **not** tag `request_id` or `user_id` — this causes high cardinality.
