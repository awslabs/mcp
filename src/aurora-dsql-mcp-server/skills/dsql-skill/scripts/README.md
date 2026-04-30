# Aurora DSQL Scripts

Bash scripts for common Aurora DSQL cluster management and connection operations.
These scripts can be executed directly, used as agent tools, or configured as hooks.

## Prerequisites

- AWS CLI configured with credentials (`aws configure`)
- `psql` client installed (for psql-connect.sh)
- `jq` installed (for JSON parsing)
- Appropriate IAM permissions:
  - `dsql:CreateCluster` (for create-cluster.sh)
  - `dsql:DeleteCluster` (for delete-cluster.sh)
  - `dsql:GetCluster` (for cluster-info.sh)
  - `dsql:ListClusters` (for list-clusters.sh)
  - `dsql:DbConnect` or `dsql:DbConnectAdmin` (for psql-connect.sh)

## Using Scripts as Tools

Agents can execute these scripts directly via shell tool calls. Each script supports `--help` for usage:

```bash
# List available clusters
./scripts/list-clusters.sh --region us-east-1

# Get cluster details
./scripts/cluster-info.sh abc123def456

# Connect and run a query
./scripts/psql-connect.sh --command "SELECT COUNT(*) FROM entities"
```

## Plugin Hooks

This plugin ships a default `PostToolUse` hook in `hooks/hooks.json` that prompts schema/row verification after `transact` operations. The hook fires automatically — no user configuration required.

### Adding Custom Hooks

Add additional hooks to `.claude/settings.json` or override the defaults:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__aurora-dsql.*__transact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/cluster-info.sh $CLUSTER --region $REGION 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

---

## Available Scripts

### create-cluster.sh

Create a new Aurora DSQL cluster.

```bash
./scripts/create-cluster.sh --created-by claude-opus-4-6
./scripts/create-cluster.sh --created-by claude-opus-4-6 --region us-east-1
./scripts/create-cluster.sh --created-by claude-opus-4-6 --region us-west-2 --tags Environment=dev,Project=myapp
```

**Output:** Cluster identifier, endpoint, and ARN. Exports environment variables for use with other scripts.

---

### delete-cluster.sh

Delete an existing Aurora DSQL cluster.

```bash
./scripts/delete-cluster.sh abc123def456
./scripts/delete-cluster.sh abc123def456 --region us-west-2
./scripts/delete-cluster.sh abc123def456 --force
```

**Note:** Deletion is permanent and cannot be undone.

---

### psql-connect.sh

Connect to Aurora DSQL using psql with automatic IAM authentication.

```bash
export CLUSTER=abc123def456
export REGION=us-east-1
./scripts/psql-connect.sh

./scripts/psql-connect.sh abc123def456 --region us-west-2
./scripts/psql-connect.sh --user myuser
./scripts/psql-connect.sh --command "SELECT * FROM entities LIMIT 5"
./scripts/psql-connect.sh --admin
./scripts/psql-connect.sh --ai-model claude-opus-4-6
```

**Features:**

- Automatically generates IAM auth token (valid for 15 minutes)
- Supports both interactive sessions and command execution
- Uses `admin` user by default (override with `--user` or `$DB_USER`)
- `--ai-model MODEL_ID` appends model identifier to PostgreSQL `application_name` for connection tracking

---

### list-clusters.sh

List all Aurora DSQL clusters in a region.

```bash
./scripts/list-clusters.sh
./scripts/list-clusters.sh --region us-west-2
```

---

### cluster-info.sh

Get detailed information about a specific cluster.

```bash
./scripts/cluster-info.sh abc123def456
./scripts/cluster-info.sh abc123def456 --region us-west-2
```

**Output:** JSON with cluster identifier, endpoint, ARN, status, and creation time.

---

### loader.sh

Install and run Aurora DSQL Loader for bulk data loading from S3.

```bash
./scripts/loader.sh --source-uri s3://my-bucket/data.parquet --table analytics_data
./scripts/loader.sh --source-uri s3://bucket/data.csv --table my_table --if-not-exists
./scripts/loader.sh --source-uri s3://bucket/data.csv --table my_table --dry-run
./scripts/loader.sh --install-only
```

**Features:**

- Platform detection (Linux/macOS, x86_64/aarch64)
- Binary validation and secure downloads
- Resume interrupted loads with `--resume-job-id`
- Dry run validation with `--dry-run`

---

## Environment Variables

Scripts respect these environment variables:

- `CLUSTER` - Default cluster identifier
- `REGION` - Default AWS region
- `AWS_REGION` - Fallback AWS region if `REGION` not set
- `DB_USER` - Default database user (defaults to 'admin')
- `AWS_PROFILE` - AWS CLI profile to use

## Quick Start Workflow

```bash
# 1. Create a cluster
./scripts/create-cluster.sh --created-by claude-opus-4-6 --region us-east-1

# Copy the export commands from output
export CLUSTER=abc123def456
export REGION=us-east-1

# 2. Connect with psql
./scripts/psql-connect.sh

# 3. Inside psql, create a table
CREATE TABLE entities (
  entity_id VARCHAR(255) PRIMARY KEY,
  tenant_id VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL
);

# 4. Exit psql and run a query from command line
./scripts/psql-connect.sh --command "SELECT * FROM information_schema.tables WHERE table_schema='public'"

# 5. When done, delete the cluster
./scripts/delete-cluster.sh $CLUSTER
```

## Notes

- **Token Expiry:** IAM auth tokens expire after 15 minutes.
- **Connection Limit:** DSQL supports up to 10,000 concurrent connections per cluster.
- **Database Name:** Always use `postgres` (only database available in DSQL).
