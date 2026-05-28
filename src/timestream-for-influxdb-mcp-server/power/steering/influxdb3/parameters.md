# InfluxDB v3 Parameter Reference

## Table of Contents
- [InfluxDBv3Core Parameters](#influxdbv3core-parameters)
- [InfluxDBv3Enterprise Additional Parameters](#influxdbv3enterprise-additional-parameters)
- [Duration Type Format](#duration-type-format)
- [PercentOrAbsoluteLong Format](#percentorabsolutelong-format)
- [CLI Examples](#cli-example)

## InfluxDBv3Core Parameters

All parameters below are available in both `InfluxDBv3Core` and `InfluxDBv3Enterprise`.

### Query and Logging

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `queryFileLimit` | integer | 0-1024 | Max number of query log files |
| `queryLogSize` | integer | 1-10000 | Max size of query log in entries |
| `logFilter` | string | max 1024 chars | Log filter expression |
| `logFormat` | string | `full` | Log output format |

### DataFusion Runtime

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `dataFusionNumThreads` | integer | 1-2048 | Number of DataFusion worker threads |
| `dataFusionRuntimeType` | string | `multi-thread`, `multi-thread-alt` | Tokio runtime type |
| `dataFusionRuntimeDisableLifoSlot` | boolean | — | Disable LIFO slot optimization |
| `dataFusionRuntimeEventInterval` | integer | 1-128 | Event polling interval |
| `dataFusionRuntimeGlobalQueueInterval` | integer | 1-128 | Global queue check interval |
| `dataFusionRuntimeMaxBlockingThreads` | integer | 1-1024 | Max blocking threads |
| `dataFusionRuntimeMaxIoEventsPerTick` | integer | 1-4096 | Max I/O events per tick |
| `dataFusionRuntimeThreadKeepAlive` | Duration | — | Thread keep-alive duration |
| `dataFusionRuntimeThreadPriority` | integer | -20 to 19 | Thread priority (lower = higher priority) |
| `dataFusionMaxParquetFanout` | integer | 1-10000000 | Max parquet file fanout |
| `dataFusionUseCachedParquetLoader` | boolean | — | Use cached parquet loader |
| `dataFusionConfig` | string | pattern: `key:value,...` | Additional DataFusion config |

### HTTP

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `maxHttpRequestSize` | long | 1024-16777216 | Max HTTP request body size in bytes |

### WAL (Write-Ahead Log)

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `forceSnapshotMemThreshold` | PercentOrAbsoluteLong | — | Memory threshold to force WAL snapshot |
| `walSnapshotSize` | integer | 1-10000 | WAL snapshot size |
| `walMaxWriteBufferSize` | integer | 1-1000000 | Max WAL write buffer size |
| `snapshottedWalFilesToKeep` | integer | 0-10000 | Number of snapshotted WAL files to retain |
| `walReplayFailOnError` | boolean | — | Fail on WAL replay errors |
| `walReplayConcurrencyLimit` | integer | — | Concurrent WAL replay limit |

### Cache and Storage

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `preemptiveCacheAge` | Duration | — | Age threshold for preemptive caching |
| `parquetMemCachePrunePercentage` | float | 0-1 | Fraction of cache to prune |
| `parquetMemCachePruneInterval` | Duration | — | Interval between cache prune cycles |
| `disableParquetMemCache` | boolean | — | Disable parquet memory cache |
| `parquetMemCacheQueryPathDuration` | Duration | — | Query path cache duration |
| `parquetMemCacheSize` | PercentOrAbsoluteLong | — | Parquet memory cache size |
| `lastCacheEvictionInterval` | Duration | — | Last-value cache eviction interval |
| `distinctCacheEvictionInterval` | Duration | — | Distinct-value cache eviction interval |
| `tableIndexCacheMaxEntries` | integer | — | Max table index cache entries |
| `tableIndexCacheConcurrencyLimit` | integer | — | Table index cache concurrency limit |

### Data Lifecycle

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `gen1Duration` | Duration | — | Duration for gen1 data files |
| `gen1LookbackDuration` | Duration | — | Lookback window for gen1 compaction |
| `retentionCheckInterval` | Duration | — | Interval between retention policy checks |
| `deleteGracePeriod` | Duration | — | Grace period before permanent deletion |
| `hardDeleteDefaultDuration` | Duration | — | Default duration for hard deletes |

### Memory

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `execMemPoolBytes` | PercentOrAbsoluteLong | — | Execution memory pool size |

## InfluxDBv3Enterprise Additional Parameters

These parameters are **only** available in `InfluxDBv3Enterprise`, in addition to all Core parameters above. `InfluxDBv3Core` is single-node only — there are no horizontal-scaling parameters in Core. Horizontal scaling requires Enterprise.

### Cluster Topology (all required in Enterprise)

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `ingestQueryInstances` | integer **[required]** | — | Number of combined ingest+query instances (primary write-and-read nodes) |
| `queryOnlyInstances` | integer **[required]** | — | Number of query-only (read) instances. Populates `readerEndpoint`. |
| `dedicatedCompactor` | boolean **[required]** | — | Whether to run a dedicated compactor instance |

**Horizontal scaling workflow:** Parameter groups are immutable, so to change topology you **MUST** create a new parameter group with updated values for these fields, then run `update-db-cluster --db-parameter-group-identifier NEW_ID` (the cluster reboots automatically).

### Compaction

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `compactionRowLimit` | integer | — | Max rows per compaction plan |
| `compactionMaxNumFilesPerPlan` | integer | — | Max files per compaction plan |
| `compactionGen2Duration` | Duration | — | Duration for gen2 compaction files |
| `compactionMultipliers` | string | — | Compaction multiplier configuration |
| `compactionCleanupWait` | Duration | — | Wait time before compaction cleanup |
| `compactionCheckInterval` | Duration | — | Interval between compaction checks |

### Caching from History

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `lastValueCacheDisableFromHistory` | boolean | — | Disable last-value cache population from history |
| `distinctValueCacheDisableFromHistory` | boolean | — | Disable distinct-value cache population from history |

### Replication

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `replicationInterval` | Duration | — | Interval between replication cycles |
| `catalogSyncInterval` | Duration | — | Interval between catalog sync operations |

## Duration Type Format

Duration parameters use a structure with `durationType` and `value`:

```json
{
  "durationType": "seconds",
  "value": 300
}
```

Valid `durationType` values: `hours`, `minutes`, `seconds`, `milliseconds`, `days`

CLI shorthand: `durationType=seconds,value=300`

## PercentOrAbsoluteLong Format

These parameters accept either a percentage or an absolute byte value (tagged union — use one, not both):

```json
{"percent": "70%"}
```
or
```json
{"absolute": 1073741824}
```

Percent pattern: `(100|[1-9]?[0-9])%` (0%-100%)

CLI shorthand: `percent=70%` or `absolute=1073741824`

## CLI Example

### Creating a v3 Core parameter group with custom settings

```bash
aws timestream-influxdb create-db-parameter-group \
  --name my-v3-tuned \
  --description "Tuned v3 Core params for high-throughput ingestion" \
  --parameters '{
    "InfluxDBv3Core": {
      "dataFusionNumThreads": 16,
      "walMaxWriteBufferSize": 50000,
      "maxHttpRequestSize": 10485760,
      "forceSnapshotMemThreshold": {"percent": "70%"},
      "preemptiveCacheAge": {"durationType": "hours", "value": 4},
      "retentionCheckInterval": {"durationType": "minutes", "value": 30}
    }
  }' \
  --region us-east-1
```

### Creating a v3 Enterprise parameter group

Enterprise requires `ingestQueryInstances`, `queryOnlyInstances`, and `dedicatedCompactor` to be set:

```bash
aws timestream-influxdb create-db-parameter-group \
  --name my-v3-enterprise \
  --description "Enterprise params with 2 ingest+query, 2 query-only, dedicated compactor" \
  --parameters '{
    "InfluxDBv3Enterprise": {
      "ingestQueryInstances": 2,
      "queryOnlyInstances": 2,
      "dedicatedCompactor": true,
      "dataFusionNumThreads": 32,
      "compactionCheckInterval": {"durationType": "minutes", "value": 5}
    }
  }' \
  --region us-east-1
```
