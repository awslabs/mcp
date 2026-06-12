# Amazon RDS for Db2 MCP Server

An AWS Labs Model Context Protocol (MCP) server for Amazon RDS for Db2. It lets an
MCP-aware assistant **connect** to RDS for Db2 instances over SSL and **run read-only
SQL** — turning natural-language questions into Db2 queries.

> **Scope.** This server handles *connect, query, and schema inspection*. It does **not**
> provision Db2 instances. Provisioning is owned by the companion
> `rds-db2-provision-skill` (a Terraform composer/orchestrator). Together they cover the
> full **deploy → connect → query** journey, each in its proper layer.

## Features

- **`connect_to_database`** — open and cache an SSL connection using credentials pulled from
  AWS Secrets Manager.
- **`run_query`** — run a parameterized SQL query (read-only by default).
- **`get_table_schema`** — fetch column metadata from `SYSCAT.COLUMNS`.
- **`is_database_connected`** / **`get_database_connection_info`** — inspect cached connections.

### Read-only by default

The server starts in read-only mode. Mutating statements (`INSERT`, `UPDATE`, `DELETE`,
DDL, `CALL ... ADMIN_CMD`, etc.), transaction-control bypasses, and common SQL-injection
patterns are rejected before execution; the connection runs with autocommit off and rolls
back after every query. Pass `--allow_write_query` to permit writes.

## Connectivity & SSL

RDS for Db2 is reached over a private endpoint inside your VPC. In the Db2 tooling
ecosystem the instance is **SSL-only**: `DB2COMM=SSL`, `ssl_svcename=50443`, and the plain
TCP listener (`8392`) is dormant and closed in the security group. This server therefore
**defaults to SSL on port 50443**.

SSL uses the IBM driver's `SSLServerCertificate` option pointed at the RDS **regional
certificate bundle (PEM)** — no Java keystore or `keytool` required. Download the bundle
for your region and pass its path with `--ssl_server_certificate`.

- Client setup (CloudShell / EC2): [Connect to Amazon RDS for Db2 using AWS CloudShell](https://aws.amazon.com/blogs/database/connect-to-amazon-rds-for-db2-using-aws-cloudshell/)
- SSL without a keystore (the approach used here): [Create an SSL connection to Amazon RDS for Db2 in Java without keystore or keytool](https://aws.amazon.com/blogs/database/create-an-ssl-connection-to-amazon-rds-for-db2-in-java-without-keystore-or-keytool/)

Content from the linked blogs was summarized; see the originals for full detail.

## Prerequisites

1. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.10+.
2. AWS credentials with permission to call `rds:DescribeDBInstances` and
   `secretsmanager:GetSecretValue` for the target instance/secret.
3. Network reachability to the instance endpoint on port 50443 (same VPC, peered VPC, or
   tunnel), and the RDS regional SSL certificate bundle.
4. The IBM `ibm_db` driver is installed automatically as a dependency.

## Installation

Add this to your MCP client configuration (e.g. Kiro, Cline, Cursor, Claude Desktop):

```json
{
  "mcpServers": {
    "awslabs.db2-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.db2-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

To pre-connect a single instance at startup, pass arguments after the package name:

```json
{
  "mcpServers": {
    "awslabs.db2-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.db2-mcp-server@latest",
        "--region", "us-east-1",
        "--db_endpoint", "db2.abc123.us-east-1.rds.amazonaws.com",
        "--database", "DB2DB",
        "--ssl_server_certificate", "/path/to/us-east-1-bundle.pem"
      ],
      "env": {"AWS_PROFILE": "your-profile", "FASTMCP_LOG_LEVEL": "ERROR"},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Command-line options

| Option | Default | Description |
|---|---|---|
| `--region` | — | AWS region (required if `--db_endpoint` is set) |
| `--db_endpoint` | — | Db2 endpoint to pre-connect and validate at startup |
| `--instance_identifier` | first DNS label of `db_endpoint` | RDS instance identifier |
| `--database` | `DB2DB` | Db2 database name |
| `--port` | `50443` (SSL) / `50000` (off) | Db2 port |
| `--secret_arn` | RDS managed master secret | Secrets Manager ARN for credentials |
| `--ssl_encryption` | `require` | `require` (SSL) or `off` (plain TCP) |
| `--ssl_server_certificate` | — | Path to the RDS regional PEM bundle |
| `--ssl_hostname_validation` | `basic` | `basic` validates the cert hostname; `off` disables it (tunnel testing only) |
| `--allow_write_query` | off | Permit non-SELECT statements |
| `--max_rows` | `1000` | Max rows per query (0 = no limit) |
| `--query_timeout_s` | `30` | Per-query timeout in seconds (0 = none) |

## The deploy → connect → query journey

1. **Deploy** with the `rds-db2-provision-skill` (Terraform). It produces an instance with a
   managed master-user secret and SSL on 50443. Note its endpoint and master-secret ARN.
2. **Connect** with `connect_to_database`.
3. **Query** with `run_query` / `get_table_schema`.

## Related resources

- `rds-db2-provision-skill` — the Terraform composer that deploys RDS for Db2.
- [Deploying Amazon RDS for Db2 using Terraform](https://aws.amazon.com/blogs/database/deploying-amazon-rds-for-db2-using-terraform/) — the published Terraform modules the provisioning skill reuses.
- [Create a monitoring dashboard for Amazon RDS for Db2](https://aws.amazon.com/blogs/database/create-monitoring-dashboard-for-amazon-rds-for-db2/) — basis for a planned phase-2 monitoring toolset.
- [Connect to Amazon RDS for Db2 from your laptop](https://aws.amazon.com/blogs/database/connect-to-amazon-rds-for-db2-from-your-laptop/) — EC2 + SSM tunnel approach used in the testing section above.
- [`aws-samples/sample-rds-db2-tools`](https://github.com/aws-samples/sample-rds-db2-tools) — companion scripts, skills, and examples.

## Development

```shell
uv venv && uv sync --all-groups
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing   # unit tests
uv run --frozen pytest -m live                                        # live tests (needs an instance)
```

## Testing over an SSM tunnel

RDS for Db2 instances are private (not publicly accessible), so a laptop usually
cannot reach the endpoint on 50443 directly. Use a small EC2 instance in the same
VPC as an SSM port-forwarding proxy — no inbound ports or SSH keys required.

Reference: [Connect to Amazon RDS for Db2 from your laptop](https://aws.amazon.com/blogs/database/connect-to-amazon-rds-for-db2-from-your-laptop/).

Prerequisites: an SSM-managed EC2 in the instance's VPC whose security group is
allowed to reach the DB on the SSL port (50443), the AWS CLI **Session Manager
plugin**, and the RDS regional certificate bundle (PEM).

```shell
# 1. Download the regional certificate bundle
curl -o us-east-1-bundle.pem https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem

# 2. Open a port-forwarding tunnel: local 50443 -> RDS endpoint:50443 via the EC2 proxy
aws ssm start-session --region us-east-1 --target <ec2-instance-id> \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters host="<rds-endpoint>",portNumber="50443",localPortNumber="50443"
```

The Db2 v12 client driver defaults `SSLClientHostnameValidation` to `BASIC`, so it
validates the certificate's hostname. Over a tunnel you connect to `127.0.0.1`,
which cannot match the certificate CN — that fails with `SQL20576N`. For tunnel
testing, disable hostname validation with `--ssl_hostname_validation off` (the
`RDS_DB2_SSL_HOSTNAME_VALIDATION=off` env var below). Keep it on in production,
where the server connects to the real endpoint and the hostname matches.

```shell
# 3. Run the live test through the tunnel
RDS_DB2_ENDPOINT=127.0.0.1 \
RDS_DB2_PORT=50443 \
RDS_DB2_REGION=us-east-1 \
RDS_DB2_DATABASE=DB2DB \
RDS_DB2_SECRET_ARN=<master-user-secret-arn> \
RDS_DB2_SSL=require \
RDS_DB2_SSL_HOSTNAME_VALIDATION=off \
RDS_DB2_SSL_CERT=$(pwd)/us-east-1-bundle.pem \
uv run --frozen pytest -m live -q
```

Clean up afterward: end the SSM session (Ctrl-C). No `/etc/hosts` change is needed.

## Security

- Credentials are read from AWS Secrets Manager and are never logged.
- Connections use SSL by default; prefer keeping `--ssl_encryption require`.
- The server is read-only unless `--allow_write_query` is explicitly set.

## License

Licensed under the Apache License, Version 2.0.
