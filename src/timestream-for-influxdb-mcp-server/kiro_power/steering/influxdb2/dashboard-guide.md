# Grafana Dashboards for InfluxDB 2

How to visualize **Timestream for InfluxDB v2** data in Grafana.

## Data source
Grafana ships a built-in [**InfluxDB** data source plugin](https://grafana.com/docs/grafana/latest/datasources/influxdb/). Add it via **Connections → Data sources → InfluxDB**. The plugin supports three query languages; for v2 use **Flux** (primary) or **InfluxQL**.

### Connection settings
- **URL:** `https://<INSTANCE_ENDPOINT>:8086` (v2 default port).
- **Network reachability:** the Grafana server must reach the instance. For private instances, run Grafana inside the VPC or front the endpoint with a bastion/port-forward (see `influxdb2/onboarding.md`).

### Flux (recommended for v2)
Set **Query language: Flux**, then provide:
- **Organization:** your InfluxDB org name.
- **Token:** a data-plane token with read access (retrieve from InfluxDB UI — see `influxdb2/onboarding.md`).
- **Default Bucket:** optional.

Example panel query:
```flux
from(bucket: "my-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage")
```
`v.timeRangeStart`/`v.timeRangeStop` bind the panel to Grafana's time picker; `v.windowPeriod` is the auto-interval for `aggregateWindow`.

### InfluxQL (alternative)
Set **Query language: InfluxQL**. InfluxQL needs a **DBRP mapping** (database/retention-policy → bucket) on the instance; without it queries return no databases. Configure **Database**, and use **Bearer** auth (header `Authorization: Bearer <token>`). Use Flux instead, unless you need InfluxQL compatibility.

Example panel query:
```sql
SELECT mean("usage") FROM "cpu" WHERE $timeFilter GROUP BY time($__interval) fill(null)
```
In Grafana, the `$timeFilter` macro expands to the panel's time range (the InfluxQL equivalent of Flux's `v.timeRangeStart`/`v.timeRangeStop`), and `$__interval` is the auto-interval for the `GROUP BY time(...)` bucket. For raw rows without aggregation, use `SELECT "usage" FROM "cpu" WHERE $timeFilter`.

## Building dashboards
- Use the visual query builder or raw editor in the panel. **Time series** and **Stat** panels cover most metrics; **Table** for raw rows.
- Use **template variables** (e.g. a query variable over tag values) for reusable, filterable dashboards.
- Grafana **alerting** and **annotations** both work against this data source.

### Example: template variable over tag values
Create a **Query** variable named `host` that lists the values of the `host` tag, so panels can be filtered by host.

InfluxQL variable query:
```sql
SHOW TAG VALUES WITH KEY = "host"
```
Flux variable query:
```flux
import "influxdata/influxdb/schema"
schema.tagValues(bucket: "my-bucket", tag: "host")
```

### Example: reference the variable in a panel query
Filter the panel by the selected `host` value. In InfluxQL, wrap the variable in a regex match (`=~ /^$host$/`) — Grafana interpolates multi-value selections as a regex like `(host1|host2)`:
```sql
SELECT mean("usage") FROM "cpu" WHERE ("host" =~ /^$host$/) AND $timeFilter GROUP BY time($__interval) fill(null)
```
In Flux, compare against the variable directly:
```flux
from(bucket: "my-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage" and r.host == "${host}")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

### Example: Stat panel for a current value
A **Stat** panel showing the latest single value works well with a `last()` selector:
```sql
SELECT last("usage") FROM "cpu" WHERE $timeFilter
```

### Example: one series per tag value
`GROUP BY` a tag to render a separate line per host in a **Time series** panel:
```sql
SELECT mean("usage") FROM "cpu" WHERE $timeFilter GROUP BY time($__interval), "host" fill(null)
```
Flux equivalent — `group()` by the `host` column before aggregating:
```flux
from(bucket: "my-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage")
  |> group(columns: ["host"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

### Example: Table panel for raw rows
For a **Table** panel showing raw, unaggregated rows, select the fields directly and skip the `GROUP BY time(...)`:
```sql
SELECT "usage", "host" FROM "cpu" WHERE $timeFilter ORDER BY time DESC LIMIT 100
```

### Example: annotation query
Grafana **annotations** overlay events on a graph. Configure a dashboard annotation against this data source with a query that returns a time column plus text:
```sql
SELECT "text" FROM "deploy_events" WHERE $timeFilter
```

### Editing panels as JSON
Grafana exposes the underlying JSON in two places:
- **Panel JSON** — open a panel's menu and choose **Inspect → Panel JSON** (the **JSON** tab in the panel inspector). This lets you view and copy the panel JSON, panel data JSON, and data frame structure JSON. It's primarily an inspect/export view (handy when provisioning or administering Grafana); inline editing of panel JSON is limited and varies by Grafana version.
- **Dashboard JSON Model** — open **Dashboard settings → JSON Model** to see the entire dashboard's JSON, including every panel definition (queries, visualization type, field config, grid layout). This is the raw representation you edit or commit when managing dashboards as code.

## Monitoring the database itself
To dashboard the health of the Timestream for InfluxDB instance (CPU, memory, write throughput, query latency), use the AWS sample in **awslabs/amazon-timestream-tools** → [`integrations/influxdb_metrics_dashboard`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/integrations/influxdb_metrics_dashboard). It is a CDK app that deploys a Telegraf collector to scrape the instance `/metrics` endpoint into CloudWatch and ships a pre-built Grafana dashboard. CloudWatch metrics (`CPUUtilization`, `MemoryUtilization`, etc.) can also be charted directly via Grafana's CloudWatch data source.

## Managing dashboards via the Grafana HTTP API

Grafana exposes a REST API for creating, reading, updating, and deleting dashboards. This is useful for provisioning panels as code or automating dashboard rollout across environments. See the [Grafana Dashboard HTTP API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/dashboard/) for more information.

These calls target your **Grafana** server (not the InfluxDB endpoint), authenticate with a Grafana **service account token** (`Authorization: Bearer <token>`), and use the dashboard API available in Grafana 12+. `:namespace` is your org namespace (`default` for the default org), the dashboard JSON (panels, InfluxQL/Flux targets, variables) goes in `spec`, and `metadata.name` is the dashboard UID.

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

**Flux** (`version: Flux`, with organization, default bucket, and token):
```bash
curl -X POST "https://<grafana-host>/api/datasources" \
  -H "Authorization: Bearer <grafana-service-account-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Timestream-InfluxDB-Flux",
    "type": "influxdb",
    "access": "proxy",
    "url": "https://<instance-endpoint>:8086",
    "jsonData": { "version": "Flux", "organization": "<org>", "defaultBucket": "<bucket>" },
    "secureJsonData": { "token": "<influxdb-token>" }
  }'
```

**InfluxQL** (token passed as an `Authorization` header; the bucket needs a DBRP mapping):
```bash
curl -X POST "https://<grafana-host>/api/datasources" \
  -H "Authorization: Bearer <grafana-service-account-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Timestream-InfluxDB-InfluxQL",
    "type": "influxdb",
    "access": "proxy",
    "url": "https://<instance-endpoint>:8086",
    "jsonData": { "dbName": "<bucket>", "httpHeaderName1": "Authorization" },
    "secureJsonData": { "httpHeaderValue1": "Bearer <influxdb-token>" }
  }'
```

### Create a dashboard with panels

Panels live in the dashboard `spec.panels` array. Each panel sets a `type`, a `gridPos` (layout), and `targets` (the queries), where each target's `datasource.uid` is the InfluxDB data source created above. This example creates a time series panel driven by a Flux query:
```bash
curl -X POST "https://<grafana-host>/apis/dashboard.grafana.app/v1/namespaces/default/dashboards" \
  -H "Authorization: Bearer <grafana-service-account-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": { "generateName": "cpu-" },
    "spec": {
      "title": "CPU Usage",
      "schemaVersion": 41,
      "tags": ["influxdb"],
      "time": { "from": "now-6h", "to": "now" },
      "panels": [
        {
          "type": "timeseries",
          "title": "Mean usage by host",
          "datasource": { "type": "influxdb", "uid": "<datasource-uid>" },
          "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
          "targets": [
            {
              "refId": "A",
              "datasource": { "type": "influxdb", "uid": "<datasource-uid>" },
              "query": "from(bucket: \"<bucket>\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r._measurement == \"cpu\" and r._field == \"usage\")\n  |> group(columns: [\"host\"])\n  |> aggregateWindow(every: v.windowPeriod, fn: mean)"
            }
          ]
        }
      ]
    }
  }'
```
Add more objects to the `panels` array — each with its own `gridPos` — to build a multi-panel dashboard. Set `"type": "stat"` for a single-value Stat panel or `"type": "table"` for a raw-rows Table panel.

## See also
- Ingestion via Telegraf: [`integrations/telegraf`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/integrations/telegraf)
- [Grafana InfluxDB data source docs](https://grafana.com/docs/grafana/latest/datasources/influxdb/)
- Multiagent observability with Grafana: [`sample_apps/python/multiagent_observability`](https://github.com/awslabs/amazon-timestream-tools/tree/mainline/sample_apps/python/multiagent_observability#grafana-dashboard-overview).
