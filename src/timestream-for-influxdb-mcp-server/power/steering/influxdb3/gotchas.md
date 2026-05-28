# Common Gotchas & Pain Points for Timestream for InfluxDB v3

## Critical — Will Cause Outages If Ignored

**Small Batch Writes + Many Writers**: Writing 1 record per request with hundreds of concurrent writers causes replica lag climbing to 200+ seconds. Always batch 5,000+ points per write request.

**Processing Engine on Multi-Node**: Scheduled triggers execute on EVERY node. On small instances (db.influx.xlarge), this causes OOM (Memory Exhausted while HashAggSpill). Use `node_spec` to target specific nodes, or scale up instance type.

## Important — Will Cause Confusion

**Parameter Group Name Must Be Alphanumeric**: The `--name` for `create-db-parameter-group` also only accepts `[a-zA-Z0-9]+` — no hyphens or underscores. Use the parameter group **ID** (not name) in `--db-parameter-group-identifier` when creating instances/clusters.

**No IAM on Data Plane**: Control plane uses SigV4/IAM. Data plane uses engine-level Bearer tokens only. IAM ReadOnly policy does NOT restrict data plane access. IAM integration for V3 data plane is planned but not yet available.

**Flux Not Supported in V3**: Users migrating from V2 must rewrite all Flux queries to SQL or InfluxQL. There is no automatic migration tool.

**UpdateDbParameterGroup Not Available**: The AWS SDK does not expose this operation. To change parameters, create a new parameter group and update the instance/cluster to reference it.

**No Direct Host Access**: Cannot SSH into instances. All management is via APIs, Console, or InfluxDB UI.

**V3 Port**: V3 uses port 8181 by default, not 8086 like V2.

## Operational — Will Cause Scaling Issues

**10K Tables Limit**: Default max tables per database. Siemens hit this. Increasing beyond recommendation requires understanding compaction and query performance implications.

**S3 Endpoint for Private V3**: Private V3 instances require an S3 VPC endpoint in the same account VPC. Without it, writes fail silently or timeout.

**Compactor Node OOM**: In V3 Enterprise, uneven load distribution can cause compactor nodes to OOM. Monitor `system.parquet_files` for growing file counts. Consider dedicated compactor nodes.

**IO Threads Default**: V3 default is 2 IO threads (`--num-io-threads`). Often insufficient for production workloads. Tune via parameter group.

## Cost — Will Cause Bill Shock

**V3 License Fee**: Enterprise adds a per-vCPU license fee via AWS Marketplace (InfluxData). This is separate from the AWS instance cost. EDP discounts do NOT apply to Marketplace spend.

**Regional Multipliers**: Pricing varies by region. sa-east-1 is 1.30x us-east-1 pricing.

## Integration Gaps

**No QuickSight Connector**: Not available. Use Grafana with Flight SQL.

**No IoT Rules Integration**: Customers must write directly via Telegraf or custom code.

**CloudWatch Metrics**: Available but rollout was gradual. Verify availability in your region. Key metrics: CPUUtilization, MemoryUtilization, HeapMemoryUsage.

**InfluxQL Technical Analysis Functions**: Some are still draft/not working in V3. Test before relying on them in production.
