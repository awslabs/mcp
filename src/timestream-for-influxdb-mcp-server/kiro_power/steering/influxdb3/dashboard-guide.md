# Grafana Dashboards for InfluxDB 3

How to visualize **Timestream for InfluxDB v3** data in Grafana.

## Data source
Use Grafana's built-in [**InfluxDB** data source plugin](https://grafana.com/docs/grafana/latest/datasources/influxdb/) (Grafana 12+ recommended for full v3 support). Add it via **Connections → Data sources → InfluxDB**. For v3 the query language is **SQL** (primary) or **InfluxQL**. **Flux is not supported in v3** — do not select it.

### Connection settings
- **URL:** `https://<CLUSTER_ENDPOINT>:8181` (v3 default port).
- **Query language: SQL** (or InfluxQL).
- **Database:** your v3 database name (replaces v2's org/bucket).
- **Token:** a data-plane token with read access; v3 uses the `Bearer` prefix (retrieve from Secrets Manager — see `influxdb3/onboarding.md`).
- **Network reachability:** Grafana must reach the cluster. Private clusters need in-VPC Grafana or a bastion port-forward; the reader endpoint is used when the cluster has query-only nodes (Enterprise).

### SQL example
```sql
SELECT date_bin($__interval, time) AS time, mean(usage) AS usage
FROM cpu
WHERE $__timeFilter(time)
GROUP BY 1 ORDER BY 1
```
`$__timeFilter(time)` and `$__interval` are Grafana macros that bind to the panel time range and auto-interval. Leave `$__interval` unquoted — Grafana substitutes a SQL interval literal, so quoting it breaks the `date_bin` call.

### InfluxQL (alternative)
Set **Query language: InfluxQL** to reuse legacy v1-style queries against v3's compatibility endpoint. Use SQL for new dashboards — it is the native, best-supported path.

InfluxQL ships several time-series functions that have no direct SQL equivalent. They run against v3's InfluxQL compatibility endpoint and are useful in panels (`$timeFilter` and `$__interval` are the Grafana macros for the panel time range and auto-interval):

- **Rate of change** of a counter, per second. Use the non-negative variant to ignore counter resets:
  ```sql
  SELECT non_negative_derivative(mean("usage"), 1s) FROM "cpu" WHERE $timeFilter GROUP BY time($__interval)
  ```
- **Smoothing** with a moving average over N points:
  ```sql
  SELECT moving_average(mean("usage"), 5) FROM "cpu" WHERE $timeFilter GROUP BY time($__interval)
  ```
- **Percentile** (e.g. p95) for latency-style panels:
  ```sql
  SELECT percentile("usage", 95) FROM "cpu" WHERE $timeFilter
  ```
- **Top-N** points:
  ```sql
  SELECT top("usage", 5) FROM "cpu" WHERE $timeFilter
  ```
- **Cumulative sum** and **point-to-point difference**:
  ```sql
  SELECT cumulative_sum(mean("usage")) FROM "cpu" WHERE $timeFilter GROUP BY time($__interval)
  SELECT difference(mean("usage")) FROM "cpu" WHERE $timeFilter GROUP BY time($__interval)
  ```
- **Spread / median / stddev** aggregations in a single panel:
  ```sql
  SELECT spread("usage"), median("usage"), stddev("usage") FROM "cpu" WHERE $timeFilter
  ```
- **Gap filling** for continuous lines — `fill(previous)` carries the last value forward, `fill(linear)` interpolates:
  ```sql
  SELECT mean("usage") FROM "cpu" WHERE $timeFilter GROUP BY time($__interval) fill(previous)
  ```

> Not every InfluxQL function is implemented in v3 — for example `sample()` and `holt_winters()` return an error. Prefer SQL for anything not covered here.

### Arrow Flight SQL (optional)
v3's native high-performance protocol is Arrow Flight SQL. The community **FlightSQL** Grafana data source plugin can connect over gRPC for lower-latency querying, but the built-in InfluxDB data source (SQL) is the simplest and recommended starting point.

## Building dashboards
- **Time series** and **Stat** panels for metrics; **Table** for raw rows. Use the SQL builder or raw editor.
- Use **template variables** (e.g. `SELECT DISTINCT host FROM cpu`) for filterable dashboards — the v3 Distinct Value Cache makes these fast.
- Grafana **alerting** and **annotations** work against the data source.

## Monitoring the cluster itself
To dashboard cluster health (CPU, memory, write throughput, query latency), use the AWS sample in **awslabs/amazon-timestream-tools** → [`integrations/influxdb_metrics_dashboard`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/integrations/influxdb_metrics_dashboard): a CDK app that deploys a Telegraf collector scraping the cluster `/metrics` endpoint into CloudWatch with a pre-built Grafana dashboard. v3's processing engine also includes a System Metrics plugin, and CloudWatch metrics can be charted directly via Grafana's CloudWatch data source.

## Managing dashboards via the Grafana HTTP API

Grafana exposes a REST API for creating, reading, updating, and deleting dashboards. This is useful for provisioning panels as code or automating dashboard rollout across environments. See the [Grafana Dashboard HTTP API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/dashboard/) for more information.

These calls target your **Grafana** server (not the InfluxDB cluster endpoint), authenticate with a Grafana **service account token** (`Authorization: Bearer <token>`), and use the dashboard API available in Grafana 12+. `:namespace` is your org namespace (`default` for the default org), the dashboard JSON (panels, SQL/InfluxQL targets, variables) goes in `spec`, and `metadata.name` is the dashboard UID.

**Create a dashboard** — `POST .../dashboards`, returns `201` (`409` if the UID already exists):
```bash
curl -X POST "https://<grafana-host>/apis/dashboard.grafana.app/v1/namespaces/default/dashboards" \
  -H "Authorization: Bearer <grafana-service-account-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": { "generateName": "cpu-" },
    "spec": { "title": "CPU Dashboard", "schemaVersion": 41, "panels": [], "tags": ["influxdb"] }
  }'
```
Set `metadata.generateName` to let Grafana assign a random UID, or `metadata.name` to choose your own. Add `metadata.annotations."grafana.app/folder"` to place it in a folder.

**Get a dashboard** — `GET .../dashboards/:uid`, returns `200` (or `404` if not found):
```bash
curl "https://<grafana-host>/apis/dashboard.grafana.app/v1/namespaces/default/dashboards/<uid>" \
  -H "Authorization: Bearer <grafana-service-account-token>"
```

**List dashboards** — `GET .../dashboards`; page with `limit` and the `metadata.continue` token returned by the previous response:
```bash
curl "https://<grafana-host>/apis/dashboard.grafana.app/v1/namespaces/default/dashboards?limit=20" \
  -H "Authorization: Bearer <grafana-service-account-token>"
```

**Delete a dashboard** — `DELETE .../dashboards/:uid`, returns `200`:
```bash
curl -X DELETE "https://<grafana-host>/apis/dashboard.grafana.app/v1/namespaces/default/dashboards/<uid>" \
  -H "Authorization: Bearer <grafana-service-account-token>"
```

### Create an InfluxDB data source

A dashboard panel references a data source by its `uid`, so create the InfluxDB data source first with `POST /api/datasources` (see the [Data source HTTP API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/data_source/)). Use the `jsonData`/`secureJsonData` fields documented for [InfluxDB provisioning](https://grafana.com/docs/grafana/latest/datasources/influxdb/configure/#provisioning-examples); the response returns the new data source's `uid`.

**SQL** (`version: SQL`, with database name and token; SQL uses the FlightSQL/gRPC protocol):
```bash
curl -X POST "https://<grafana-host>/api/datasources" \
  -H "Authorization: Bearer <grafana-service-account-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Timestream-InfluxDB-SQL",
    "type": "influxdb",
    "access": "proxy",
    "url": "https://<cluster-endpoint>:8181",
    "jsonData": { "version": "SQL", "dbName": "<database>", "httpMode": "POST", "insecureGrpc": false },
    "secureJsonData": { "token": "<influxdb-v3-token>" }
  }'
```
For InfluxQL instead, drop `version`/`insecureGrpc` and keep `"dbName": "<database>"` with the token in an `Authorization: Bearer` header (`httpHeaderName1`/`httpHeaderValue1`).

### Create a dashboard with panels

Panels live in the dashboard `spec.panels` array. Each panel sets a `type`, a `gridPos` (layout), and `targets` (the queries), where each target's `datasource.uid` is the InfluxDB data source created above. For the SQL query language, the target carries the statement in the `rawSql` field (with `rawQuery: true`). It's easiest to put the body in a file and post it with `-d @dashboard.json`:
```json
{
  "metadata": { "generateName": "cpu-" },
  "spec": {
    "title": "CPU Usage",
    "schemaVersion": 41,
    "tags": ["influxdb"],
    "time": { "from": "now-6h", "to": "now" },
    "panels": [
      {
        "type": "timeseries",
        "title": "Mean usage over time",
        "datasource": { "type": "influxdb", "uid": "<datasource-uid>" },
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
        "targets": [
          {
            "refId": "A",
            "datasource": { "type": "influxdb", "uid": "<datasource-uid>" },
            "rawQuery": true,
            "rawSql": "SELECT date_bin($__interval, time) AS time, mean(usage) AS usage FROM cpu WHERE $__timeFilter(time) GROUP BY 1 ORDER BY 1"
          }
        ]
      }
    ]
  }
}
```
```bash
curl -X POST "https://<grafana-host>/apis/dashboard.grafana.app/v1/namespaces/default/dashboards" \
  -H "Authorization: Bearer <grafana-service-account-token>" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```
Add more objects to the `panels` array — each with its own `gridPos` — to build a multi-panel dashboard. Set `"type": "stat"` for a single-value Stat panel or `"type": "table"` for a raw-rows Table panel.

### Example: reference the variable in a panel query
Filter the panel by the selected `host` value. In InfluxQL, wrap the variable in a regex match (`=~ /^$host$/`) — Grafana interpolates multi-value selections as a regex like `(host1|host2)`:
```sql
SELECT mean("usage") FROM "cpu" WHERE ("host" =~ /^$host$/) AND $timeFilter GROUP BY time($__interval) fill(null)
```
In SQL, compare against the variable directly — Grafana substitutes the selected value into the string, so quote it like any string literal:
```sql
SELECT date_bin($__interval, time) AS time, mean(usage) AS usage
FROM cpu
WHERE $__timeFilter(time) AND host = '$host'
GROUP BY 1 ORDER BY 1
```
For a **multi-value** variable, use `IN` with the `:singlequote` format so each selected value is quoted: `... AND host IN (${host:singlequote})`.
### Example: one series per tag value
`GROUP BY` a tag to render a separate line per host in a **Time series** panel:
```sql
SELECT mean("usage") FROM "cpu" WHERE $timeFilter GROUP BY time($__interval), "host" fill(null)
```
SQL equivalent — select the `host` tag as a column and add it to the `GROUP BY`; Grafana renders each distinct `host` as its own series:
```sql
SELECT date_bin($__interval, time) AS time, host, mean(usage) AS usage
FROM cpu
WHERE $__timeFilter(time)
GROUP BY 1, host ORDER BY 1
```

### Example: Table panel for raw rows
For a **Table** panel showing raw, unaggregated rows, select the fields directly and skip the `date_bin(...)`/`GROUP BY`:
```sql
SELECT time, host, usage
FROM cpu
WHERE $__timeFilter(time)
ORDER BY time DESC
LIMIT 100
```

## See also
- Ingestion via Telegraf: [`integrations/telegraf`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/integrations/telegraf)
- [Grafana InfluxDB data source docs](https://grafana.com/docs/grafana/latest/datasources/influxdb/)
- Multiagent observability with Grafana: [`sample_apps/python/multiagent_observability`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/sample_apps/python/multiagent_observability#grafana-dashboard-overview).
