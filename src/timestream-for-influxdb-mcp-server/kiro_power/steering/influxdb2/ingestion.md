# InfluxDB v2 Data Ingestion & Writing

## Write Endpoints

```
POST /api/v2/write?org=<org>&bucket=<bucket>&precision=<ns|us|ms|s>
Authorization: Bearer <token>
Content-Type: text/plain
```

- Use `org` ID (not name) to avoid breakage if the org is renamed.
- Default precision is `ns` — always specify explicitly to avoid silent timestamp errors.
- Returns `204` on success, `400` on malformed line protocol, `422` on field type conflict, `401` on bad token.

## Batching

**Always batch writes.** Single-point writes with many concurrent writers cause severe replica lag.

- Target **5,000+ points per request** minimum
- Optimal batch size: 5,000–10,000 points
- Max recommended: ~50,000 points per request (beyond this, HTTP timeouts become a risk)
- For high-throughput workloads, tune write timeout in the parameter group (see Tuning section below)

## Python Client

```bash
pip install influxdb-client
```

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

client = InfluxDBClient(
    url="https://<endpoint>:8086",
    token="<token>",
    org="<org-id>"  # use org ID, not name
)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Write a single point
point = Point("cpu") \
    .tag("host", "server01") \
    .tag("region", "us-east") \
    .field("usage_idle", 98.2) \
    .field("usage_system", 1.8)
write_api.write(bucket="<bucket>", record=point)

# Write a batch
points = [
    Point("cpu").tag("host", f"server{i}").field("usage_idle", 90.0 + i)
    for i in range(5000)
]
write_api.write(bucket="<bucket>", record=points)

write_api.close()
client.close()
```

For async/high-throughput use `write_options=WriteOptions(batch_size=5000, flush_interval=1000)` instead of `SYNCHRONOUS`:

```python
from influxdb_client import InfluxDBClient, Point, WriteOptions

client = InfluxDBClient(url="https://<endpoint>:8086", token="<token>", org="<org-id>")
write_api = client.write_api(write_options=WriteOptions(batch_size=5000, flush_interval=1000))
# Points are buffered and flushed automatically
write_api.write(bucket="<bucket>", record=Point("cpu").tag("host", "server01").field("usage_idle", 98.2))
write_api.close()  # flushes remaining buffer
client.close()
```

## Go Client

```bash
go get github.com/influxdata/influxdb-client-go/v2
```

```go
import (
    "time"
    influxdb2 "github.com/influxdata/influxdb-client-go/v2"
)

client := influxdb2.NewClient("https://<endpoint>:8086", "<token>")
// Non-blocking API batches writes automatically
writeAPI := client.WriteAPI("<org-id>", "<bucket>") // use org ID, not name

p := influxdb2.NewPoint("cpu",
    map[string]string{"host": "server01", "region": "us-east"},
    map[string]interface{}{"usage_idle": 98.2, "usage_system": 1.8},
    time.Now(),
)
writeAPI.WritePoint(p)
writeAPI.Flush() // ensure buffered points are sent
client.Close()
```

## Telegraf

Telegraf is the recommended agent for infrastructure metrics.

### Output

```toml
[[outputs.influxdb_v2]]
  urls = ["https://<endpoint>:8086"]
  token = "<token>"
  organization = "<org-id>"  # use org ID, not name
  bucket = "<bucket>"
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
| 404 | Bucket not found | Verify names or IDs |
| 413 | Payload too large | Reduce batch size |
| 422 | Field type conflict | Conflicting points are **dropped** (partial write); valid points in the batch succeed. Check field types haven't changed. |
| 429 | Too many requests | Back off and retry with exponential backoff |
| 500 | Server error | Retry; check instance health via `/health` |

On 400 (malformed line protocol), the entire batch is rejected. On 422 (type conflict), only the conflicting points are dropped — the rest of the batch succeeds.

## Tuning Write Performance

### Parameter group settings

| Parameter | Default | Recommendation |
|-----------|---------|----------------|
| `httpWriteTimeout` | 0 | Increase to 60–120s to protect against large amounts of open connections |
| `storageWalMaxWriteDelay` | 10ms | Increase if seeing write stalls under load |
| `storageCacheMaxMemorySize` | 1073741824 | Increase on large instances to reduce WAL flushes |

To change: create a new parameter group with updated values and update the instance to reference it (`UpdateDbInstance`). `UpdateDbParameterGroup` is not available via SDK.


## Line Protocol

For information on the line protocol data format, see [line-protocol.md](../line-protocol.md).
