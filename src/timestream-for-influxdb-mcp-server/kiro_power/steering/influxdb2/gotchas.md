# Common Gotchas & Pain Points for Timestream for InfluxDB v2

## Critical — Will Cause Outages If Ignored

**Series Cardinality**: TSM engine performance typically degrades above ~10M series, depending on instance size. If the user expects high cardinality (many unique tag combinations), recommend V3 instead. Symptoms: slow queries, high memory, compaction stalls.

**Small Batch Writes + Many Writers**: Writing 1 record per request with hundreds of concurrent writers causes replica lag climbing to 200+ seconds. Always batch 5,000+ points per write request.

**Bucket Delete/Recreate with Read Replicas**: Deleting and recreating a bucket on the primary causes replication interruption due to bucket ID mismatch. Avoid this pattern — update the bucket instead.

**Runaway Cardinality**: Since InfluxDB v2 is affected by cardinality. Having many unique tags (1,000,000+) will result in performance degradation. Avoid this. Review tags to make sure tags do not contain unique values for most entries. Consider changing tags with many unique entries to fields.

**Downtime During Patching**: InfluxDB v2 instances and clusters will experience downtime during maintenance windows. We recommend setting the maintenance window to a low-traffic period.

**NOTE**: Monitor resource utilization and consider setting up critical alarms to scale compute if needed. See [influxdb2/troubleshooting.md](troubleshooting.md#monitoring) for more information.

## Important — Will Cause Confusion

**Password Must Be Alphanumeric**: The `--password` parameter for `create-db-instance` and `create-db-cluster` only accepts `[a-zA-Z0-9]+`. Special characters cause a `ValidationException`. If omitted, a password is auto-generated and stored in Secrets Manager.

**Parameter Group Name Must Be Alphanumeric**: The `--name` for `create-db-parameter-group` also only accepts `[a-zA-Z0-9]+` — no hyphens or underscores. Use the parameter group **ID** (not name) in `--db-parameter-group-identifier` when creating instances/clusters.

**No IAM on Data Plane**: Control plane uses SigV4/IAM. Data plane uses engine-level Bearer tokens only. IAM ReadOnly policy does NOT restrict data plane access.

**UpdateDbParameterGroup Not Available**: The AWS SDK does not expose this operation. To change parameters, create a new parameter group and update the instance/cluster to reference it.

**No Direct Host Access**: Cannot SSH into instances. All management is via APIs, Console, or InfluxDB UI.

## Cost — Will Cause Bill Shock

**Read Replica License**: V2 read replicas add 50% license fee on top of base instance cost.

**Regional Multipliers**: Pricing varies by region. sa-east-1 is 1.30x us-east-1 pricing.

## Integration Gaps

**No QuickSight Connector**: Not available. Use native InfluxDB data source (V2).

**No IoT Rules Integration**: Customers must write directly via Telegraf or custom code.

**CloudWatch Metrics**: Available but rollout was gradual. Verify availability in your region. Key metrics: CPUUtilization, MemoryUtilization, HeapMemoryUsage.

## Forgetting that parameter changes require a reboot
**Problem:** Expecting a new parameter group to take effect without a reboot.
**Fix:** Parameter changes only take effect after a reboot. `update-db-cluster --db-parameter-group-identifier NEW_ID` reboots automatically — parameter groups are immutable, so every parameter change goes through `update-db-cluster`.

## Trying to modify a parameter group
**Problem:** Attempting to update an existing parameter group's parameters.
**Fix:** Parameter groups are immutable after creation. Create a new one and reassign it via `update-db-cluster --db-parameter-group-identifier NEW_ID`. There is no `delete-db-parameter-group` operation.

## Passing the cluster name instead of the cluster ID
**Problem:** `--db-cluster-id my-v2-cluster` fails with `ResourceNotFoundException`.
**Fix:** `dbClusterId` is a service-generated identifier returned in the `CreateDbCluster` response. Get it from `list-db-clusters` or the create response — don't use the name you provided at creation.

## Cluster stuck in CREATING or FAILED
**Problem:** Cluster does not reach `AVAILABLE` status.
**Fix:** Run `get-db-cluster` to check `status`. If `FAILED`:
1. Check that the VPC subnets and security groups are valid and in the same VPC
2. Verify the security group allows inbound on the configured port (default 8086)
3. Delete the failed cluster and retry with corrected parameters
4. If the issue persists, check AWS CloudTrail for the `CreateDbCluster` event error details
