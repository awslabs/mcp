# InfluxDB 3 Query Guide

V3 supports two query languages:
- **SQL** — primary language
- **InfluxQL** — SQL-like, limited vs SQL

## SQL Query Endpoint

```
GET /api/v3/query_sql?db=DATABASE_NAME&q=SELECT+*+FROM+TABLE_NAME+LIMIT+10
Authorization: Bearer <token>
Accept: application/json
```

**Example**
```shell
curl --request GET \
  "https://localhost:8181/api/v3/query_sql?db=DATABASE_NAME&q=Q" \
  --header "Authorization: Bearer INFLUX_TOKEN"
```

or

```
POST /api/v3/query_sql
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/json
```

JSON body, for POST request:
```json
{
  "db": "<DATABASE_NAME>",
  "q": "<SQL query>",
  "format": "json",
  "params": "<JSON object containing parameters to be used in a parameterized query>"
}
```

**Example**
```shell
curl --request POST \
  "https://localhost:8181/api/v3/query_sql" \
  --header "Authorization: Bearer INFLUX_TOKEN" \
  --header "Content-Type: application/json" \
  --data-raw '{"db":"DATABASE_NAME","format":"json","params":{},"q":"SELECT * FROM mytable"}'
```

**NOTE**: Setting `"format"` to `"jsonl"` is preferred because it streams data back to the client. Keep in mind that this means query response bodies must be read, otherwise queries will be considered cancelled by InfluxDB.

### SQL Patterns

**Syntax**
```sql
[ WITH with_query [, …] ]  
SELECT [ ALL | DISTINCT ] select_expr [, …]  
[ FROM from_item [, …] ]  
[ JOIN join_item [, …] ]  
[ WHERE condition ]  
[ GROUP BY grouping_element [, …] ]  
[ HAVING condition]  
[ UNION [ ALL ] ]
[ ORDER BY expression [ ASC | DESC ][, …] ]  
[ LIMIT count ]
```

**Keywords**
```sql
AND
ALL
ANALYZE
AS
ASC
AT TIME ZONE
BETWEEN
BOTTOM
CASE
DESC
DISTINCT
EXISTS
EXPLAIN
FROM
GROUP BY
HAVING
IN
INNER JOIN
JOIN
LEFT JOIN
LIKE
LIMIT
NOT
OR
ORDER BY
FULL OUTER JOIN
RIGHT JOIN
SELECT
TOP
TYPE
UNION
WHERE
WITH
```

**Numeric Literals**
```sql
-- Integers
10
+10
-10

-- Unsigned integers
10::BIGINT UNSIGNED
+10::BIGINT UNSIGNED

-- Floats
10.78654
-100.56
```

**Date and Time Literals**
```sql
'2022-01-31T06:30:30.123Z'     -- (RFC3339) 
'2022-01-31T06:30:30.123'      -- (RFC3339-like)
'2022-01-31 06:30:30.123'      -- (RFC3339-like)
'2022-01-31 06:30:30'          -- (RFC3339-like, no fractional seconds) 
to_timestamp_nanos(1643610630123000000)   -- (Unix epoch nanoseconds to a timestamp)
to_timestamp(1643610630)                  -- (Unix epoch seconds to a timestamp)
```

**General examples**
```sql
-- Double-quote identifiers that contain whitespace
SELECT "water temperature", "buoy location" FROM buoy

-- Double-quote measurement names with special characters
SELECT * FROM "h2o-temperature"

-- Double-quote identifiers that should be treated as case-sensitive
SELECT "pH" FROM "Water"

-- Selecting with a WHERE clause
SELECT 
  * 
FROM 
  "h2o_feet" 
WHERE 
  "location" = 'santa_monica' 
  AND "level description" = 'below 3 feet'
```

**Show schema information**
```sql
SHOW tables
SHOW columns FROM <measurement>
```

**Joins**
InfluxDB v3 SQL supports joins across tables (measurements) within a database.

The following joins are supported:
```sql
-- Inner join
SELECT
  *
FROM
  home
INNER JOIN home_actions ON
  home.room = home_actions.room
  AND home.time = home_actions.time;

-- Left outer join
SELECT
  *
FROM
  home
LEFT OUTER JOIN home_actions ON
  home.room = home_actions.room
  AND home.time = home_actions.time;

-- Right outer join
SELECT
  *
FROM
  home
RIGHT OUTER JOIN home_actions ON
  home.room = home_actions.room
  AND home.time = home_actions.time;

-- Full outer join
SELECT
  *
FROM
  home
FULL OUTER JOIN home_actions ON
  home.room = home_actions.room
  AND home.time = home_actions.time;
```

**Selector functions**
Selector functions are unique to InfluxDB. Selector functions behave like aggregate functions except they return a time value in addition to the computed value.

Selector functions:
- `SELECTOR_FIRST()`: Returns the first value of a selected column and timestamp.
- `SELECTOR_LAST()`: Returns the last value of a selected column and timestamp.
- `SELECTOR_MIN()`: Returns the smallest value of a selected column and timestamp.
- `SELECTOR_MAX()`: Returns the largest value of a selected column and timestamp.

Examples:
```sql
SELECT 
SELECTOR_MAX("pH", time)['value'],
SELECTOR_MAX("pH", time)['time']
FROM "h2o_pH"

SELECT 
SELECTOR_LAST("water_level", time)['value'],
SELECTOR_LAST("water_level", time)['time']
FROM "h2o_feet"
WHERE time >= timestamp '2019-09-10T00:00:00Z' AND time <= timestamp '2019-09-19T00:00:00Z'
```

## InfluxQL Query Endpoint

InfluxQL can be executed using either the `/api/v3/query_influxql` or the `/query` V1 backwards compatible endpoint.

```
GET /api/v3/query_influxql?db=DATABASE_NAME&q=SELECT+*+FROM+TABLE_NAME+LIMIT+10
Authorization: Bearer <token>
Accept: application/json
```

The `query_influxql` endpoint supports the following query parameters:
- `db`: The name of the database. If you provide a query that specifies the database, you can omit the ‘db’ parameter from your request.
- `q`: Required. The query to execute.
- `format`: The format of the response. Valid options are: `json`, `jsonl`, `csv`, `pretty`, or `parquet`. `jsonl` is preferred because it streams results back to the client. `pretty` is for human-readable output. The default is `json`.
- `params`: JSON-encoded query parameters for parameterized queries.

**Example**
```shell
curl --request GET \
  "https://localhost:8181/api/v3/query_influxql?q=Q" \
  --header "Authorization: Bearer INFLUX_TOKEN"
```

or

```
POST /api/v3/query_influxql
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/json
```

**Example**
```shell
curl --request POST \
  "https://localhost:8181/api/v3/query_influxql" \
  --header "Authorization: Bearer INFLUX_TOKEN" \
  --header "Content-Type: application/json" \
  --data-raw '{"db":"DATABASE_NAME","format":"json","params":{},"q":"SELECT * FROM mytable"}'
```

or

```
GET /query?db=DATABASE_NAME&q=QUERY&chunk_size=10000&chunked=true&u=USERNAME&p=PASSWORD
Authorization: Bearer <token>
Accept: text/csv
```

The `query` endpoint supports the following query parameters:
- `chunked`: Returns points in streamed batches. When set to `true`, InfluxDB chunks responses by series or by every 10,000 points, whichever occurs first.
- `chunk_size`: Specifies the number of points to include in a chunk, if `chunked` is `true`.
- `db`: Required. Database name.
- `epoch`: Timestamp precision. Valid values are: `h`, `m`, `s`, `ms`, `us`, and `ns`.
- `u`: For query string authentication, the user's username.
- `p`: For query string authentication, the user's password. InfluxDB v3 enterprise expects this to be a token with read access to the database and will ignore `u`.
- `q`: The InfluxQL query to execute.

**Example**
```shell
curl --request GET \
  "https://localhost:8181/query?q=Q" \
  --header "Authorization: Bearer INFLUX_TOKEN"
```

or

```
POST /query
Authorization: Bearer <token>
Content-Type: application/json
Accept: text/csv
```

JSON body, for POST request:
```json
{
  "db": "<DATABASE_NAME>",
  "q": "<InfluxQL query>",
  "chunk_size": 10000,
  "chunked": true,
  "epoch": "ns"
}
```

**Example**
```shell
curl --request POST \
  "https://localhost:8181/query" \
  --header "Authorization: Bearer INFLUX_TOKEN" \
  --header "Content-Type: application/json" \
  --data-raw '{
  "chunk_size": 10000,
  "chunked": false,
  "db": "DATABASE_NAME",
  "epoch": "ns",
  "pretty": false,
  "q": "Q"
}'
```

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

**InfluxQL Limitations vs SQL:** InfluxQL cannot join across measurements, has no `pivot`, no custom functions, and limited math operations. Use SQL for anything beyond basic aggregations.
