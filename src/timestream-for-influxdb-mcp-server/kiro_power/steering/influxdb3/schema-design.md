# InfluxDB v3 Schema Design & Data Modeling

## V2 vs V3 Data Model

| Concept | V2 | V3 |
|---------|----|----|
| Top-level namespace | Organization | *(none)* |
| Data container | Bucket (with retention) | Database (with retention) |
| Logical grouping | Measurement | Table (auto-created from measurement) |
| Indexed metadata | Tags (string only) | Tags → columns (indexed) |
| Value storage | Fields | Fields → columns (non-indexed) |
| Retention config | `retentionRules[].everySeconds` | `retention_period` (e.g. `"30d"`) |
| Series cardinality | ~10M typical threshold (varies by instance) | Virtually unlimited |
| Query language | Flux (primary), InfluxQL | SQL (primary), InfluxQL |

Key differences:
- V3 has **no organizations** — databases are the top-level container.
- V3 measurements become **tables** automatically on first write. Tables have explicit column schemas.
- V3 has **no practical cardinality limit** — the Parquet/S3 storage engine handles high-cardinality workloads that would degrade V2's TSM engine.
- V3 Enterprise limits the total number of tables to **10,000 across all databases**.
- V3 Core limits the total number of tables to **2,000 across all databases**.

## Measurement Naming

Measurements are auto-created on first write — there is no explicit create step. In V3, each measurement becomes a table.

Rules:
- Use simple, descriptive names that describe the data: `cpu`, `memory`, `http_requests`, `sensor_reading`
- Do **not** encode data in the measurement name. `blueberries.plot-1.north` is wrong — use tags for `crop`, `plot`, `region` instead.
- Do not use dots, hyphens, or concatenated attributes in measurement names — they force regex queries and prevent filtering.
- Avoid SQL reserved words (`select`, `from`, `table`, `order`, `group`) — they require quoting.
- Case-sensitive: `CPU` and `cpu` are different measurements.

When to use one measurement vs multiple:
- Use **one measurement** when data shares the same tags and fields (e.g., all CPU metrics in `cpu` with fields `usage_idle`, `usage_system`, `usage_user`).
- Use **separate measurements** when data has different tag/field schemas (e.g., `cpu` and `disk` have different fields and tags).
- Do **not** create a measurement per entity (e.g., `cpu_server01`, `cpu_server02`) — use a `host` tag instead.
- Be aware of table limits (each unique measurement name creates a table).

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

InfluxDB v3 supports virtually unlimited cardinality. High-cardinality tags are safe, but each unique tag key adds a column — respect the **500-columns-per-table limit** (1 timestamp + up to 499 tag/field columns).

## Database Design

A database is the top-level data container in V3 — there are no organizations.

Design principle: same as V2 — **one database per retention period**.

Guidance:
- Create databases via `POST /api/v3/configure/database`.
- Retention is set via `retention_period` (e.g. `"7d"`, `"90d"`, `"1y"`). Null or omitted = infinite.
- Tables are limited to **10,000 across all databases** (default) — plan measurement names accordingly.
- Each table is limited to **500 columns** (1 timestamp + up to 499 tag/field keys).

### Database creation example

```bash
curl -X POST "https://<endpoint>:8181/api/v3/configure/database" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "db": "downsampled-90d",
    "retention_period": "90d"
  }'
```

## Retention Policy

Retention is configured per database via `retention_period` using human-readable durations (`"7d"`, `"30d"`, `"1y"`). Null = infinite.

Update retention via `PATCH /api/v3/configure/database/{name}`. To clear retention (keep data indefinitely), use `DELETE /api/v3/configure/database/retention?db=<name>`.

## Field Type Conflicts

Field types are **locked on first write** per measurement per field key on both V2 and V3. Writing a different type to the same field causes an error and the conflicting points are dropped.

| First write | Subsequent write | Result |
|-------------|-----------------|--------|
| `temp=72.3` (float) | `temp=72i` (integer) | Error — `temp` is locked as float |
| `count=10i` (integer) | `count=10.0` (float) | Error — `count` is locked as integer |
| `status="ok"` (string) | `status=true` (boolean) | Error — `status` is locked as string |

InfluxDB v3 returns **400** if points have been rejected. Depending of the value of the `accept_partial` query parameter, this may mean some points have been written. A **422** status code will be returned if writing the line protocol points would exceed the number of allowed databases, tables, columns, tags, or fields.

Prevention:
- Document your schema before writing. Agree on types per field across all writers.
- Use explicit type suffixes in line protocol: `i` for integer, `"quotes"` for string, bare number for float.
- Be careful with numeric fields — `10` is a float, `10i` is an integer. Mixing these is the most common conflict.
- Telegraf plugins have fixed output types — check plugin docs before adding new inputs.

Detection: use `SHOW COLUMNS FROM <table>` or query `information_schema.columns`.

Resolution:
- You **cannot change** a field's type after first write. Options:
  1. Write to a new field name (e.g., `temp_f` instead of `temp`) and update queries.
  2. Delete all data in the measurement and rewrite with the correct type.
  3. Create a new measurement with the correct schema and migrate data via a task.

## Series Cardinality

A **series** is a unique combination of measurement name + tag set. Series cardinality = total number of unique series across all measurements.

Example: `cpu,host=A,region=us` and `cpu,host=B,region=us` are 2 series.

InfluxDB V3 Parquet/S3 storage engine has **virtually unlimited cardinality**. High-cardinality tags that would cripple V2 are handled efficiently. The main limits to watch are:
- For Enterprise: 10,000 tables across all databases
- For Core: 2,000 tables across all databases
- **500 columns per table** (1 timestamp + up to 499 tag/field columns) — each tag key and field key is a column

If a V2 user is hitting cardinality limits, migrating to V3 is the recommended long-term solution.

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
- V2 cardinality: devices × locations × types
- V3: same line protocol, writes to `sensor_reading` table in the target database

### Infrastructure monitoring

```
cpu,host=web01,region=us-east-1 usage_idle=92.3,usage_system=3.1,usage_user=4.6 1709251200000000000
memory,host=web01,region=us-east-1 used_percent=67.2,available=8589934592i 1709251200000000000
disk,host=web01,region=us-east-1,device=sda1 used_percent=45.0,free=107374182400i 1709251200000000000
```

- Separate measurements for `cpu`, `memory`, `disk` (different field schemas)
- Tags: `host`, `region`, `device` (bounded)
- Fields: numeric metrics
- V3: creates 3 tables — count toward table limit (across all databases)

### Application metrics

```
http_requests,method=GET,endpoint=/api/users,status=200 count=1523i,latency_ms=45.2 1709251200000000000
http_requests,method=POST,endpoint=/api/users,status=201 count=89i,latency_ms=120.5 1709251200000000000
```

- Tags: `method`, `endpoint`, `status` (all bounded)
- Fields: `count` (integer), `latency_ms` (float)
- Do **not** tag `request_id` or `user_id` — high cardinality on V2, wastes column space on V3
