# InfluxDB 2 Query Guide

V2 supports two query languages:
- **Flux** — primary language, functional pipeline style, full-featured
- **InfluxQL** — SQL-like, available via V1 compatibility endpoint, limited vs Flux

## Flux Query Endpoint

```
POST /api/v2/query?orgID=<org-id>
Authorization: Bearer <token>
Content-Type: application/vnd.flux
Accept: application/csv
```

Raw body: '<flux script>'

- `Accept: application/csv` is required — Flux always returns CSV. Omitting it causes a 400.
- `Content-Type: application/vnd.flux` is required.
- Use org ID (not name) in the `orgID` query param.
- Include the header `Accept-Encoding: gzip` for responses over 1.4 KB. Using compression saves network bandwidth but increases server-side load.

For example:
```shell
curl \
  --request POST \
  http://localhost:8086/api/v2/query?orgID=ORG_ID \
  --header 'Authorization: Bearer API_TOKEN' \
  --header 'Accept: application/csv' \
  --header 'Content-Type: application/vnd.flux' \
  --data 'from(bucket:"BUCKET_NAME")
        |> range(start: -12h)
        |> filter(fn: (r) => r._measurement == "example-measurement")
        |> aggregateWindow(every: 1h, fn: mean)'
```

or

```
POST /api/v2/query
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/csv
```

JSON body:
- `dialect`: Options for tabular data output. Default output is annotated CSV with headers. [See W3 metadata vocabulary for tabular data](https://www.w3.org/TR/2015/REC-tabular-metadata-20151217/#dialect-descriptions).
- `extern`: Represents a source from a file with a list of Flux statements.
- `now`: Specifies the time that should be treated as the current time. Default is the server's current time.
- `query`: Required. The query to execute.
- `type`: The type of query. Must be `flux`.

For example:
```shell
curl --request POST \
  "http://localhost:8086/api/v2/query" \
  --header "Authorization: Bearer INFLUX_TOKEN" \
  --header "Content-Type: application/json" \
  --data-raw '{
  "dialect": {},
  "extern": {},
  "now": "NOW",
  "query": "QUERY",
  "type": "flux"
}'

Change InfluxDB URL
```

Passing `"dialect": {}` and `"extern": {}` (as above) just means "use defaults / inject nothing". Both are defined in InfluxData's OpenAPI source, not the prose docs — see [`Query.yml`](https://github.com/influxdata/openapi/blob/master/src/common/schemas/Query.yml), [`Dialect.yml`](https://github.com/influxdata/openapi/blob/master/src/common/schemas/Dialect.yml), and [`File.yml`](https://github.com/influxdata/openapi/blob/master/src/common/schemas/File.yml).

### `dialect` — output (annotated CSV) formatting

| Field | Meaning | Default |
|-------|---------|---------|
| `annotations` | Annotation rows to include: any of `group`, `datatype`, `default` | `[]` (none) |
| `header` | Include the column-name header row | `true` |
| `delimiter` | Column separator (single char) | `,` |
| `commentPrefix` | Prefix marking annotation rows | `#` |
| `dateTimeFormat` | `RFC3339` or `RFC3339Nano` (nanosecond precision) | `RFC3339` |

The Flux CSV parsers expect the full annotation set, so for round-trippable output set `"annotations": ["group","datatype","default"]`.

### `extern` — a Flux AST prepended to the query

`extern` is a Flux **AST `File`** node whose `body` is a list of statements injected before your `query`. Use it to supply variables without string-concatenating values into the query text. Example — inject `mybucket = "telegraf"`:

```json
{
  "type": "flux",
  "query": "from(bucket: mybucket) |> range(start: -1h)",
  "extern": {
    "type": "File",
    "body": [
      {
        "type": "VariableAssignment",
        "id":   { "type": "Identifier", "name": "mybucket" },
        "init": { "type": "StringLiteral", "value": "telegraf" }
      }
    ]
  }
}
```

InfluxDB runs `mybucket = "telegraf"` then the query. `init` accepts any Flux expression node (`StringLiteral`, `IntegerLiteral`, `ObjectExpression`, …). This is how Grafana injects its `v` time-range record.

- **Simpler alternative:** for plain value injection use `params` instead — `"params": {"mybucket":"telegraf"}` with `query: "from(bucket: params.mybucket) ..."`. You **cannot** use `params` and `extern` together.
- **Generating the AST:** don't hand-write it — POST Flux text to `/api/v2/query/ast` (or run `flux ast`) to get the JSON for `extern`.

## Flux Patterns

### Basic filter

```flux
from(bucket: "my-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage_idle")
```

`range()` is always required — Flux will not scan without a time bound.

`range()` can be relative to the current time, such as `range(start: -1h, stop: -10m)` or absolute, such as `range(start: 2026-01-01T00:00:00Z, stop: 2026-01-01T12:00:00Z)`.

### Aggregation over time windows

```flux
from(bucket: "my-bucket")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage_idle")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

`createEmpty: false` prevents null rows for windows with no data.

### Multiple fields with pivot

Flux returns one row per field by default. Use `pivot` to get all fields as columns:

```flux
from(bucket: "my-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
```

### Filter by tag value

```flux
from(bucket: "my-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r.host == "server01")
```

Tag filters go in the same `filter()` call as measurement/field filters.

### Top N values

```flux
from(bucket: "my-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage_idle")
  |> top(n: 5, columns: ["_value"])
```

### Last value per tag group

```flux
from(bucket: "my-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage_idle")
  |> last()
```

### Downsampling with aggregateWindow + write to another bucket

```flux
from(bucket: "raw")
  |> range(start: -task.every)
  |> filter(fn: (r) => r._measurement == "cpu")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
  |> to(bucket: "downsampled", org: "my-org")
```

Used in scheduled tasks (see Tasks section below).

### Math between fields

```flux
from(bucket: "my-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "cpu")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> map(fn: (r) => ({ r with usage_total: r.usage_user + r.usage_system }))
```

## InfluxQL Query Endpoint

```
GET /query?db=<bucket-name>&q=<InfluxQL>&epoch=<s|ms|ns>
Authorization: Bearer <token>
```

Or via POST with form encoding:
```
POST /query
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded

db=<bucket-name>&q=<InfluxQL>
```

- `db` maps to the bucket name (not ID)
- `epoch` sets timestamp format in results (optional)

### InfluxQL Patterns

**Basic select:**
```sql
SELECT * FROM cpu WHERE time > now() - 1h
```

**Aggregation with time grouping:**
```sql
SELECT mean(usage_idle), max(usage_system)
FROM cpu
WHERE time > now() - 24h
GROUP BY time(5m), host
```

**Filter by tag:**
```sql
SELECT mean(usage_idle) FROM cpu
WHERE host = 'server01' AND time > now() - 1h
GROUP BY time(5m)
```

**Show measurements and tag keys:**
```sql
SHOW MEASUREMENTS
SHOW TAG KEYS FROM cpu
SHOW TAG VALUES FROM cpu WITH KEY = "host"
SHOW FIELD KEYS FROM cpu
```

**Limitations vs Flux:** InfluxQL cannot join across measurements, has no `pivot`, no custom functions, and limited math operations. Use Flux for anything beyond basic aggregations.

## Scheduled Tasks (Flux)

Tasks run Flux scripts on a schedule — used for downsampling, alerting, and data transformation.

```bash
# Create a task
curl -X POST "https://<endpoint>:8086/api/v2/tasks" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "orgID": "<org-id>",
    "name": "downsample-cpu",
    "every": "1h",
    "flux": "option task = {name: \"downsample-cpu\", every: 1h}\nfrom(bucket: \"raw\") |> range(start: -task.every) |> filter(fn: (r) => r._measurement == \"cpu\") |> aggregateWindow(every: 5m, fn: mean, createEmpty: false) |> to(bucket: \"downsampled\")"
  }'

# List tasks
curl "https://<endpoint>:8086/api/v2/tasks?orgID=<org-id>" \
  -H "Authorization: Bearer <token>"

# Manually trigger a task run
curl -X POST "https://<endpoint>:8086/api/v2/tasks/<taskID>/runs" \
  -H "Authorization: Bearer <token>"

# Check run history
curl "https://<endpoint>:8086/api/v2/tasks/<taskID>/runs" \
  -H "Authorization: Bearer <token>"
```

Task `status`: `active` (runs on schedule) | `inactive` (paused). Use `PATCH /api/v2/tasks/<taskID>` with `{"status": "inactive"}` to pause.

## Query Performance

- Always use `range()` with the narrowest time window needed — full scans are expensive
- Filter on tags (indexed) before fields (not indexed) in `filter()` calls
- Use `aggregateWindow` instead of `window` + `reduce` for standard aggregations — it's optimized
- For "current state" queries (latest value per series), use `last()` after a short range rather than scanning all time
- Tune `queryConcurrency` and `queryMaxMemoryBytes` in the parameter group for high-concurrency workloads
- If queries timeout, increase `httpReadTimeout` in the parameter group
