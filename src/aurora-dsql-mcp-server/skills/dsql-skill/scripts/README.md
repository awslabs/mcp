# Aurora DSQL Scripts

Bash scripts for common Aurora DSQL cluster management and connection operations.

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

## Available Scripts

### create-cluster.sh
Create a new Aurora DSQL cluster.

```bash
# Create cluster in default region
./create-cluster.sh

# Create cluster in specific region
./create-cluster.sh --region us-west-2

# Create cluster with tags
./create-cluster.sh --region us-east-1 --tags Environment=dev,Project=myapp
```

**Output:** Cluster identifier, endpoint, and ARN. Exports environment variables for use with other scripts.

---

### delete-cluster.sh
Delete an existing Aurora DSQL cluster.

```bash
# Delete cluster (with confirmation prompt)
./delete-cluster.sh abc123def456

# Delete cluster in specific region
./delete-cluster.sh abc123def456 --region us-west-2

# Delete cluster without confirmation
./delete-cluster.sh abc123def456 --force
```

**Note:** Deletion is permanent and cannot be undone.

---

### psql-connect.sh
Connect to Aurora DSQL using psql with automatic IAM authentication.

```bash
# Connect using $CLUSTER environment variable
export CLUSTER=abc123def456
export REGION=us-east-1
./psql-connect.sh

# Connect with explicit cluster ID
./psql-connect.sh abc123def456

# Connect in specific region
./psql-connect.sh abc123def456 --region us-west-2

# Connect as a custom database user
./psql-connect.sh --user myuser

# Execute a command and exit
./psql-connect.sh --command "SELECT * FROM entities LIMIT 5"

# Generate admin auth token (for DDL operations)
./psql-connect.sh --admin
```

**Features:**
- Automatically generates IAM auth token (valid for 15 minutes)
- Supports both interactive sessions and command execution
- Uses `admin` user by default (override with `--user` or `$DB_USER`)
- Respects `$CLUSTER`, `$REGION`, and `$DB_USER` environment variables

---

### list-clusters.sh
List all Aurora DSQL clusters in a region.

```bash
# List clusters in default region
./list-clusters.sh

# List clusters in specific region
./list-clusters.sh --region us-west-2
```

**Output:** Table of cluster identifiers, endpoints, and status.

---

### cluster-info.sh
Get detailed information about a specific cluster.

```bash
# Get cluster info
./cluster-info.sh abc123def456

# Get cluster info in specific region
./cluster-info.sh abc123def456 --region us-west-2
```

**Output:** JSON with cluster identifier, endpoint, ARN, status, and creation time.

---

## Quick Start Workflow

```bash
# 1. Create a cluster
./create-cluster.sh --region us-east-1

# Copy the export commands from output
export CLUSTER=abc123def456
export REGION=us-east-1

# 2. Connect with psql
./psql-connect.sh

# 3. Inside psql, create a table
CREATE TABLE entities (
  entity_id VARCHAR(255) PRIMARY KEY,
  tenant_id VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL
);

# 4. Exit psql and run a query from command line
./psql-connect.sh --command "SELECT * FROM information_schema.tables WHERE table_schema='public'"

# 5. When done, delete the cluster
./delete-cluster.sh $CLUSTER
```

## Environment Variables

Scripts respect these environment variables:

- `CLUSTER` - Default cluster identifier (used by psql-connect.sh)
- `REGION` - Default AWS region (used by all scripts)
- `AWS_REGION` - Fallback AWS region if `REGION` not set
- `DB_USER` - Default database user (used by psql-connect.sh, defaults to 'admin')
- `AWS_PROFILE` - AWS CLI profile to use (standard AWS CLI behavior)

## Error Handling

All scripts:
- Use `set -euo pipefail` for strict error handling
- Validate required arguments
- Provide helpful error messages
- Include `--help` option for usage information

## Notes

- **Token Expiry:** IAM auth tokens expire after 15 minutes. For long-running psql sessions, you'll need to reconnect.
- **Connection Limit:** DSQL supports up to 10,000 concurrent connections per cluster.
- **Database Name:** Always use `postgres` (only database available in DSQL).
- **Database Users:** Scripts default to `admin` user. You can create custom database users and roles with `CREATE USER` and `GRANT` statements. IAM authentication is used to connect as any database user - the IAM token is generated for a specific database user.
