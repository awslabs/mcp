---
inclusion: manual
---

# Aurora DSQL Get Started Guide

## Overview

This guide provides steps to help users get started with Aurora DSQL in their project. It sets up their DSQL cluster with IAM authentication and connects their database to their code by understanding the context within the codebase.

## Use Case

These guidelines apply when users say "Get started with DSQL" or similar phrases. The user's codebase may be mature (with existing database connections) or have little to no code - the guidelines should apply to both cases.

## Agent Communication Style

**Keep all responses succinct:**
- ALWAYS tell the user what you did.
  - Responses MUST be concise and concrete.
  - ALWAYS contain descriptions to necessary steps.
  - ALWAYS remove unnecessary verbiage.
  - Example:
    - "Created an inventory table with 4 columns"
    - "Updated the product column to be NOT NULL"
- Ask direct questions when needed:
  - ALWAYS ask clarifying questions to avoid inaccurate assumptions
  - User ambiguity SHOULD result in questions.
  - MUST clarify incompatible user decisions
  - Example:
    - "What column names would you like in this table?"
    - "What is the column name of the primary key?"
    - "JSON must be serialized. Would you like to stringify the JSON to serialize it as TEXT?"

**Examples:**

- **Good**: "Generated auth token. Ready to connect with psql?"
- **Bad**: "I'm going to generate an authentication token using the AWS CLI which will allow you to connect to your database. This token will be valid for..."

---

## Get Started with DSQL (Interactive Guide)

**TRIGGER PHRASE:** When the user says "Get started with DSQL", "Get started with Aurora DSQL", or similar phrases, provide an interactive onboarding experience by following these steps:

**Before starting:** Let the user know they can pause and resume anytime by saying "Continue with DSQL setup" if they need to come back later.

**RESUME TRIGGER:** If the user says "Continue with DSQL setup" or similar, check what's already configured (AWS credentials, clusters, MCP server, connection tested) and resume from where they left off. Ask them which step they'd like to continue from or analyze their setup to determine automatically.

### Step 1: Verify Prerequisites

**Check AWS credentials:**

```bash
aws sts get-caller-identity
```

**If not configured:**
- Guide them through `aws configure`
- MUST verify IAM permissions include `dsql:CreateCluster`, `dsql:GetCluster`, `dsql:DbConnectAdmin`
- Recommend [`AmazonAuroraDSQLConsoleFullAccess`](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonAuroraDSQLConsoleFullAccess.html) managed policy

**Check PostgreSQL client:**

```bash
psql --version
```

**If missing OR version <=14:**
DSQL requires SNI support from psql >=14.
- macOS: `brew install postgresql@17`
- Linux (Debian/Ubuntu): `sudo apt-get install postgresql-client`
- Linux (RHEL/CentOS/Amazon Linux):
  ```bash
  sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
  sudo yum install -y postgresql17
  ```

### Step 2: Check for Existing Clusters

**Set region (uses AWS_REGION or REGION if set, defaults to us-east-1):**
```bash
REGION=${AWS_REGION:-${REGION:-us-east-1}}
echo $REGION
```

**List clusters in the region:**
```bash
aws dsql list-clusters --region $REGION
```

**If they have NO clusters:**
- Ask: "Would you like to create a new DSQL cluster in $REGION or a different region?"
  - If yes, proceed to create single-region cluster
  - If they want different region, ask which one and update REGION variable

**If they have ANY clusters:**
- List ALL cluster identifiers with creation dates and status
- Ask: "Would you like to use one of these clusters or create a new one?"
  - If using existing, proceed to Step 3.
  - If creating new:
    - "Which region would you like to create a enw cluster in?"
    - Immediately update REGION variable
- Confirm all selections before proceeding.

**Create cluster command (if needed):**

```bash
aws dsql create-cluster --region $REGION --tags Key=Name,Value=my-dsql-cluster
```

**Wait for ACTIVE status** (takes ~60 seconds):

```bash
aws dsql get-cluster --identifier CLUSTER_ID --region $REGION
```

### Step 3: Get Cluster Connection Details

**Construct cluster endpoint:**

```bash
CLUSTER_ID="<selected-cluster-id>"
CLUSTER_ENDPOINT="${CLUSTER_ID}.dsql.${REGION}.on.aws"
echo $CLUSTER_ENDPOINT
```

**Store endpoint for their project environment:**
- Check for `.env` file or environment config
- Add or update: `DSQL_ENDPOINT=<endpoint>`
- Add region: `AWS_REGION=$REGION`
- ALWAYS try reading `.env` first before modifying
- If file is unreadable, use: `echo "DSQL_ENDPOINT=$CLUSTER_ENDPOINT" >> .env`

### Step 4: Set Up MCP Server (Optional)

Would the user like to be guided through setting up the MCP server?

If so, follow the steps detailed in [mcp-setup.md](./mcp-setup.md)

**MCP server provides:**
- Direct query execution from agent
- Schema exploration tools
- Simplified database operations

### Step 5: Test Connection

**Generate authentication token and connect:**

```bash
export PGPASSWORD=$(aws dsql generate-db-connect-admin-auth-token \
  --region $REGION \
  --hostname $CLUSTER_ENDPOINT \
  --expires-in 3600)

export PGSSLMODE=require

psql --quiet -h $CLUSTER_ENDPOINT -U admin -d postgres
```

**Verify with test query:**

```sql
SELECT current_database(), version();
```

**If connection fails:**
- Check token expiration (regenerate if needed)
- Verify SSL mode is set
- Confirm cluster is ACTIVE
- Check IAM permissions

### Step 6: Understand the Project

**First, check if this is an empty/new project:**
- Look for existing source code, routes, or application logic
- Check if it's just minimal boilerplate

**If empty or near-empty project:**
- Ask briefly (1-2 questions): What are they building? Any specific tech preferences?
- Remember context for subsequent steps

**If established project:**
- Skip questions - infer from codebase
- Check for existing database code or ORMs
- Update relevant code to use DSQL

**ALWAYS reference [`./development-guide.md`](./development-guide.md) before making schema changes**

### Step 7: Install Database Driver

**Based on their language, install appropriate driver (some examples):**

**JavaScript/TypeScript:**
```bash
npm install @aws-sdk/credential-providers @aws-sdk/dsql-signer pg tsx
npm install @aws/aurora-dsql-node-postgres-connector
```

**Python:**
```bash
pip install psycopg2-binary
pip install aurora-dsql-python-connector
```

**Go:**
```bash
go get github.com/jackc/pgx/v5
```

**Rust:**
```bash
cargo add sqlx --features postgres,runtime-tokio-native-tls
cargo add aws-sdk-dsql tokio --features full
```

**For implementation patterns, reference [`./dsql-examples.md`](./dsql-examples.md) and [`./language.md`](./language.md)**

### Step 8: Schema Setup

**Check for existing schema:**
- Search for `.sql` files, migration folders, ORM schemas (Prisma, Drizzle, TypeORM)

**If existing schema found:**
- Show what you found
- Ask: "Found existing schema definitions. Want to migrate these to DSQL?"
- If yes, MUST verify DSQL compatibility:
  - No SERIAL types (use UUID or generated values)
  - No foreign keys (implement in application)
  - No array/JSON column types (serialize as TEXT)
  - Reference [`./development-guide.md`](./development-guide.md) for full constraints

**If no schema found:**
- Ask if they want to:
  1. Create simple example table
  2. Design custom schema together
  3. Skip for now

**If creating example table:**

Use MCP server or psql to execute:

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ASYNC idx_users_email ON users(email);
```

**For custom schema:**
- Ask about their app's needs
- Design tables following DSQL constraints
- Reference [`./dsql-examples.md`](./dsql-examples.md) for patterns
- ALWAYS use `CREATE INDEX ASYNC` for all indexes

### Step 9: What's Next

Let them know you're ready to help with more:

"You're all set! Here are some things I can help with - feel free to ask about any of these (or anything else):

- Schema design and migrations following DSQL best practices
- Writing queries with proper tenant isolation
- Connection pooling and token refresh strategies
- Multi-region cluster setup for high availability
- Performance optimization with indexes and query patterns"

### Important Notes:

- ALWAYS be succinct - guide step-by-step without verbose explanations
- ALWAYS check [`./development-guide.md`](./development-guide.md) before schema operations
- ALWAYS use MCP tools for queries when available (with user permission)
- ALWAYS track MCP status throughout the session
- ALWAYS validate DSQL compatibility for existing schemas
- ALWAYS provide working, tested commands
- MUST handle token expiration gracefully (15-minute default, 1-hour recommended)

**MCP Server Workflow:**
- If MCP enabled: Use MCP tools for database operations, continuously update user on cluster state
- If MCP not enabled: Provide CLI commands and manual SQL queries
- Agent must adapt workflow based on MCP availability

---

## DSQL Best Practices

### Critical Constraints

**ALWAYS follow these rules:**

1. **Indexes:** Use `CREATE INDEX ASYNC` - synchronous index creation not supported
2. **Serialization:** Store arrays/JSON as TEXT (comma-separated or JSON.stringify)
3. **Referential Integrity:** Implement foreign key validation in application code
4. **DDL Operations:** Execute one DDL per transaction, no mixing with DML
5. **Transaction Limits:** Maximum 3,000 row modifications, 10 MiB data size per transaction
6. **Token Refresh:** Regenerate auth tokens before 15-minute expiration
7. **SSL Required:** Always set `PGSSLMODE=require` or `sslmode=require`

### DSQL-Specific Features

**Leverage Aurora DSQL capabilities:**

1. **Serverless:** True scale-to-zero with consumption-based pricing
2. **Distributed:** Active-active writes across multiple regions
3. **Strong Consistency:** Immediate read-your-writes across all regions
4. **IAM Authentication:** No password management, automatic token rotation
5. **PostgreSQL Compatible:** Supports a listed 10 [Database Drivers](./development-guide.md#database-drivers)
(#database-drivers), 4 [ORMs](./development-guide.md#object-relational-mapping-orm-libraries), and 3 [Adapters/Dialects](./development-guide.md#adapters-and-dialects) as listed.

**For detailed patterns, see [`./development-guide.md`](./development-guide.md)**

## Additional Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- [Aurora DSQL Starter Kit](https://github.com/awslabs/aurora-dsql-starter-kit/tree/main)
- [Code Samples Repository](https://github.com/aws-samples/aurora-dsql-samples)
- [IAM Authentication Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)
- [Getting Started Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html)
- [PostgreSQL Compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [Incompatible PostgreSQL Features](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html)
- [CloudFormation Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dsql-cluster.html)
