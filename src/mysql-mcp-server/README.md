# AWS Labs MySQL MCP Server

An AWS Labs Model Context Protocol (MCP) server for Aurora MySQL

## Features

### Natural language to MySQL SQL query

Converting human-readable questions and commands into structured MySQL-compatible SQL queries and executing them against the configured Aurora MySQL database.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. This MCP server can only be run locally on the same host as your LLM client.
4. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Installation

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.mysql-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.mysql-mcp-server@latest",
        "--allow_write_query"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.mysql-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.mysql-mcp-server@latest",
        "awslabs.mysql-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

NOTE: the MCP config examples include --allow_write_query to illustrate how to enable write queries. If you want to disable write queries, remove the --allow_write_query option.

## Support for Database Cluster Creation

You can use the following LLM prompt to create a new Aurora MySQL cluster:

> Create an Aurora MySQL cluster named 'mycluster' in us-west-2 region

---

## Connection Methods

The MCP server supports connecting to multiple database endpoints using different connection methods via LLM prompts.

### Database Types

These engine values match AWS RDS API engine strings, so they can be passed
through to `aws rds` calls without translation:

- **aurora-mysql**: Amazon Aurora MySQL
- **mysql**: Amazon RDS for MySQL
- **mariadb**: Amazon RDS for MariaDB

Self-hosted MySQL/MariaDB endpoints don't need a `database_type` — connect
directly via `mysqlwire` with the endpoint, port, and credentials.

### Example Prompts

**Connect using RDS Data API:**
> Connect to database named mydb in Aurora MySQL cluster 'my-cluster' with database_type as aurora-mysql, using rdsapi as connection method in us-west-2 region

**Connect using mysqlwire (Aurora MySQL):**
> Connect to database named mydb with database endpoint as my-amy-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com with database_type as aurora-mysql, using mysqlwire as connection method in us-west-2 region

**Connect using mysqlwire (RDS MySQL):**
> Connect to database named mydb with database endpoint as test-rds-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com with database_type as mysql, using mysqlwire as connection method in us-west-2 region

**Connect using mysqlwire (RDS MariaDB):**
> Connect to database named mydb with database endpoint as test-mariadb-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com with database_type as mariadb, using mysqlwire as connection method in us-west-2 region

---

### Supported Connection Methods

| Method | Description | aurora-mysql | mysql | mariadb |
|--------|-------------|:-:|:-:|:-:|
| `rdsapi` | Connect to Aurora MySQL using the RDS Data API. Requires Data API enabled on the cluster. | ✓ | ✗ | ✗ |
| `mysqlwire` | Connect directly using the MySQL wire protocol. Requires VPC connectivity. | ✓ | ✓ | ✓ |
| `mysqlwire_iam` | Wire protocol with IAM authentication. Requires IAM auth enabled on the cluster. | ✓ | ✓ | ✗ |

### Prerequisites by Connection Method

#### mysqlwire / mysqlwire_iam
- VPC security group must allow inbound connections from your MCP server to the database
- For `mysqlwire_iam`: IAM authentication must be enabled on the Aurora MySQL cluster

#### rdsapi
- RDS Data API must be enabled on the Aurora MySQL cluster
- Appropriate IAM permissions for Data API access

### AWS Authentication

The MCP server uses the AWS profile specified in the AWS_PROFILE environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

Make sure the AWS profile has permissions to access the RDS Data API, and the secret from AWS Secrets Manager. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.

## Development setup

This package ships the Amazon RDS global CA bundle inside the wheel so IAM
authenticated connections (`mysqlwire_iam`) can perform strict TLS
verification out of the box. The PEM itself is not checked into source
control; it is fetched at build time by `hatch_build.py`.

### Why the bundle is fetched at build time

AWS rotates the RDS global CA bundle without notice. Keeping the PEM out
of source control avoids committing binary blobs to code review, and lets
the build hook automatically pick up the latest bundle from
`https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` on
every build. Runtime TLS validation against the bundled CA handles cert
chain and FQDN matching in the usual way.

### Running the build hook

`uv build`, `uv sync`, `pip wheel`, and `pip install` from source all
invoke the hook automatically. The hook is idempotent: if the PEM is
already on disk, it skips the fetch.

To run the hook standalone (for example, to populate the PEM in an
editable checkout that has not yet been built):

```bash
python hatch_build.py
```

This writes the bundle to
`awslabs/mysql_mcp_server/connection/rds_global_bundle.pem`.

### Building offline

If the build machine cannot reach `truststore.pki.rds.amazonaws.com`,
the hook fails with an error that includes a `curl` recovery command.
Run that on a connected host once and rerun the build; the hook will
use the placed file.

### Optional: override the CA bundle at runtime

Pass `--ca_bundle <path>` to the server to use a PEM other than the one
bundled with the package. Useful for enterprises that maintain their own
trust store, or if AWS rotates the CA faster than a new wheel is published:

```bash
uvx awslabs.mysql-mcp-server@latest --ca_bundle /path/to/custom.pem
```
