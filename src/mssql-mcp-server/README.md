# AWS Labs MCP Server for Microsoft SQL Server

An AWS Labs Model Context Protocol (MCP) server for Microsoft SQL Server on AWS RDS.

## Features

- Direct SQL Server connections via password authentication (AWS Secrets Manager)
- SQL injection detection and mutating keyword blocking
- Read-only mode enforcement
- Connection pool management with automatic credential refresh

## Tools

- `run_query` — Execute SQL queries against SQL Server
- `get_table_schema` — Fetch table column information from INFORMATION_SCHEMA
- `connect_to_database` — Connect to a SQL Server RDS instance
- `is_database_connected` — Check if a connection exists
- `get_database_connection_info` — List all cached connections

## Usage

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database master \
  --port 1433
```

## Connection Methods

- `MSSQL_PASSWORD` — Uses credentials from AWS Secrets Manager (MasterUserSecret by default)

### Using a custom Secrets Manager secret

By default the server discovers the RDS instance's **MasterUserSecret** by calling
`describe_db_instances`. To connect as a different database user, create your own
secret in AWS Secrets Manager and pass its ARN with `--secret_arn`:

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database master \
  --secret_arn arn:aws:secretsmanager:us-east-1:123456789012:secret:my-readonly-user-AbCdEf
```

The secret must be a JSON object with the following keys (case variations accepted):

| Key | Accepted variants |
|-----|-------------------|
| username | `username`, `user`, `Username` |
| password | `password`, `Password` |

Example secret value:

```json
{
  "username": "mcp_readonly",
  "password": "UseAStrongPassword"  # pragma: allowlist secret
}
```

The `--secret_arn` flag can also be passed at runtime via the `connect_to_database`
MCP tool's `secret_arn` parameter, allowing the LLM to switch credentials without
restarting the server.

## TLS / SSL

By default the server connects with `--ssl_encryption require`, which encrypts the
connection and validates the server certificate against the system CA store.

RDS SQL Server certificates are signed by the **Amazon RDS CA**, which is not included
in the default system trust store. If you see a certificate validation error on first
connection, install the Amazon RDS CA bundle:

**Windows** (PowerShell, run as Administrator)

```powershell
# Download the global RDS CA bundle
Invoke-WebRequest -Uri https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem `
  -OutFile global-bundle.pem

# Import all certificates in the bundle into the Trusted Root store
certutil -addstore "Root" global-bundle.pem
```

**macOS**

```bash
# Download the global RDS CA bundle
curl -O https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

# Import into the macOS system keychain (requires sudo)
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain global-bundle.pem
```

**Linux (Debian/Ubuntu)**

```bash
curl -O https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
sudo cp global-bundle.pem /usr/local/share/ca-certificates/amazon-rds-ca.crt
sudo update-ca-certificates
```

**Linux (RHEL/Amazon Linux)**

```bash
curl -O https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
sudo cp global-bundle.pem /etc/pki/ca-trust/source/anchors/amazon-rds-ca.pem
sudo update-ca-trust
```

After installing the CA cert, restart the MCP server.

### SSH Tunnel

When connecting through an SSH tunnel, the transport is already encrypted end-to-end.
You can disable TLS at the pymssql layer to avoid certificate validation failures:

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --ssl_encryption off
```

## Read-Only Mode

By default the server runs in **read-only mode**. It applies several layers of
protection before a query reaches the database:

1. **Mutating keyword blocking** — rejects queries containing DML/DDL keywords
   (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, MERGE, TRUNCATE, EXEC, GRANT, etc.)
2. **SQL injection pattern detection** — blocks common injection vectors such as
   stacked queries, UNION SELECT, tautologies, WAITFOR DELAY, and calls to system /
   extended / RDS stored procedures (`sp_*`, `xp_*`, `rds_*`).
3. **Transaction isolation** — sets `READ COMMITTED` isolation level.
4. **Autocommit disabled + forced rollback** — in read-only mode, autocommit is off
   and every query is followed by a rollback, so any mutation that slips past the
   keyword filter is never committed.

### Limitations of application-level read-only mode

The keyword and pattern checks are a **best-effort safeguard**, not a security
boundary. They cannot guarantee that no mutation ever reaches the database because:

- A stored procedure that performs writes internally could be invoked via a SELECT
  that doesn't contain any blocked keywords (e.g.
  `SELECT dbo.my_func_that_writes()`).
- Future T-SQL syntax or edge-case encodings might bypass the regex-based detector.

**For true read-only enforcement, use a database user that only has read
permissions.** See [Recommended: database-level read-only user](#recommended-database-level-read-only-user) below.

### Write mode

To allow write queries, pass `--allow_write_query`:

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database master \
  --allow_write_query
```

## Recommended: database-level read-only user

For production use, create a dedicated SQL Server login with only read permissions
and store its credentials in Secrets Manager. This provides a hard security boundary
that cannot be bypassed at the application layer.

### 1. Create the login and user in SQL Server

Connect to your RDS instance as the master user and run:

```sql
-- Create a server-level login
CREATE LOGIN mcp_readonly WITH PASSWORD = 'UseAStrongPassword';  # pragma: allowlist secret

-- Switch to the target database
USE my_database;

-- Create a database user mapped to the login
CREATE USER mcp_readonly FOR LOGIN mcp_readonly;

-- Grant read-only access
ALTER ROLE db_datareader ADD MEMBER mcp_readonly;

-- (Optional) Allow the user to view definitions (table schemas, view text, etc.)
GRANT VIEW DEFINITION TO mcp_readonly;
```

This user can run SELECT queries and read `INFORMATION_SCHEMA` but cannot INSERT,
UPDATE, DELETE, CREATE, DROP, or execute stored procedures.

### 2. Store the credentials in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name mcp/mssql/readonly \
  --description "Read-only SQL Server credentials for MCP server" \
  --secret-string '{"username":"mcp_readonly","password":"UseAStrongPassword"}'  # pragma: allowlist secret
```

Note the ARN in the output.

### 3. Start the MCP server with the custom secret

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database my_database \
  --secret_arn arn:aws:secretsmanager:us-east-1:123456789012:secret:mcp/mssql/readonly-AbCdEf
```

With this setup you get **defense in depth**: the application-level keyword blocker
catches mistakes early and provides clear error messages, while the database-level
permissions prevent any mutation even if a query slips past the detector.

## Notes

- Default port: 1433
- Default TLS mode: `require` (validates server certificate)
- Connection pools expire after 30 minutes and are automatically refreshed
