# AWS Labs MCP Server for Oracle Database

An AWS Labs Model Context Protocol (MCP) server for Oracle Database on AWS RDS.

## Features

- Direct Oracle connections via password authentication (AWS Secrets Manager)
- SQL injection detection and Oracle-specific mutating keyword blocking
- Read-only transaction enforcement using `SET TRANSACTION READ ONLY`
- Connection pool management using python-oracledb thin mode (no Oracle Instant Client needed)
- Support for both service_name and SID connection styles
- TLS encryption with certificate validation by default (`--ssl_encryption require`)

## Tools

- `run_query` — Execute SQL queries against Oracle Database
- `get_table_schema` — Fetch table column information from ALL_TAB_COLUMNS
- `connect_to_database` — Connect to an Oracle RDS instance
- `is_database_connected` — Check if a connection exists
- `get_database_connection_info` — List all cached connections

## Usage

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL
```

## Connection Methods

- `ORACLE_PASSWORD` — Uses credentials from AWS Secrets Manager (MasterUserSecret by default)

### Using a custom Secrets Manager secret

By default the server discovers the RDS instance's **MasterUserSecret** by calling
`describe_db_instances`. To connect as a different database user, create your own
secret in AWS Secrets Manager and pass its ARN with `--secret_arn`:

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
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

## TLS / SSL

By default the server connects with `--ssl_encryption require`, which encrypts the
connection using Oracle TCPS and validates the server certificate against the system CA
store.

RDS Oracle certificates are signed by the **Amazon RDS CA**, which is not included
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

### Port Forwarding / SSH Tunnel

Oracle TCPS (TLS) listens on port **2484** by default. Standard unencrypted Oracle TCP
uses port **1521**. When using an SSH tunnel with TLS, tunnel port 2484 (not 1521):

```bash
ssh -N \
  -L 2484:my-instance.xxxx.rds.amazonaws.com:2484 \
  ec2-user@<bastion-ip>
```

> **Security group requirement:** the EC2 bastion's security group must be allowed as
> an inbound source on port 2484 in the Oracle RDS security group.

Then connect with `--ssl_encryption noverify` to keep TLS encryption while skipping
certificate and hostname verification (the cert won't match `localhost`):

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint localhost \
  --port 2484 \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --ssl_encryption noverify
```

To disable TLS entirely (e.g., tunneling port 1521 and the SSH connection provides encryption):

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint localhost \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --ssl_encryption off
```

### `--ssl_encryption` options

| Value | Behavior |
|-------|----------|
| `require` | *(default)* TCPS on port 2484. Encrypts the connection and validates the server certificate against the system CA store. |
| `noverify` | TCPS on port 2484. Encrypts the connection but skips certificate and hostname verification. Use when connecting via SSH tunnel or when the RDS CA is not installed locally. |
| `off` | Plain TCP on port 1521. No encryption. Use only when the transport is already secured (e.g., SSH tunnel) or in isolated test environments. |

## Read-Only Mode

By default the server runs in **read-only mode**. It applies several layers of
protection before a query reaches the database:

1. **Mutating keyword blocking** — rejects queries containing DML/DDL keywords
   (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, GRANT, REVOKE, AUDIT,
   FLASHBACK, LOCK TABLE, BEGIN, DECLARE, etc.)
2. **SQL injection pattern detection** — blocks Oracle-specific injection vectors such as
   EXECUTE IMMEDIATE, ALTER SYSTEM/SESSION, DBMS_* / UTL_* packages, XMLTYPE XXE,
   alternative quoting, SYS internal tables, v$/gv$/dba_ views, HTTPURITYPE/URITYPE
   SSRF, CTXSYS, and CONNECT BY tautologies.
3. **Transaction control blocking** — rejects COMMIT, ROLLBACK, SAVEPOINT, and
   SET TRANSACTION statements in read-only mode.
4. **SET TRANSACTION READ ONLY** — every query is executed inside a read-only
   transaction, so any mutation that slips past the keyword filter is rejected by
   the database itself.

### Limitations of application-level read-only mode

The keyword and pattern checks are a **best-effort safeguard**, not a security
boundary. They cannot guarantee that no mutation ever reaches the database because:

- A PL/SQL function that performs writes internally could be invoked via a SELECT
  that doesn't contain any blocked keywords (e.g.
  `SELECT my_func_that_writes() FROM DUAL`).
- Future Oracle SQL syntax or edge-case encodings might bypass the regex-based detector.

**For true read-only enforcement, use a database user that only has read
permissions.** See [Recommended: database-level read-only user](#recommended-database-level-read-only-user) below.

### Write mode

To allow write queries, pass `--allow_write_query`:

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --allow_write_query
```

## Recommended: database-level read-only user

For production use, create a dedicated Oracle user with only read permissions
and store its credentials in Secrets Manager. This provides a hard security boundary
that cannot be bypassed at the application layer.

### 1. Create the read-only user in Oracle

Connect to your RDS instance as the master user and run:

```sql
-- Create a read-only user
CREATE USER mcp_readonly IDENTIFIED BY "UseAStrongPassword";  -- pragma: allowlist secret

-- Allow the user to connect
GRANT CREATE SESSION TO mcp_readonly;

-- Grant read access to specific schemas (repeat for each schema)
GRANT SELECT ANY TABLE TO mcp_readonly;

-- (Optional) Restrict to specific tables instead of SELECT ANY TABLE
-- GRANT SELECT ON hr.employees TO mcp_readonly;
-- GRANT SELECT ON hr.departments TO mcp_readonly;

-- (Optional) Allow the user to view table definitions in ALL_TAB_COLUMNS
-- This is granted implicitly when SELECT access exists on the tables.
```

This user can run SELECT queries and read `ALL_TAB_COLUMNS` but cannot INSERT,
UPDATE, DELETE, CREATE, DROP, or execute PL/SQL procedures.

### 2. Store the credentials in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name mcp/oracle/readonly \
  --description "Read-only Oracle credentials for MCP server" \
  --secret-string '{"username":"mcp_readonly","password":"UseAStrongPassword"}'  # pragma: allowlist secret
```

Note the ARN in the output.

### 3. Start the MCP server with the custom secret

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --secret_arn arn:aws:secretsmanager:us-east-1:123456789012:secret:mcp/oracle/readonly-AbCdEf
```

With this setup you get **defense in depth**: the application-level keyword blocker
catches mistakes early and provides clear error messages, while the database-level
permissions prevent any mutation even if a query slips past the detector.

## Notes

- RDS for Oracle does not support the RDS Data API; only direct connections are supported.
- Uses python-oracledb thin mode — no Oracle Instant Client installation required.
- Either `--service_name` or `--sid` must be provided (not both).
- Oracle system catalog stores table names in UPPERCASE. Table names passed to `get_table_schema` are automatically uppercased.
- Default port: 1521 (TCP). Oracle TCPS (TLS) typically uses port 2484 — pass `--port 2484` when connecting with `--ssl_encryption require` or `noverify`.
- Connection pools expire after 30 minutes and are automatically refreshed
