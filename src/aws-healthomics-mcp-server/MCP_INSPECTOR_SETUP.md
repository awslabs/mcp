# MCP Inspector Setup Guide for AWS HealthOmics MCP Server

This guide provides step-by-step instructions for setting up and running the MCP Inspector with the AWS HealthOmics MCP server for development and testing purposes.

## Overview

The MCP Inspector is a web-based tool that allows you to interactively test and debug MCP servers. It provides a user-friendly interface to explore available tools, test function calls, and inspect responses.

## Prerequisites

Before starting, ensure you have the following installed:

1. **uv** (Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Node.js and npm** (for MCP Inspector):
   - Download from [nodejs.org](https://nodejs.org/) or use a package manager

3. **MCP Inspector** (no installation needed, runs via npx):
   ```bash
   # No installation required - runs directly via npx
   npx @modelcontextprotocol/inspector --help
   ```

4. **AWS CLI** (configured with appropriate credentials):
   ```bash
   aws configure
   ```

## Setup Methods

### Method 1: Using Source Code (Recommended for Development)

This method is ideal when you're developing or modifying the HealthOmics MCP server.

1. **Navigate to the HealthOmics server directory** (IMPORTANT - must be in this directory):
   ```bash
   cd src/aws-healthomics-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:

   **Option A: Create a `.env` file** in the server directory:
   ```bash
   cat > .env << EOF
   export AWS_REGION=us-east-1
   export AWS_PROFILE=your-aws-profile
   export FASTMCP_LOG_LEVEL=DEBUG
   export HEALTHOMICS_DEFAULT_MAX_RESULTS=10
   export GENOMICS_SEARCH_S3_BUCKETS=s3://your-genomics-bucket/,s3://another-bucket/
   EOF
   ```

   **Option B: Export them directly**:
   ```bash
   export AWS_REGION=us-east-1
   export AWS_PROFILE=your-aws-profile
   export FASTMCP_LOG_LEVEL=DEBUG
   export HEALTHOMICS_DEFAULT_MAX_RESULTS=10
   export GENOMICS_SEARCH_S3_BUCKETS=s3://your-genomics-bucket/,s3://another-bucket/
   ```

4. **Start the MCP Inspector with source code** (run from `src/aws-healthomics-mcp-server` directory):

   **Option A: Using .env file (recommended)**:
   ```bash
   # Source the .env file to load environment variables
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Option B: Using .env file with one command**:
   ```bash
   # Load .env and run in one command
   source .env && npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Option C: Using MCP Inspector's environment variable support**:
   ```bash
   npx @modelcontextprotocol/inspector \
     -e AWS_REGION=us-east-1 \
     -e AWS_PROFILE=your-profile \
     -e FASTMCP_LOG_LEVEL=DEBUG \
     -e HEALTHOMICS_DEFAULT_MAX_RESULTS=100 \
     -e GENOMICS_SEARCH_S3_BUCKETS=s3://your-bucket/ \
     uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Option D: Direct execution without .env**:
   ```bash
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Important**: You must run these commands from the `src/aws-healthomics-mcp-server` directory for the module imports to work correctly.

### Method 2: Using the Installed Package

This method uses the published package, suitable for testing the released version.

1. **Install the server globally**:
   ```bash
   uvx install awslabs.aws-healthomics-mcp-server
   ```

2. **Set environment variables**:
   ```bash
   export AWS_REGION=us-east-1
   export AWS_PROFILE=your-aws-profile
   export FASTMCP_LOG_LEVEL=DEBUG
   export HEALTHOMICS_DEFAULT_MAX_RESULTS=10
   export GENOMICS_SEARCH_S3_BUCKETS=s3://your-genomics-bucket/
   ```

3. **Start the MCP Inspector**:
   ```bash
   npx @modelcontextprotocol/inspector uvx awslabs.aws-healthomics-mcp-server
   ```

### Method 3: Using a Configuration File

This method allows you to save your configuration for repeated use.

1. **Create a configuration file** (`healthomics-inspector-config.json`):

   **For source code development**:
   ```json
   {
     "command": "uv",
     "args": ["run", "-m", "awslabs.aws_healthomics_mcp_server.server"],
     "env": {
       "AWS_REGION": "us-east-1",
       "AWS_PROFILE": "your-aws-profile",
       "FASTMCP_LOG_LEVEL": "DEBUG",
       "HEALTHOMICS_DEFAULT_MAX_RESULTS": "10",
       "GENOMICS_SEARCH_S3_BUCKETS": "s3://your-genomics-bucket/,s3://shared-references/"
     }
   }
   ```

   **Alternative for direct Python execution**:
   ```json
   {
     "command": "uv",
     "args": ["run", "python", "awslabs/aws_healthomics_mcp_server/server.py"],
     "env": {
       "AWS_REGION": "us-east-1",
       "AWS_PROFILE": "your-aws-profile",
       "FASTMCP_LOG_LEVEL": "DEBUG",
       "HEALTHOMICS_DEFAULT_MAX_RESULTS": "10",
       "GENOMICS_SEARCH_S3_BUCKETS": "s3://your-genomics-bucket/,s3://shared-references/"
     }
   }
   ```

2. **Start the inspector with the config**:
   ```bash
   npx @modelcontextprotocol/inspector --config healthomics-inspector-config.json
   ```

## Transport Modes

The server supports three transports, selected with the `--transport` flag or the `MCP_TRANSPORT` environment variable. A non-empty CLI flag always wins over the matching environment variable.

| Transport | Value | Description | Inspector connection |
|-----------|-------|-------------|----------------------|
| Standard I/O | `stdio` (default) | The inspector launches and talks to the server over stdin/stdout. This is what all the examples above use. | Inspector spawns the command directly |
| Streamable HTTP | `streamable-http` | The server listens on a TCP socket and serves the streamable-HTTP protocol. | Connect the inspector to the server URL |
| Server-Sent Events | `sse` | The server listens on a TCP socket and serves the SSE protocol. | Connect the inspector to the server URL |

### Network Bind Settings

For the network transports (`streamable-http` and `sse`) you can control where the server binds:

| Setting | CLI flag | Environment variable | Default |
|---------|----------|----------------------|---------|
| Transport | `--transport` | `MCP_TRANSPORT` | `stdio` |
| Bind host | `--host` | `MCP_HOST` | `127.0.0.1` (loopback) |
| Bind port | `--port` | `MCP_PORT` | `8000` |
| Request path | `--path` | `MCP_PATH` | `/mcp` |

Notes:
- Host/port/path only apply to network transports. They are ignored for `stdio`.
- The host must be a valid IPv4 address, IPv6 address, or hostname; the port must be an integer in `1-65535`. Invalid values cause the server to exit without binding.

### Secure-by-default Exposure

Network transports bind to the loopback address (`127.0.0.1`) by default. Binding to a non-loopback host still starts the server, but emits a startup warning: the server performs no inbound authentication of its own, so non-loopback exposure requires an external fronting authentication layer (for example SigV4 via `mcp-proxy-for-aws`, a reverse proxy, an API gateway, or hosting on Amazon Bedrock AgentCore Runtime, which terminates JWT or IAM authentication at its boundary). Keep the server on loopback for local inspector testing. See the README's "Securing non-loopback exposure" section for production fronting options.

### Running a Network Transport for the Inspector

Because the inspector connects to a network transport over a URL, start the server and the inspector separately.

1. **Start the server** in one terminal (from `src/aws-healthomics-mcp-server`):

   Streamable HTTP:
   ```bash
   source .env
   uv run python awslabs/aws_healthomics_mcp_server/server.py --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
   ```

   SSE:
   ```bash
   source .env
   uv run python awslabs/aws_healthomics_mcp_server/server.py --transport sse --host 127.0.0.1 --port 8000 --path /mcp
   ```

   Equivalent using environment variables:
   ```bash
   export MCP_TRANSPORT=streamable-http
   export MCP_HOST=127.0.0.1
   export MCP_PORT=8000
   export MCP_PATH=/mcp
   uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

2. **Start the inspector** in another terminal (with no server command, so it acts purely as a client):
   ```bash
   npx @modelcontextprotocol/inspector
   ```

3. **Connect from the inspector UI**:
   - Set **Transport Type** to `Streamable HTTP` or `SSE` to match the server.
   - Set the **URL** to the server's bind address and path, for example `http://127.0.0.1:8000/mcp`.
   - Click **Connect**.

## Tenancy Modes

The server runs in one of two tenancy modes.

### Single-tenant (default)

The server resolves AWS credentials once from the process environment (the standard boto3 credential chain, `AWS_PROFILE`, `AWS_REGION`, etc.). Every request uses the same identity. This is the default and matches all the stdio examples above. No extra flags are needed.

### Multi-tenant (opt-in)

Multi-tenant mode resolves AWS credentials **per inbound request** from an identity presented on the HTTP request. Enable it with `--multi-tenant` (or `MCP_MULTI_TENANT`).

Requirements and constraints:
- **Network transport only.** Multi-tenant mode is incompatible with `stdio`; the server exits at startup if you combine them. Use `streamable-http` or `sse`.
- **At least one inbound mechanism required.** You must select one or more inbound identity mechanisms with `--inbound-auth` (or `MCP_INBOUND_AUTH`). Without one, every request would be rejected, so the server refuses to start.
- Credential material is never logged.

| Setting | CLI flag | Environment variable | Notes |
|---------|----------|----------------------|-------|
| Enable multi-tenant | `--multi-tenant` | `MCP_MULTI_TENANT` | Accepts `true/1/yes/on/enabled` or `false/0/no/off/disabled` (case-insensitive) |
| Inbound mechanisms | `--inbound-auth` | `MCP_INBOUND_AUTH` | Comma-separated subset of `sigv4,jwt,explicit`, e.g. `sigv4,jwt` |
| JWT role ARN | (none) | `MCP_JWT_ROLE_ARN` | Required only when `jwt` is enabled |

#### Inbound Identity Mechanisms

When more than one mechanism is enabled, exactly one is selected per request using the fixed precedence `sigv4 > jwt > explicit` (the order you list them in does not matter).

**`sigv4`** — The request carries an AWS SigV4 `Authorization` header (`AWS4-HMAC-SHA256 ...`). SigV4 proves possession of the secret without transmitting it, so a trusted fronting layer must forward the caller's short-lived credentials on these headers:
- `X-Aho-Forwarded-Secret-Access-Key` (required)
- `X-Aho-Forwarded-Session-Token` (optional; `X-Amz-Security-Token` is accepted as a fallback)

The access key id is parsed from the `Authorization` header's `Credential` scope and used as the per-caller cache key.

**`jwt`** — The request carries an `Authorization: Bearer <token>` header. The server decodes the token claims (it does **not** verify the signature — a fronting layer is expected to have done that), extracts the caller identifier (`sub` claim by default), and calls STS `AssumeRole` on the role named in `MCP_JWT_ROLE_ARN` with an ABAC session tag (`caller=<sub>`) identifying the caller. The server's own credentials must be permitted to `sts:AssumeRole` and `sts:TagSession` on that role.

**`explicit`** — The request carries short-lived AWS credentials directly in headers (matched case-insensitively):
- `X-Aws-Access-Key-Id` (required)
- `X-Aws-Secret-Access-Key` (required)
- `X-Aws-Session-Token` (optional, but expected for short-lived credentials)

This mechanism carries live credential material and must only be used over a trusted transport (operator-controlled TLS / fronting layer) with short-lived credentials.

#### Starting the Server in Multi-tenant Mode

Example: streamable HTTP with the `explicit` mechanism (simplest to test directly from the inspector, since you can set the headers yourself):

```bash
uv run python awslabs/aws_healthomics_mcp_server/server.py \
  --transport streamable-http \
  --host 127.0.0.1 --port 8000 --path /mcp \
  --multi-tenant true\
  --inbound-auth explicit
```

Example: enable multiple mechanisms and configure the JWT role:

```bash
export MCP_JWT_ROLE_ARN=arn:aws:iam::123456789012:role/HealthOmicsMcpCaller
uv run python awslabs/aws_healthomics_mcp_server/server.py \
  --transport streamable-http \
  --host 127.0.0.1 --port 8000 --path /mcp \
  --multi-tenant true\
  --inbound-auth sigv4,jwt,explicit
```

Equivalent using environment variables:

```bash
export MCP_TRANSPORT=streamable-http
export MCP_HOST=127.0.0.1
export MCP_PORT=8000
export MCP_PATH=/mcp
export MCP_MULTI_TENANT=true
export MCP_INBOUND_AUTH=explicit
uv run python awslabs/aws_healthomics_mcp_server/server.py
```

#### Testing Multi-tenant Mode from the Inspector

The inspector lets you attach custom headers to network connections, which is how you present a per-request identity:

1. Start the server in multi-tenant mode with a network transport (see above).
2. Start the inspector as a client: `npx @modelcontextprotocol/inspector`.
3. In the inspector UI, set **Transport Type** and **URL** to match the server (e.g. `http://127.0.0.1:8000/mcp`).
4. Open the connection's **Authentication / Header** settings and add the headers for your chosen mechanism. For `explicit`:
   - `X-Aws-Access-Key-Id: <your access key id>`
   - `X-Aws-Secret-Access-Key: <your secret access key>`
   - `X-Aws-Session-Token: <your session token>` (for STS session credentials)
5. Click **Connect**. Requests without a valid identity for an enabled mechanism are rejected with HTTP 401, no tool runs, and no AWS call is made.

> Tip: `explicit` is the most convenient mechanism for hands-on inspector testing because you can supply the credentials directly as headers. `sigv4` and `jwt` are designed for a trusted fronting layer and are harder to exercise from the inspector alone.

#### Obtaining and Using JWT Tokens

> ⚠️ **Security: the `jwt` mechanism performs NO signature verification.** It decodes the token payload without checking the signature, so any syntactically valid token with a `sub` claim succeeds — including a forged one. Because the `sub` value becomes the `caller` ABAC session tag, a forged token can both obtain credentials for the assumed role and impersonate any other caller. This mechanism must **only** be deployed behind a trusted fronting layer (API gateway, ALB OIDC, AgentCore, or reverse proxy) that cryptographically verifies the token signature before forwarding the request, and the server must never be directly reachable by clients. Local inspector testing over loopback is fine because only you can reach the socket; do not replicate a direct-exposure setup in production.

The `jwt` mechanism expects an `Authorization: Bearer <token>` header. The server **does not verify the token signature** — it decodes the payload, reads the caller claim (`sub` by default), and calls STS `AssumeRole` on `MCP_JWT_ROLE_ARN` with a `caller=<sub>` session tag. The real authorization boundary is the assumed role's trust policy, not the token itself.

**Prerequisites (one-time IAM setup):**
- Create the role named in `MCP_JWT_ROLE_ARN` with a trust policy that allows the server's own identity (the credentials the server process runs with) to call `sts:AssumeRole` and `sts:TagSession`.
- Grant the server's own identity permission to `sts:AssumeRole` and `sts:TagSession` on that role.
- Give the role whatever HealthOmics/S3/CloudWatch permissions the tools need.

Example trust policy on the assumed role (replace the principal with your server's identity):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/HealthOmicsMcpServer" },
      "Action": ["sts:AssumeRole", "sts:TagSession"]
    }
  ]
}
```

**Option A — Amazon Cognito user pool:**
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <app-client-id> \
  --auth-parameters USERNAME=<user>,PASSWORD=<password> \
  --query 'AuthenticationResult.IdToken' \
  --output text
```
Use the returned `IdToken` (its `sub` claim identifies the caller). For an app client with a secret, add the computed `SECRET_HASH` to `--auth-parameters`.

**Option B — Generic OIDC / OAuth2 provider (Okta, Auth0, Azure AD, Keycloak, etc.):**
```bash
curl -s -X POST https://<issuer>/oauth2/token \
  -d grant_type=client_credentials \
  -d client_id=<client-id> \
  -d client_secret=<client-secret> \
  -d scope=<scope> | jq -r '.access_token'
```
Confirm the token carries a `sub` claim (or set the mechanism's caller claim to match your provider's identity claim).

**Option C — Local development token (no IdP):**

Because the server does not verify the signature, you can hand-craft a token whose payload contains a `sub` claim for local testing. This only works when the STS `AssumeRole` call succeeds, so the role and trust policy above must still exist.
```bash
# Header and payload are base64url-encoded; the signature can be any placeholder.
HEADER=$(printf '{"alg":"none","typ":"JWT"}' | basenc --base64url | tr -d '=')
PAYLOAD=$(printf '{"sub":"test-caller@example.com"}' | basenc --base64url | tr -d '=')
echo "${HEADER}.${PAYLOAD}.signature"
```
Do not use hand-crafted tokens outside local testing — deploy behind a fronting layer that authenticates and cryptographically verifies real tokens.

**Inspect a token's claims** to confirm the `sub` value before using it:
```bash
echo "<token>" | cut -d. -f2 | basenc --base64url --decode 2>/dev/null | jq .
```

**Use the token in the inspector:**
1. Start the server with `--inbound-auth jwt` (or include `jwt` in the list) and `MCP_JWT_ROLE_ARN` set:
   ```bash
   export MCP_JWT_ROLE_ARN=arn:aws:iam::123456789012:role/HealthOmicsMcpCaller
   uv run python awslabs/aws_healthomics_mcp_server/server.py \
     --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp \
     --multi-tenant --inbound-auth jwt
   ```
2. Start the inspector as a client: `npx @modelcontextprotocol/inspector`.
3. Set **Transport Type** and **URL** to match the server (e.g. `http://127.0.0.1:8000/mcp`).
4. In the connection's **Authentication** settings, enter the token in the **Bearer Token** field (the inspector sends it as `Authorization: Bearer <token>`). If your inspector version has no dedicated field, add a custom header instead: `Authorization: Bearer <token>`.
5. Click **Connect**. A malformed token, a token missing the `sub` claim, or a failed STS exchange is rejected with HTTP 401; no tool runs and no further AWS call is made.

> Security: bearer tokens are live credentials. Only send them over loopback or an operator-controlled TLS/fronting layer, and prefer short-lived tokens.

## Environment Variables Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `AWS_REGION` | AWS region for HealthOmics operations | `us-east-1` | `us-west-2` |
| `AWS_PROFILE` | AWS CLI profile for authentication | (default profile) | `genomics-dev` |
| `FASTMCP_LOG_LEVEL` | Server logging level | `WARNING` | `DEBUG`, `INFO`, `ERROR` |
| `HEALTHOMICS_DEFAULT_MAX_RESULTS` | Default pagination limit | `10` | `50` |
| `GENOMICS_SEARCH_S3_BUCKETS` | S3 buckets for genomics file search | (none) | `s3://bucket1/,s3://bucket2/path/` |

### Transport & Tenancy Variables

These variables control transport selection, network binding, and multi-tenant credential resolution. Each has an equivalent CLI flag that takes precedence when supplied.

| Variable | CLI flag | Description | Default | Example |
|----------|----------|-------------|---------|---------|
| `MCP_TRANSPORT` | `--transport` | Transport mode: `stdio`, `streamable-http`, or `sse` | `stdio` | `streamable-http` |
| `MCP_HOST` | `--host` | Bind host for network transports | `127.0.0.1` | `0.0.0.0` |
| `MCP_PORT` | `--port` | Bind port for network transports (`1-65535`) | `8000` | `9000` |
| `MCP_PATH` | `--path` | Request path for network transports | `/mcp` | `/healthomics` |
| `MCP_MULTI_TENANT` | `--multi-tenant` | Enable per-request credential resolution (network transport only) | `false` | `true` |
| `MCP_INBOUND_AUTH` | `--inbound-auth` | Comma-separated inbound mechanisms: subset of `sigv4,jwt,explicit` | (none) | `sigv4,jwt` |
| `MCP_JWT_ROLE_ARN` | (none) | Role ARN assumed by the `jwt` mechanism (required when `jwt` is enabled) | (none) | `arn:aws:iam::123456789012:role/HealthOmicsMcpCaller` |

### Testing-Specific Variables

These variables are primarily for testing against mock services:

| Variable | Description | Example |
|----------|-------------|---------|
| `HEALTHOMICS_SERVICE_NAME` | Override service name for testing | `omics-mock` |
| `HEALTHOMICS_ENDPOINT_URL` | Override endpoint URL for testing | `http://localhost:8080` |

## Using the MCP Inspector

Once started, the MCP Inspector will be available at `http://localhost:5173`.

### Initial Testing Steps

1. **Verify Connection**: The inspector should show "Connected" status
2. **List Tools**: You should see all available HealthOmics MCP tools
3. **Test Basic Functionality**:
   - Try `GetAHOSupportedRegions` (requires no parameters)
   - Test `ListAHOWorkflows` to verify AWS connectivity

### Available Tools Categories

The HealthOmics MCP server provides tools in several categories:

- **Workflow Management**: Create, list, and manage workflows
- **Workflow Execution**: Start runs, monitor progress, manage tasks
- **Analysis & Troubleshooting**: Performance analysis, failure diagnosis, log access
- **File Discovery**: Search for genomics files across storage systems
- **Workflow Validation**: Lint WDL and CWL workflow definitions
- **Utility Tools**: Region information, workflow packaging

### Example Test Scenarios

1. **List Available Regions**:
   - Tool: `GetAHOSupportedRegions`
   - Parameters: None
   - Expected: List of AWS regions where HealthOmics is available

2. **List Workflows**:
   - Tool: `ListAHOWorkflows`
   - Parameters: `max_results: 5`
   - Expected: List of workflows in your account

3. **Search for Files**:
   - Tool: `SearchGenomicsFiles`
   - Parameters: `search_terms: ["fastq"]`, `file_type: "fastq"`
   - Expected: FASTQ files from configured S3 buckets

## Troubleshooting

### Common Issues and Solutions

#### 1. Connection Failed
**Symptoms**: Inspector shows "Disconnected" or connection errors

**Solutions**:
- Check that the server process is running
- Verify no other process is using the same port
- Check server logs for error messages

#### 2. AWS Authentication Errors
**Symptoms**: Tools return authentication or permission errors

**Solutions**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Test HealthOmics access
aws omics list-workflows --region us-east-1

# Check AWS profile
echo $AWS_PROFILE
```

#### 3. No Tools Visible
**Symptoms**: Inspector connects but shows no available tools

**Solutions**:
- Check server startup logs for import errors
- Verify all dependencies are installed: `uv sync`
- Ensure you're using the correct server command

#### 4. Region Not Supported
**Symptoms**: HealthOmics API calls fail with region errors

**Solutions**:
- Use `GetAHOSupportedRegions` to see available regions
- Update `AWS_REGION` to a supported region
- Common supported regions: `us-east-1`, `us-west-2`, `eu-west-1`

#### 5. S3 Access Issues for File Search
**Symptoms**: `SearchGenomicsFiles` returns empty results or errors

**Solutions**:
- Verify S3 bucket permissions
- Check `GENOMICS_SEARCH_S3_BUCKETS` configuration
- Ensure buckets exist and contain genomics files

#### 6. HTTP 405 (Method Not Allowed) on Connect
**Symptoms**: The inspector fails to connect to a network transport and the server logs show `POST /mcp ... 405 Method Not Allowed` (often alongside `OPTIONS ... 405` and a `307 Temporary Redirect` on the trailing-slash path). The inspector reports `Error POSTing to endpoint (HTTP 405): Method Not Allowed`.

**Cause**: The inspector's **Transport Type** does not match the server's `--transport`. Streamable HTTP and SSE are different protocols and are not interchangeable. A streamable-http client `POST`s to the path, but under SSE that same path is the event-stream endpoint and only accepts a `GET`, so the server returns `405`.

**Solutions**:
- Make the inspector's Transport Type match the server's transport:
  - Server started with `--transport streamable-http` → set inspector Transport Type to **Streamable HTTP**.
  - Server started with `--transport sse` → set inspector Transport Type to **SSE**.
- Use the same URL and path on both sides, for example `http://127.0.0.1:8000/mcp`.
- When unsure, prefer `streamable-http` on both sides — it is the newer single-endpoint transport and connects most smoothly with the current inspector.
- The `307` redirect on the trailing-slash path (`/mcp/`) is normal path normalization and is not the cause of the failure.

### Debug Mode

For detailed debugging, start with maximum logging:

```bash
export FASTMCP_LOG_LEVEL=DEBUG
cd src/aws-healthomics-mcp-server
npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
```

### Log Analysis

Server logs will show:
- Tool registration and initialization
- AWS API calls and responses
- Error details and stack traces
- Performance metrics

## Security Considerations

### Local Development

The MCP Inspector runs locally and connects directly to your MCP server:
- ✅ No external network exposure by default
- ✅ Runs on localhost for development and testing
- ✅ Direct connection to your local server process
- ⚠️ Ensure your AWS credentials are properly secured
- ⚠️ Be cautious when testing with production AWS accounts

### AWS Credentials

Ensure your AWS credentials have appropriate permissions:
- HealthOmics read/write access
- S3 read access for configured buckets
- CloudWatch Logs read access for log retrieval
- IAM PassRole permissions for workflow execution

## Advanced Configuration

### Custom Port

To run the inspector on a different port:

```bash
mcp-inspector --insecure --port 8080 uv run -m awslabs.aws_healthomics_mcp_server.server
```

### Multiple Server Testing

You can run multiple MCP servers simultaneously by using different ports and configuration files.

### Integration with Development Workflow

For active development:

1. Use Method 1 (source code) for immediate testing of changes
2. Set up file watching to restart the server on code changes
3. Use DEBUG logging to trace execution
4. Keep the inspector open in a browser tab for quick testing

## Using Environment Variables

### Working with .env Files

If you have a `.env` file in your `src/aws-healthomics-mcp-server` directory, you can use it in several ways:

1. **Source the .env file before running** (recommended):
   ```bash
   cd src/aws-healthomics-mcp-server
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

2. **Load and run in one command**:
   ```bash
   cd src/aws-healthomics-mcp-server
   source .env && npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

3. **Use a shell script** (create `run-inspector.sh`):
   ```bash
   #!/bin/bash
   cd src/aws-healthomics-mcp-server
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   Then run:
   ```bash
   chmod +x run-inspector.sh
   ./run-inspector.sh
   ```

### Environment Variable Format

Your `.env` file should contain export statements:
```bash
export AWS_REGION=us-east-1
export AWS_PROFILE=default
export FASTMCP_LOG_LEVEL=DEBUG
export HEALTHOMICS_DEFAULT_MAX_RESULTS=100
export GENOMICS_SEARCH_S3_BUCKETS=s3://omics-data/,s3://broad-references/
```

### Verifying Environment Variables

To check if your environment variables are loaded correctly:
```bash
source .env
echo "AWS_REGION: $AWS_REGION"
echo "AWS_PROFILE: $AWS_PROFILE"
echo "FASTMCP_LOG_LEVEL: $FASTMCP_LOG_LEVEL"
echo "GENOMICS_SEARCH_S3_BUCKETS: $GENOMICS_SEARCH_S3_BUCKETS"
```

## Development and Testing from Source Code

### Quick Start for Developers

If you're working on the HealthOmics MCP server source code:

1. **One-time setup**:
   ```bash
   cd src/aws-healthomics-mcp-server
   uv sync
   # Create or edit your .env file with your settings
   ```

2. **Start testing** (from the `src/aws-healthomics-mcp-server` directory):
   ```bash
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

3. **Make changes to the code** and restart the inspector to test them immediately.

### Testing Individual Components

You can also test the server components independently:

1. **Test server startup** (from `src/aws-healthomics-mcp-server` directory):
   ```bash
   uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

2. **Run with Python module syntax**:
   ```bash
   uv run python -m awslabs.aws_healthomics_mcp_server.server
   ```

3. **Test with different log levels**:
   ```bash
   FASTMCP_LOG_LEVEL=DEBUG uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

### Development Tips

- **Code changes**: The server needs to be restarted after code changes
- **Environment variables**: Set them once in your shell session or use a `.env` file
- **Debugging**: Use `FASTMCP_LOG_LEVEL=DEBUG` to see detailed execution logs
- **Testing tools**: Use the inspector's tool testing interface to verify individual functions

## Additional Resources

- [MCP Inspector Documentation](https://modelcontextprotocol.io/docs/tools/inspector)
- [AWS HealthOmics Documentation](https://docs.aws.amazon.com/omics/)
- [HealthOmics MCP Server README](./README.md)
- [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

## Support

For issues specific to the HealthOmics MCP server:
1. Check the server logs for detailed error messages
2. Verify AWS permissions and region availability
3. Test AWS connectivity independently of the MCP server
4. Review the main README.md for configuration requirements

For MCP Inspector issues:
- Refer to the [official MCP documentation](https://modelcontextprotocol.io/)
- Check the inspector's GitHub repository for known issues
