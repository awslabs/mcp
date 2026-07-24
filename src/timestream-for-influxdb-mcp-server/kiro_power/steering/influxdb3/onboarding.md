# Timestream for InfluxDB v3

## Overview

This guide provides steps for helping users get started with Amazon Timestream for InfluxDB v3. It sets up their cluster and retrieves their InfluxDB v3 token.

## Use Case

These guidelines apply when users say "Get started with Timestream for InfluxDB v3" or similar phrases. The user's codebase may be mature or have little to no code. This guideline applies to either case.

## Agent Communication Style

**Keep all responses succinct:**

- ALWAYS tell the user what you did.
  - Responses MUST be concise and concrete.
  - ALWAYS contain descriptions to necessary steps.
  - ALWAYS remove unnecessary verbiage.
    - Example:
      - "Created a cluster with 4 ingest-query nodes"
      - "Updated cluster to db.influx.4xlarge"
- Ask direct questions when needed:
  - ALWAYS ask clarifying questions to avoid inaccurate assumptions
  - User ambiguity SHOULD result in questions.
  - MUST clarify incompatible user decisions
    - Example:
      - "How many nodes would you like?"
      - "Do you want your cluster to be publicly accessible?"

Examples:
- Good: "Retrieved auth token. Are you ready to connect with the Influx CLI?"
- Bad: "I'm going to get the auth token from AWS Secrets using the AWS CLI which will allow you to interact with your cluster. This token permits all actions within your database and ..."

## Provisioning Checklist

- [ ] Determine engine: Core (single-node) or Enterprise (multi-node)
- [ ] Choose a parameter group: pass a **service-owned** group to `--db-parameter-group-identifier` — `InfluxDBV3Core` (single-node) or `InfluxDBV3Enterprise` (multi-node) — or create a custom group and pass its returned **id**. **Mind the casing:** service-owned group **identifiers** use an uppercase `V` (`InfluxDBV3Core`), while the `--parameters` **option keys** use a lowercase `v` (`InfluxDBv3Core`).
- [ ] Create cluster with `create-db-cluster` — **you MUST NOT pass** `--username`, `--password`, `--organization`, `--bucket`, or `--deployment-type` — these switch the cluster into a non-v3 initialization mode
- [ ] Poll until `status` is `AVAILABLE`
- [ ] Retrieve token from Secrets Manager: `READONLY-InfluxDB-auth-parameters-<CLUSTER_ID>`
- [ ] Open security group for port 8181 (V3 default)
- [ ] Validate that the cluster is healthy with `/ping` and a test write — if write fails, check token permissions and retry

→ Next step: retrieve the token and make a data-plane call (see Authentication below).

**V3 Core (service-owned default parameter group):**

Use the service-owned `InfluxDBV3Core` parameter group (uppercase `V`). `--db-parameter-group-identifier` is optional — omitting it yields the same Core defaults.
```bash
aws timestream-influxdb create-db-cluster \
  --name my-v3-cluster \
  --db-instance-type db.influx.4xlarge \
  --db-parameter-group-identifier InfluxDBV3Core \
  --vpc-subnet-ids subnet-abc subnet-def \
  --vpc-security-group-ids sg-abc \
  --region us-east-1
```

**V3 Core (custom parameter group):**
```bash
aws timestream-influxdb create-db-parameter-group \
  --name myv3params \
  --description "InfluxDB v3 Core parameters" \
  --parameters '{"InfluxDBv3Core": {}}' \
  --region us-east-1
# Use the returned `id` in the next command

aws timestream-influxdb create-db-cluster \
  --name my-v3-cluster \
  --db-instance-type db.influx.4xlarge \
  --db-parameter-group-identifier <param-group-id> \
  --vpc-subnet-ids subnet-abc subnet-def \
  --vpc-security-group-ids sg-abc \
  --region us-east-1
```

### Authentication

The service provisions a Secrets Manager secret on cluster creation:

```bash
aws secretsmanager get-secret-value \
  --secret-id "READONLY-InfluxDB-auth-parameters-<CLUSTER_ID>" \
  --region us-east-1 --query SecretString --output text
```

The `READONLY-` prefix means the secret is service-managed — modifying it does not change the cluster's actual token.

Example data-plane call:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://$ENDPOINT:8181/api/v3/query_sql?q=SELECT+*+FROM+my_table&db=my_db"
```

### Cluster Management

**Update:**
```bash
aws timestream-influxdb update-db-cluster \
  --db-cluster-id <id> --db-instance-type db.influx.8xlarge --region us-east-1
```

Updatable: `--db-instance-type`, `--db-parameter-group-identifier`, `--db-storage-type`, `--port`, `--failover-mode`, `--log-delivery-configuration`, `--maintenance-schedule`. Changes to instance type, parameter group, or storage type trigger an automatic reboot.

**Reboot:**
```bash
aws timestream-influxdb reboot-db-cluster --db-cluster-id <id> --region us-east-1
# Or specific instances (up to 3):
aws timestream-influxdb reboot-db-cluster --db-cluster-id <id> \
  --instance-ids <id1> <id2> --region us-east-1
```

**Delete:** You **MUST** confirm with the user before deleting — this is irreversible and destroys all data.
```bash
aws timestream-influxdb delete-db-cluster --db-cluster-id <id> --region us-east-1
```

**List and inspect:**
```bash
aws timestream-influxdb list-db-clusters --region us-east-1
aws timestream-influxdb list-db-instances-for-cluster --db-cluster-id <id> --region us-east-1
aws timestream-influxdb get-db-cluster --db-cluster-id <id> --region us-east-1
```

### Scaling

**Vertical:** Change `--db-instance-type` via `update-db-cluster` — reboots automatically.

**Horizontal (Enterprise only):** `InfluxDBv3Core` is single-node. To scale out, use an `InfluxDBv3Enterprise` parameter group with `ingestQueryInstances`, `queryOnlyInstances`, and `dedicatedCompactor` (all three required). Because parameter groups are immutable, changing topology requires creating a new group and running `update-db-cluster --db-parameter-group-identifier <new-id>`. See `parameters.md` for details.

You **MUST NOT pass** `--deployment-type MULTI_NODE_READ_REPLICAS` for V3 — that creates a different (non-v3) cluster type. V3 scales through Enterprise parameter groups.

### Cluster Statuses

- **In-progress:** `CREATING`, `UPDATING`, `UPDATING_INSTANCE_TYPE`, `REBOOTING`, `MAINTENANCE`, `DELETING`
- **Steady:** `AVAILABLE`, `DELETED`
- **Error:** `FAILED`, `REBOOT_FAILED`, `PARTIALLY_AVAILABLE`

Note: `GetDbCluster` returns this value in a field named `status` (not `dbClusterStatus`).

### Connectivity

- **Default port:** 8181. Override with `--port` at creation.
- **Endpoint format:** `CLUSTER_ID-ACCOUNT_ID.timestream-influxdb.REGION.on.aws`
- **`readerEndpoint`:** Populated when the cluster has query-only instances (Enterprise).
- **VPC endpoint service name:** `com.amazonaws.REGION.timestream-influxdb`
- **Private access via bastion:**
  ```bash
  aws ssm start-session --target <bastion-id> \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters '{"host":["ENDPOINT"],"portNumber":["8181"],"localPortNumber":["8181"]}'
  ```
  Add `127.0.0.1 ENDPOINT` to `/etc/hosts` for TLS validation.
- **Network type:** `IPV4` (default) or `DUAL`. Dual-stack is a one-way door — you cannot change `publiclyAccessible` after creation.

### Log Delivery

Logs are delivered hourly to S3. The bucket **MUST** have a policy granting the service principal access and **MUST** be in the same account and region:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "timestream-influxdb.amazonaws.com"},
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::BUCKET_NAME/InfluxLogs/*"
  }]
}
```

Enable via: `--log-delivery-configuration '{"s3Configuration":{"bucketName":"BUCKET","enabled":true}}'`

### Data Ingestion

When a user asks how to write data — read `development-guide.md`. Key facts:
- Always batch 5,000+ points per request
- No `org` param needed; `db` param for database name; auth prefix `Bearer`
- V3 supports the V2 write endpoint (`/api/v2/write`) for backward compatibility

### Schema Design

When a user asks about databases, tables, retention, or cardinality — read `schema-design.md`. Key facts:
- Design databases by retention period
- Measurements become tables automatically on first write
- Virtually unlimited cardinality; watch the **10,000-table** limit (across all databases) and the **500-column-per-table** limit ([docs](https://docs.influxdata.com/influxdb3/enterprise/admin/databases/#database-table-and-column-limits))

### Querying

Read `development-guide.md` — SQL is the primary query language. Flux is NOT supported in V3 — users migrating from V2 must rewrite queries.

### Data Plane Operations

Read `development-guide.md` — 52 endpoints covering write, SQL/InfluxQL query, databases CRUD, tables CRUD, tokens, caches, processing engine triggers, health.

### Error Recovery

Validate that the resource is healthy before investigating further:
- **FAILED/CREATE_FAILED status**: Check `get-db-cluster` for status, then delete and recreate
- **Write errors**: Check line protocol syntax, verify token, confirm endpoint connectivity — see `development-guide.md`
- **Query timeouts**: Reduce time range, filter on indexed columns, check instance sizing
- **OOM errors**: Scale up instance type, reduce concurrent queries, tune memory parameters in parameter group

### Common Mistakes

Read `gotchas.md` before advising on V3 architecture decisions.

## Tagging

```bash
aws timestream-influxdb tag-resource --resource-arn <arn> --tags Key=Env,Value=Prod --region us-east-1
aws timestream-influxdb list-tags-for-resource --resource-arn <arn> --region us-east-1
aws timestream-influxdb untag-resource --resource-arn <arn> --tag-keys Env --region us-east-1
```

## Quick Reference

| Operation | CLI Command |
|-----------|-------------|
| Create V3 cluster | `create-db-cluster --name N --db-instance-type T --db-parameter-group-identifier P --vpc-subnet-ids ... --vpc-security-group-ids ...` |
| Get cluster | `get-db-cluster --db-cluster-id ID` |
| Update cluster | `update-db-cluster --db-cluster-id ID ...` |
| Delete cluster | `delete-db-cluster --db-cluster-id ID` |
| Reboot cluster | `reboot-db-cluster --db-cluster-id ID [--instance-ids ...]` |
| List clusters | `list-db-clusters` |
| List cluster instances | `list-db-instances-for-cluster --db-cluster-id ID` |
| Create param group | `create-db-parameter-group --name NAME --parameters '{"InfluxDBv3Core":{...}}'` |
| Get param group | `get-db-parameter-group --identifier ID` |
| Tag resource | `tag-resource --resource-arn ARN --tags Key=K,Value=V` |

All commands require `--region` and are prefixed with `aws timestream-influxdb`. There is no `delete-db-parameter-group` operation.
