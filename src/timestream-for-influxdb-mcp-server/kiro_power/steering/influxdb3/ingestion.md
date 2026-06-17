# InfluxDB v3 Data Ingestion & Writing

## Write Endpoints

```
POST /api/v3/write_lp?db=<database>&precision=<auto|nanosecond|microsecond|millisecond|second>
Authorization: Bearer <token>
Content-Type: text/plain
```

- No `org` parameter — V3 has no organizations.
- `db` is the database name (required).
- `accept_partial` (boolean, default true) — when true, valid points succeed even if some fail.
- Default port is **8181** (not 8086 like V2).
- Auth uses `Bearer` prefix (not `Token`).

### Backward-compatible endpoint

V3 also supports the V2 write endpoint for migration:

```
POST /api/v2/write?bucket=<database>&precision=<auto|nanosecond|microsecond|millisecond|second>
Authorization: Bearer <token>
Content-Type: text/plain
```

- `bucket` maps to the V3 database name.
- `org` parameter is accepted but **ignored**.
- Allows existing V2 client code (including `influxdb-client` Python library) to write to V3 without changes — just update the URL, port, and token prefix.

## Batching

**Always batch writes.** Single-point writes with many concurrent writers cause severe replica lag.

- Target **5,000+ points per request** minimum
- Optimal batch size: 5,000–10,000 points
- Max recommended: ~50,000 points per request (beyond this, HTTP timeouts become a risk)
- For high-throughput workloads, tune write timeout in the parameter group (see Tuning section below)

## Python Client

```bash
pip install influxdb3-python
```

```python
from influxdb_client_3 import InfluxDBClient3, Point

client = InfluxDBClient3(
    host="<endpoint>",       # Hostname, including scheme and port. For example: http://localhost:8181
    token="<token>",
    database="<database>"
)

# Write a single point
point = Point("cpu") \
    .tag("host", "server01") \
    .tag("region", "us-east") \
    .field("usage_idle", 98.2) \
    .field("usage_system", 1.8)
client.write(point)

# Write with line protocol string
client.write("cpu,host=server02,region=us-west usage_idle=92.1 1709251200000000000")

# Write a batch of points
points = [
    Point("cpu").tag("host", f"server{i}").field("usage_idle", 90.0 + i)
    for i in range(5000)
]
client.write(points)

client.close()
```

For batching with callbacks (high-throughput):

```python
from influxdb_client_3 import InfluxDBClient3, Point, WriteOptions, InfluxDBError, write_client_options

def on_success(conf, data: str):
    print(f"Written batch: {conf}")

def on_error(conf, data: str, exception: InfluxDBError):
    print(f"Write failed: {exception}")

def on_retry(conf, data: str, exception: InfluxDBError):
    print(f"Retrying: {exception}")

write_opts = WriteOptions(batch_size=5000, flush_interval=1_000)
wco = write_client_options(
    success_callback=on_success,
    error_callback=on_error,
    retry_callback=on_retry,
    write_options=write_opts,
)

with InfluxDBClient3(
    host="<endpoint>",
    token="<token>",
    database="<database>",
    write_client_options=wco,
) as client:
    for i in range(10000):
        client.write(Point("cpu").tag("host", f"server{i % 100}").field("usage_idle", 90.0 + (i % 10)))
# Buffer is flushed on context manager exit
```

### Migrating V2 Python code to V3

If you have existing V2 `influxdb-client` code, you can write to V3 without changing libraries by using the V2 compatibility endpoint:

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Point to V3 instance — use port 8181, org is ignored
client = InfluxDBClient(
    url="https://<endpoint>:8181",
    token="<token>",
    org="-"  # required by client but ignored by V3
)
write_api = client.write_api(write_options=SYNCHRONOUS)

# bucket maps to V3 database name
write_api.write(bucket="<database>", record=Point("cpu").tag("host", "server01").field("usage_idle", 98.2))

write_api.close()
client.close()
```

Note: The V2 client sends `Authorization: Token <value>` by default. If V3 requires `Bearer` prefix, set `auth_scheme="Bearer"` in the `InfluxDBClient` constructor.

## Telegraf

Telegraf is the recommended agent for infrastructure metrics.

### Output

Telegraf can write to V3 using the same `influxdb_v2` output plugin via the V2 compatibility endpoint:

```toml
[[outputs.influxdb_v2]]
  urls = ["https://<endpoint>:8181"]
  token = "<token>"
  organization = "-"          # required by plugin but ignored by V3
  bucket = "<database>"       # maps to V3 database name
```

### Common Telegraf settings

```toml
# Example: collect CPU metrics
[[inputs.cpu]]
  percpu = false
  totalcpu = true
  collect_cpu_time = false
```

```bash
# Test config before running
telegraf --config /etc/telegraf/telegraf.conf --test

# Run
telegraf --config /etc/telegraf/telegraf.conf
```

Telegraf automatically batches writes — default `metric_batch_size = 1000`. Increase to 5000+ for high-throughput:

```toml
[agent]
  metric_batch_size = 5000
  metric_buffer_limit = 100000
```

## Write Error Handling

| HTTP Status | Cause | Action |
|-------------|-------|--------|
| 204 | Success | — |
| 400 | Malformed line protocol | Check syntax |
| 401 | Invalid or expired token | Verify token has write permission |
| 404 | Database not found | Verify names or IDs |
| 413 | Payload too large | Reduce batch size |
| 422 | Writing the line protocol points would exceed the maximum number of tables, databases, columns, tags, or fields | Check line protocol and existing data |
| 429 | Too many requests | Back off and retry with exponential backoff |
| 500 | Server error | Retry; check instance health via `/health` |

## Tuning Write Performance

### Parameter group settings

| Parameter | Default | Recommendation |
|-----------|---------|----------------|
| `walMaxWriteBufferSize` | 100000 | Increase for bursty write workloads |
| `ingestQueryInstances` | 2 | Only for Enterprise. Increase for overall throughput |
| `queryOnlyInstances` | 0 | Only for Enterprise. Increase for higher query throughput |

## Line Protocol

For information on the line protocol data format, see [line-protocol.md](../line-protocol.md).
