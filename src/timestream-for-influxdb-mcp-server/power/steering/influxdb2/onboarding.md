# InfluxDB V2 Onboarding Guide

## Overview

This guide provides steps for helping users get started with Amazon Timestream for InfluxDB v2. It covers provisioning through first successful write and query.

## Use Case

These guidelines apply when users say "Get started with Timestream for InfluxDB v2" or similar phrases. The user's codebase may be mature or have little to no code. This guideline applies to either case.

## Agent Communication Style

**Keep all responses succinct:**

- ALWAYS tell the user what you did.
  - Responses MUST be concise and concrete.
  - ALWAYS contain descriptions to necessary steps.
  - ALWAYS remove unnecessary verbiage.
    - Example:
      - "Created a db.influx.2xlarge instance"
      - "Updated instance to db.influx.4xlarge"
- Ask direct questions when needed:
  - ALWAYS ask clarifying questions to avoid inaccurate assumptions
  - User ambiguity SHOULD result in questions.
  - MUST clarify incompatible user decisions
    - Example:
      - "What Region would you like your instance in?"
      - "Do you want your instance to be publicly accessible?"
      - "Do you want an instance with a read replica?"

Examples:
- Good: "Are you ready to deploy your instance with the AWS CLI?"
- Bad: "I'm going to deploy an instance using the AWS CLI. To create an instance, I will use the organization name, username, and password you told me to use..."

## IAM Prerequisites

The AWS principal running these commands needs the following permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "timestream-influxdb:CreateDbParameterGroup",
    "timestream-influxdb:CreateDbInstance",
    "timestream-influxdb:CreateDbCluster",
    "timestream-influxdb:GetDbInstance",
    "timestream-influxdb:GetDbCluster",
    "timestream-influxdb:ListDbInstancesForCluster",
    "secretsmanager:GetSecretValue",
    "ec2:DescribeVpcs",
    "ec2:DescribeSubnets",
    "ec2:CreateVpc",
    "ec2:CreateSubnet",
    "ec2:CreateSecurityGroup",
    "ec2:AuthorizeSecurityGroupIngress"
  ],
  "Resource": "*"
}
```

`secretsmanager:GetSecretValue` must be scoped to the secret ARN returned by the create operation, or `*` if the ARN isn't known in advance.

## Step 0 — VPC and Network Prerequisites

Timestream for InfluxDB requires at least one VPC subnet and a security group. Check whether these exist first.

### Option A — Use an existing VPC

```bash
# List VPCs
aws ec2 describe-vpcs --query 'Vpcs[*].{ID:VpcId,CIDR:CidrBlock,Name:Tags[?Key==`Name`].Value|[0]}'

# List subnets in a VPC
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc-id>" \
  --query 'Subnets[*].{ID:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock}'
```

Note at least one subnet ID to use in Step 1. For `WITH_MULTIAZ_STANDBY` or read replica deployments, provide subnets in at least two availability zones.

### Option B — Create a new VPC and subnets

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query 'Vpc.VpcId' --output text)

# Create subnets in two AZs (required for multi-AZ deployments)
SUBNET_1=$(aws ec2 create-subnet --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 --availability-zone us-east-1a \
  --query 'Subnet.SubnetId' --output text)

SUBNET_2=$(aws ec2 create-subnet --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 --availability-zone us-east-1b \
  --query 'Subnet.SubnetId' --output text)
```

### Create a security group and allow port 8086

Port 8086 (or whichever port the instance was configured with) must be open inbound for InfluxDB V2 data plane access. Do this regardless of whether the VPC is new or existing.

```bash
# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name influxdb-sg \
  --description "InfluxDB V2 access" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow inbound on port 8086 from a specific IP (recommended)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8086 \
  --cidr <your-ip>/32

# Or allow from within the VPC only (private access)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8086 \
  --cidr 10.0.0.0/16
```

**Public vs private access:**
- **Public endpoint** (`publicly-accessible: true` on the instance): the security group must allow inbound 8086 from your client IP. The endpoint will be a public DNS name.
- **Private endpoint** (`publicly-accessible: false`): allow inbound 8086 from your VPC CIDR or specific private IPs. Access requires being within the VPC (EC2, Lambda in the same VPC, VPN, or Direct Connect).

Use `--cidr <your-ip>/32` rather than `0.0.0.0/0` to avoid exposing the instance to the public internet.

## Step 1 — Provision the Instance

**Storage sizing:** EBS storage cannot be increased after creation — plan capacity upfront. Minimum is 400GB; for production workloads estimate based on retention period × write rate × bytes per point.

**Standalone (single node):**
```bash
# 1. Create parameter group (name must be alphanumeric only — no hyphens)
aws timestream-influxdb create-db-parameter-group \
  --name myv2params \
  --parameters '{"InfluxDBv2": {}}'
# Note the `id` field in the response — use it (not the name) in the next command

# 2. Create instance — note the influxAuthParametersSecretArn in the response
aws timestream-influxdb create-db-instance \
  --name my-influxdb \
  --db-instance-type db.influx.large \
  --db-storage-type InfluxIOIncludedT1 \
  --allocated-storage 400 \
  --deployment-type SINGLE_AZ \
  --publicly-accessible \
  --vpc-subnet-ids subnet-abc subnet-def \
  --vpc-security-group-ids sg-abc \
  --db-parameter-group-identifier <param-group-id> \
  --username admin \
  --password <alphanumeric-only> \
  --organization my-org \
  --bucket my-bucket

# 3. Poll until AVAILABLE (typically 10-15 min)
aws timestream-influxdb get-db-instance --identifier my-influxdb
```

The `influxAuthParametersSecretArn` is returned in the **create response** — capture it immediately. It is also available in `get-db-instance` output. Omit `--publicly-accessible` for private VPC-only access. Poll until `status` is `AVAILABLE`, then note the `endpoint` value.

**Password constraint:** must be alphanumeric only (`[a-zA-Z0-9]+`) — no special characters.

**`--db-parameter-group-identifier` is optional** — if omitted, a default parameter group is used. Acceptable for getting started; create a custom one when you need to tune parameters.

**Multi-AZ standby (HA standalone):** Same as above but use `--deployment-type WITH_MULTIAZ_STANDBY` and provide subnets in at least two AZs. Adds a standby node in a second AZ with automatic failover. No reader endpoint — standby is passive.

## Standalone vs Read Replica

| | Standalone | Read Replica Cluster |
|---|---|---|
| Use case | Dev, low-cost, single writer+reader | Read-scale production workloads |
| HA | Optional (`WITH_MULTIAZ_STANDBY`) | Built-in, automatic failover |
| Cost | Base instance cost | Base + 50% license fee per replica |
| Endpoints | Single endpoint | Writer endpoint + reader endpoint |
| Subnets required | 1 AZ minimum | 2 AZs minimum |

Choose read replicas when you need to scale read throughput or require automatic failover. For most new deployments, start with standalone.

**Read replica cluster:**
```bash
aws timestream-influxdb create-db-cluster \
  --name my-influxdb-cluster \
  --db-instance-type db.influx.large \
  --db-storage-type InfluxIOIncludedT1 \
  --allocated-storage 400 \
  --deployment-type MULTI_NODE_READ_REPLICAS \
  --publicly-accessible \
  --vpc-subnet-ids subnet-az1 subnet-az2 \
  --vpc-security-group-ids sg-abc \
  --db-parameter-group-identifier <param-group-id> \
  --username admin \
  --password <alphanumeric-only> \
  --organization my-org \
  --bucket my-bucket

# Poll cluster until AVAILABLE
aws timestream-influxdb get-db-cluster --db-cluster-id <cluster-id>

# Check individual node status and roles
aws timestream-influxdb list-db-instances-for-cluster --db-cluster-id <cluster-id>
```

The `get-db-cluster` response includes both `endpoint` (writer) and `readerEndpoint`:
- **`endpoint`** — use for all writes and Flux queries
- **`readerEndpoint`** — use for read-only queries to offload the primary

**Important:** Never delete and recreate a bucket on a read replica cluster — the bucket ID mismatch breaks replication. Use `PATCH /api/v2/buckets/{bucketID}` to update instead.

## Step 2 — Retrieve Credentials from Secrets Manager

```bash
aws secretsmanager get-secret-value \
  --secret-id <influxAuthParametersSecretArn>
```

The secret contains `username` and `password`. The token is **not** stored here — retrieve it in Step 3.

## Step 3 — Create an All-Access Token

The Secrets Manager secret contains `username` and `password` only — no token. Use them to sign in, then create an all-access token for all future data plane operations.

```bash
# 1. Sign in with Basic auth (Authorization header, not Cookie)
SESSION=$(curl -si -X POST \
  "https://<endpoint>:8086/api/v2/signin" \
  -H "Authorization: Basic $(echo -n 'username:password' | base64)" \
  | grep -i set-cookie | sed 's/.*set-cookie: //' | sed 's/;.*//' | tr -d '\r')

# 2. Get org ID and user ID (org name comes from the secret)
# Note: uses [0] — safe for a fresh Timestream instance which always has exactly one org and one user
ORG_ID=$(curl -s "https://<endpoint>:8086/api/v2/orgs" \
  -H "Cookie: $SESSION" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['orgs'][0]['id'])")

USER_ID=$(curl -s "https://<endpoint>:8086/api/v2/users" \
  -H "Cookie: $SESSION" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['users'][0]['id'])")

# 3. Create all-access token — store the value immediately, it won't be retrievable later
ALL_ACCESS_TOKEN=$(curl -s -X POST "https://<endpoint>:8086/api/v2/authorizations" \
  -H "Cookie: $SESSION" \
  -H "Content-Type: application/json" \
  -d "{\"orgID\":\"$ORG_ID\",\"userID\":\"$USER_ID\",\"permissions\":[
    {\"action\":\"read\",  \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"authorizations\"}},
    {\"action\":\"write\", \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"authorizations\"}},
    {\"action\":\"read\",  \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"buckets\"}},
    {\"action\":\"write\", \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"buckets\"}},
    {\"action\":\"read\",  \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"dashboards\"}},
    {\"action\":\"write\", \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"dashboards\"}},
    {\"action\":\"read\",  \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"dbrp\"}},
    {\"action\":\"write\", \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"dbrp\"}},
    {\"action\":\"read\",  \"resource\":{\"id\":\"$ORG_ID\",  \"type\":\"orgs\"}},
    {\"action\":\"read\",  \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"tasks\"}},
    {\"action\":\"write\", \"resource\":{\"orgID\":\"$ORG_ID\",\"type\":\"tasks\"}},
    {\"action\":\"read\",  \"resource\":{\"id\":\"$USER_ID\", \"type\":\"users\"}},
    {\"action\":\"write\", \"resource\":{\"id\":\"$USER_ID\", \"type\":\"users\"}}
  ]}" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo "All-access token: $ALL_ACCESS_TOKEN"
```

Use `$ALL_ACCESS_TOKEN` as the Token for all subsequent data plane operations. The session cookie is only needed for this bootstrap step — it expires after ~1 hour.

## Step 4 — Verify Connectivity

```bash
curl https://<endpoint>:8086/ping
# Returns 204 — no auth required, confirms network connectivity

curl -H "Authorization: Token $ALL_ACCESS_TOKEN" \
  https://<endpoint>:8086/health
# Returns: {"name":"influxdb","status":"pass","version":"..."}
```

The InfluxDB UI is also available at `https://<endpoint>:8086` — useful for exploring data and building Flux queries interactively.

## Step 5 — Create Scoped Tokens

Best practice: use tokens scoped to the minimum permissions required for each operation. The all-access token from Step 3 should be stored securely and used only to create further scoped tokens — not used directly in applications or automation.

```bash
# Get bucket ID
BUCKET_ID=$(curl -s "https://<endpoint>:8086/api/v2/buckets?org=my-org" \
  -H "Authorization: Token $ALL_ACCESS_TOKEN" \
  | python3 -c "import sys,json; print([b for b in json.load(sys.stdin)['buckets'] if not b['name'].startswith('_')][0]['id'])")

# Create a read/write token scoped to the bucket
curl -X POST https://<endpoint>:8086/api/v2/authorizations \
  -H "Authorization: Token $ALL_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"orgID\": \"$ORG_ID\",
    \"description\": \"app read/write token\",
    \"permissions\": [
      {\"action\": \"read\",  \"resource\": {\"type\": \"buckets\", \"id\": \"$BUCKET_ID\", \"orgID\": \"$ORG_ID\"}},
      {\"action\": \"write\", \"resource\": {\"type\": \"buckets\", \"id\": \"$BUCKET_ID\", \"orgID\": \"$ORG_ID\"}}
    ]
  }"
```

Store the `token` value from the response immediately — it is not retrievable after creation.

## Step 6 — Write Test Data

```bash
# Use scoped token from Step 5 if created, otherwise use all-access token
TOKEN="${APP_TOKEN:-$ALL_ACCESS_TOKEN}"

# Use current Unix timestamp so the data appears in range(start: -1h) queries
NOW=$(date +%s)
curl -X POST "https://<endpoint>:8086/api/v2/write?org=my-org&bucket=my-bucket&precision=s" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: text/plain" \
  -d "cpu,host=server01,region=us-east usage_idle=98.2,usage_system=1.8 $NOW
cpu,host=server02,region=us-east usage_idle=92.1,usage_system=3.4 $NOW"
```

Returns `204` on success. Common errors:
- `401` — token invalid or wrong org
- `400` — malformed line protocol (check tag/field syntax, no spaces in tag values)

## Step 7 — Query to Verify

**Flux:**
```bash
curl -X POST "https://<endpoint>:8086/api/v2/query?org=my-org" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/csv" \
  -d '{
    "query": "from(bucket: \"my-bucket\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"cpu\")",
    "type": "flux"
  }'
```

**InfluxQL (V1 compatibility endpoint):**
```bash
curl "https://<endpoint>:8086/query?db=my-bucket&q=SELECT+*+FROM+cpu+WHERE+time+>+now()+-+1h" \
  -H "Authorization: Token $TOKEN"
```

## What's Created by `create-db-instance`

When you pass `--username`, `--organization`, and `--bucket` to `create-db-instance`, Timestream automatically creates:
- The initial organization with the given name
- The initial bucket with the given name (infinite retention by default)
- The admin user and credentials (stored in Secrets Manager)

You do **not** need to call `POST /api/v2/orgs` or `POST /api/v2/buckets` for the initial setup — they already exist. Use those endpoints to create additional orgs/buckets later.

## Next Steps

- Set a retention policy on the bucket: `PATCH /api/v2/buckets/{bucketID}` with `retentionRules: [{type: "expire", everySeconds: N}]`
- Create additional buckets for different retention tiers (e.g., raw 7d, downsampled 90d)
- Set up Telegraf for metric ingestion — see `development-guide.md`
