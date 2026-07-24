# InfluxDB v2 Parameter Reference

> **Single top-level key.** The `--parameters` JSON is a **tagged union** — for InfluxDB v2
> you set exactly one top-level key, `InfluxDBv2`. You cannot mix it with `InfluxDBv3Core`
> or `InfluxDBv3Enterprise` in the same parameter group. Keys are case-sensitive.

> **Read replicas are not configured here.** Unlike v3 Enterprise — where cluster topology
> (`ingestQueryInstances`, `queryOnlyInstances`, `dedicatedCompactor`) lives in the parameter
> group — v2 read replicas are a **cluster-deployment** setting, not a parameter. Configure
> them on `create-db-cluster` via `--deployment-type MULTI_NODE_READ_REPLICAS` and
> `--failover-mode` (`AUTOMATIC` / `NO_FAILOVER`), and choose the node size with
> `--db-instance-type`. The same `InfluxDBv2` parameter group applies uniformly to the primary
> and all read replicas in the cluster. See `onboarding.md` for the full cluster setup workflow.

## Table of Contents
- [InfluxDBv2 Parameters](#influxdbv2-parameters)
  - [Query and Logging](#query-and-logging)
  - [HTTP Timeouts](#http-timeouts)
  - [InfluxQL Query Limits](#influxql-query-limits)
  - [Query Memory](#query-memory)
  - [Session](#session)
  - [Storage — Cache](#storage--cache)
  - [Storage — Compaction](#storage--compaction)
  - [Storage — Index and Series](#storage--index-and-series)
  - [Storage — WAL](#storage--wal)
- [Duration Type Format](#duration-type-format)
- [CLI Examples](#cli-examples)

## InfluxDBv2 Parameters

All parameters below belong to the single `InfluxDBv2` top-level key.

### Query and Logging

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `fluxLogEnabled` | boolean | — | Enable logging of Flux query execution |
| `logLevel` | string | `debug`, `info`, `error` | Log output level |
| `noTasks` | boolean | — | Disable the task scheduler on startup |
| `queryConcurrency` | integer | 0-256 | Number of queries allowed to execute concurrently |
| `queryQueueSize` | integer | 0-256 | Max number of queries allowed in execution queue |
| `tracingType` | string | `log`, `jaeger`, `disabled` | Tracing backend type |
| `metricsDisabled` | boolean | — | Disable the Prometheus `/metrics` endpoint |
| `pprofDisabled` | boolean | — | Disable the `/debug/pprof` profiling endpoint |
| `uiDisabled` | boolean | — | Disable the InfluxDB web UI |

### HTTP Timeouts

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `httpIdleTimeout` | Duration | — | Max idle duration before timing out an HTTP connection |
| `httpReadHeaderTimeout` | Duration | — | Max duration to read HTTP request headers |
| `httpReadTimeout` | Duration | — | Max duration to read an entire HTTP request |
| `httpWriteTimeout` | Duration | — | Max duration before timing out an HTTP response write |

### InfluxQL Query Limits

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `influxqlMaxSelectBuckets` | long | 0-1000000000000 | Max number of `GROUP BY time()` buckets a SELECT can process |
| `influxqlMaxSelectPoint` | long | 0-1000000000000 | Max number of points a SELECT can process |
| `influxqlMaxSelectSeries` | long | 0-1000000000000 | Max number of series a SELECT can process |

### Query Memory

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `queryInitialMemoryBytes` | long | 0-1000000000000 | Initial bytes of memory allocated per query |
| `queryMaxMemoryBytes` | long | 0-1000000000000 | Max bytes of memory allowed across all running queries |
| `queryMemoryBytes` | long | 0-1000000000000 | Max bytes of memory allowed per individual query |

### Session

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `sessionLength` | integer | 1-2880 | Session duration in minutes (max 48 hours) |
| `sessionRenewDisabled` | boolean | — | Disable automatic session renewal on activity |

### Storage — Cache

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `storageCacheMaxMemorySize` | long | 0-1000000000000 | Max size of the in-memory write cache in bytes |
| `storageCacheSnapshotMemorySize` | long | 0-1000000000000 | Cache size in bytes that triggers a snapshot to a TSM file |
| `storageCacheSnapshotWriteColdDuration` | Duration | — | Idle duration before a cold shard's cache is snapshotted |

### Storage — Compaction

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `storageCompactFullWriteColdDuration` | Duration | — | Idle duration before a cold shard is fully compacted |
| `storageCompactThroughputBurst` | long | 0-1000000000000 | Max bytes/sec burst rate for compaction throughput |
| `storageMaxConcurrentCompactions` | integer | 0-64 | Max number of concurrent full/level compactions |

### Storage — Index and Series

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `storageMaxIndexLogFileSize` | long | 0-1000000000000 | Size threshold (bytes) at which the index log file is compacted |
| `storageNoValidateFieldSize` | boolean | — | Skip validation of maximum field/value size |
| `storageRetentionCheckInterval` | Duration | — | Interval between retention policy enforcement checks |
| `storageSeriesFileMaxConcurrentSnapshotCompactions` | integer | 0-64 | Max concurrent snapshot compactions for the series file |
| `storageSeriesIdSetCacheSize` | long | 0-1000000000000 | Size of the internal series ID set cache |

### Storage — WAL (Write-Ahead Log)

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `storageWalMaxConcurrentWrites` | integer | 0-256 | Max number of concurrent WAL writes |
| `storageWalMaxWriteDelay` | Duration | — | Max duration a WAL write waits when the limit is reached before timing out |

## Duration Type Format

Duration parameters use a structure with `durationType` and `value`:

```json
{
  "durationType": "seconds",
  "value": 300
}
```

Valid `durationType` values: `hours`, `minutes`, `seconds`, `milliseconds`, `days`

Both `durationType` and `value` are **required** when the duration parameter is set. `value` must be `>= 0`.

CLI shorthand: `durationType=seconds,value=300`

## CLI Examples

### Creating a v2 parameter group with custom settings

```bash
aws timestream-influxdb create-db-parameter-group \
  --name my-v2-tuned \
  --description "Tuned v2 params for high-concurrency querying" \
  --parameters '{
    "InfluxDBv2": {
      "queryConcurrency": 128,
      "queryQueueSize": 256,
      "logLevel": "info",
      "fluxLogEnabled": true,
      "influxqlMaxSelectSeries": 1000000,
      "queryMaxMemoryBytes": 4294967296,
      "httpReadTimeout": {"durationType": "seconds", "value": 60},
      "storageRetentionCheckInterval": {"durationType": "minutes", "value": 30}
    }
  }' \
  --region us-east-1
```

### Creating a v2 parameter group with shorthand syntax

```bash
aws timestream-influxdb create-db-parameter-group \
  --name my-v2-shorthand \
  --description "v2 params using shorthand syntax" \
  --parameters 'InfluxDBv2={queryConcurrency=64,logLevel=debug,httpIdleTimeout={durationType=minutes,value=5}}' \
  --region us-east-1
```

### Associating the parameter group with an instance

Parameter groups are immutable. To apply one (or change parameters), associate the group with
a DB instance and reboot:

```bash
aws timestream-influxdb update-db-instance \
  --identifier my-v2-instance \
  --db-parameter-group-identifier my-v2-tuned \
  --region us-east-1
```
