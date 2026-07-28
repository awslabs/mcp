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

## Security model

> **The server's read-only mode is a best-effort SQL-text safeguard, not a security boundary.**

When the MCP server runs without `--allow_write_query`, it inspects the SQL string for mutating keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `SET`, `CALL`, `PREPARE`, `EXECUTE`, `HANDLER`, `LOCK`, `FLUSH`, `RESET`, `KILL`, `INSTALL`, `UNINSTALL`, etc.) and rejects matches before they reach the database. This guard is defence in depth — it is not a guarantee. SQL grammars evolve, regular expressions have edge cases, and an LLM under prompt injection is a creative adversary.

**The actual security boundary is the database role you connect with.** The Postgres, MSSQL, and Oracle sibling servers all carry the same caveat; this section aligns the MySQL package with that wording.

### Recommended configuration

Connect with a least-privilege MySQL user that has only the permissions your workload actually needs. For read-only workflows, grant `SELECT` (and `EXECUTE` on specific procedures, if any) at the database level:

```sql
-- Aurora MySQL / RDS MySQL / RDS MariaDB
CREATE USER 'mcp_readonly'@'%' IDENTIFIED BY '...';
GRANT SELECT ON your_database.* TO 'mcp_readonly'@'%';
-- If the workflow legitimately needs specific stored procedures:
GRANT EXECUTE ON PROCEDURE your_database.some_safe_proc TO 'mcp_readonly'@'%';
FLUSH PRIVILEGES;
```

Or, for IAM authentication, attach a policy granting `rds-db:connect` for the dedicated read-only user only.

With a least-privilege role in place, every mutating statement the regex might miss still fails at the database with `ERROR 1142 (42000): … command denied to user`. The server's regex serves as a fast, informative rejection at the MCP layer; the database role is the durable guarantee.

### What the server-side regex does and does not catch

| Catches | Does not catch |
|---------|----------------|
| Single mutating statements (`INSERT`, `UPDATE`, `DELETE`, DDL, GRANT/REVOKE, etc.) | Mutating logic inside an `EXECUTE` of a `PREPARE`'d statement whose body lives in a `@user_variable` (defence: `PREPARE`, `EXECUTE`, `DEALLOCATE` are themselves blocked) |
| Stacked queries (`SELECT 1; INSERT …`, `SELECT 1; COMMIT; INSERT …`) | Mutating logic inside a stored procedure that this server isn't aware of (defence: `CALL` is blocked) |
| Toggling integrity-control session variables (`SET sql_log_bin = 0`, `SET foreign_key_checks = 0`, `SET unique_checks = 0`) in **both** read-only and write modes | Quoted-identifier obfuscation of variable names |
| MySQL conditional comment payloads (`/*!50000 INSERT … */`) | A trojaned UDF that has already been installed by a higher-privileged operator |
| Multi-variable `SET` with the dangerous variable in any position (`SET @x = 1, sql_log_bin = 0`) | New mutating verbs introduced by future MySQL releases until added to the denylist |

When in doubt, rely on the database role.

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
