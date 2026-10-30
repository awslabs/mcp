# AWS Labs EC2Rescue for Linux MCP Server

An MCP server that enables AI agents to diagnose EC2 instance issues by running [EC2 Rescue Linux](https://github.com/awslabs/aws-ec2rescue-linux) modules through AWS Systems Manager (SSM). Each `ec2rl` diagnostic module is exposed as an individual MCP tool — agents can collect logs and metrics without SSH access, arbitrary shell commands, or manual module knowledge.

```
AI Client (Claude, Kiro, etc.)
    │  MCP (stdio / Streamable HTTP)
    ▼
EC2Rescue for Linux MCP Server
    │  boto3 (SSM SendCommand / EC2 DescribeInstances)
    ▼
AWS Systems Manager ──▶ EC2 instance (SSM Agent + ec2rl)
```

### Why use this server?

- **No arbitrary commands** — Agents can only call registered `ec2rl` modules, not run arbitrary shell commands on the instance.
- **No interactive shell needed** — Diagnostics run through SSM `SendCommand`, eliminating the need to open SSH or Session Manager sessions.
- **Symptom-driven module selection** — The AI sees a structured tool list and can match modules to symptoms like "high CPU" or "kernel panic."
- **Accessible triage** — Less-experienced engineers can ask questions like "Why is `i-0abc123` slow?" and receive AI-gathered diagnostic outputs with explanations.
- **Credentials stay server-side** — AWS keys remain on the MCP server; clients never hold them.

## Security Considerations

Before using this MCP server, you should consider conducting your own
independent assessment to ensure that your use complies with your own security
and quality control practices, as well as the laws, rules, and regulations that
govern you and your content.

The agent can only run registered `ec2rl` modules with character-validated
arguments, not arbitrary shell commands. After a run, the server reads the
files `ec2rl` produced under `/var/tmp/ec2rl/<timestamp>/`. Those paths come
from the instance and are filtered, but that confinement is best-effort, not a
security boundary: a compromised instance keeps some influence over which of
its files reach your AI client. It gains no privilege doing so — these tools
already require root on the instance via SSM.

**Accepted risk.** The *contents* of files under that directory are whatever
the instance wrote, so a compromised instance can return misleading diagnostic
output. The server treats gathered output as untrusted data to surface to the
operator, not as trusted input.

**Diagnostic output left on the instance.** Each run writes a new
timestamped directory under `/var/tmp/ec2rl/` on the target instance. The
server only reads that output back — it never deletes it. The files are
Customer Content on the customer's own instance, so operators should prune
`/var/tmp/ec2rl/` periodically.

**Protecting that output at rest.** That output can contain secrets, tokens, or
PII, and lands unencrypted-by-default on the instance's own volume. Protecting
it at rest is the operator's responsibility: run these instances on encrypted
EBS volumes (an existing unencrypted volume cannot be encrypted in place).

**Module definitions.** The server only loads its bundled `mod.d/` module
definitions, which decide the `ec2rl` commands it will run. They are verified
at load time against a checksum manifest, and the server refuses to start if a
definition has been modified without the manifest being regenerated.

**Credential guidance.** The server uses the standard boto3 credential chain.
Prefer `AWS_PROFILE` with SSO or an assumed role configured in `.aws/config`;
if you set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` directly, you are
responsible for rotating them.

**Data sensitivity.** Diagnostic output is not redacted before it is returned
to the AI client and its (possibly third-party) model provider. Output can
therefore contain secrets, tokens, or PII read from the instance. Some gathered
modules can return files that are especially likely to contain secrets, for
example `environment` (`/etc/environment`), `cron` (job command lines),
`profile` (`/etc/profile`), and `cloudinitlog` (cloud-init may echo user-data).
Review a module's output sensitivity before running it against a model provider
you do not control.

When using the Streamable HTTP transport, see
[HTTP Mode Security Considerations](#-http-mode-security-considerations) under
Authentication.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (package manager)
- AWS credentials configured (via environment variables or AWS profile)
- Target EC2 instances must be [SSM managed nodes](https://docs.aws.amazon.com/systems-manager/latest/userguide/managed_instances.html)
- [EC2 Rescue Linux](https://github.com/awslabs/aws-ec2rescue-linux) installed on target instances (or use the `install_ec2rescue_linux` tool to install it)

## Available Tools

By default, the server registers 32 curated modules plus 2 utility tools. Use `--all` to register all 209+ modules.

### Utility Tools

| Tool | Description |
|------|-------------|
| `list_instances` | List EC2 instances accessible via SSM |
| `install_ec2rescue_linux` | Install EC2 Rescue for Linux via `AWSSupport-InstallEC2Rescue` SSM Automation |

### Default ec2rl Modules (32 tools)

Each module is exposed as `run_ec2rescue_linux_<name>`.

| Category | Modules |
|----------|---------|
| System basics | `cpuinfo`, `meminfo`, `kernelversion`, `osrelease`, `lsblk`, `mounts`, `ps` |
| Network | `ifconfig`, `iproute`, `netstatanp`, `ethtool`, `resolvconf`, `dig` |
| Logs | `journal`, `dmesg`, `messages`, `cloudinitlog` |
| Kernel / boot | `kernelpanic`, `hungtasks`, `oomkiller`, `softlockup`, `fstabfailures`, `kernelcmdline`, `lsmod` |
| Performance | `iostat`, `vmstat`, `top`, `sysctl` |
| Packages / config | `dpkgpackages`, `rpmpackages`, `kernelconfig`, `fstab` |

Use `--modules=tcpdump,strace` to add specific modules beyond the defaults, or `--all` for all 209+.

### Output size controls

Some modules produce large logs. To keep responses within the context window, the server bounds their output by default:

- **Append-only logs** (`messages`, `dmesg`, `yumlog`, `aptlog`, `cloudinitlog`, `httpdlogs`, `nginxlogs`, `mysqldlog`, `systemsmanager`, `workspacelogs`, `zypperlog`) return only the last **100 lines** (most recent entries). Pass `tail_lines=<N>` to change the count, or `tail_lines=0` to fetch the full log. (`journal` is excluded — use its `--since`/`--until` args instead.)
- **Key-filtered modules** (`kernelconfig`, `sysctl`, `dpkgpackages`, `rpmpackages`) accept `grep_keys=[...]` to return only matching lines.

### Not supported

These upstream [EC2 Rescue for Linux](https://github.com/awslabs/aws-ec2rescue-linux) features are intentionally not exposed by this MCP server:

- **Upload** (`ec2rl upload`) — uploading results to S3 or an AWS Support URL.
- **Bug report** (`ec2rl bug-report`) — generating a bug report bundle.
- **Version / config** (`ec2rl version`, `version-check`, `menu-config`, `save-config`) — version checks and interactive/saved configuration.
- **Batch runs** — modules run one at a time (`run_ec2rescue_linux_<module>`); ec2rl's bulk `run` over all modules or by class/domain is not exposed.

## Quickstart


| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.ec2rescue-for-linux-mcp-server&config=%7B%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22awslabs.ec2rescue-for-linux-mcp-server%40latest%22%5D%2C%20%22env%22%3A%20%7B%22FASTMCP_LOG_LEVEL%22%3A%20%22ERROR%22%2C%20%22AWS_PROFILE%22%3A%20%22your-aws-profile%22%2C%20%22AWS_REGION%22%3A%20%22us-east-1%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.ec2rescue-for-linux-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZWMycmVzY3VlLWZvci1saW51eC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0=%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=awslabs.ec2rescue-for-linux-mcp-server&config=%7B%22command%22%3A%22uvx%20awslabs.ec2rescue-for-linux-mcp-server%40latest%22%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

You can modify the settings of your MCP client to run your local server (e.g. for Kiro, ~/.kiro/settings/mcp.json)

### For Mac/Linux:

```json
{
  "mcpServers": {
    "awslabs.ec2rescue-for-linux-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.ec2rescue-for-linux-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

### For Windows:

```json
{
  "mcpServers": {
    "awslabs.ec2rescue-for-linux-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.ec2rescue-for-linux-mcp-server@latest",
        "awslabs.ec2rescue-for-linux-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

To specify a flag (for example, to enable all modules), add it to the `args` array:

```json
{
  "mcpServers": {
    "awslabs.ec2rescue-for-linux-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.ec2rescue-for-linux-mcp-server@latest",
        "-all"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```

> **Note:** Replace `your-profile` with your AWS profile name and `us-east-1` with your target region.

## IAM Policy (MCP Server Side)

The IAM principal running this MCP server needs the following minimum
permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMReadOnly",
      "Effect": "Allow",
      "Action": [
        "ssm:DescribeInstanceInformation",
        "ssm:GetCommandInvocation"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SSMSendCommand",
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ssm:*::document/AWS-RunShellScript",
        "arn:aws:ec2:*:ACCOUNT_ID:instance/*",
        "arn:aws:ssm:*:ACCOUNT_ID:managed-instance/*"
      ]
    },
    {
      "Sid": "EC2DescribeInstances",
      "Effect": "Allow",
      "Action": "ec2:DescribeInstances",
      "Resource": "*"
    }
  ]
}
```

### Additional permissions for `--allow-install`

Only needed if you start the server with `--allow-install`. The
`AWSSupport-InstallEC2Rescue` runbook is started without an
`AutomationAssumeRole`, so it runs with this principal's permissions and needs
its own [documented
permissions](https://docs.aws.amazon.com/systems-manager-automation-runbooks/latest/userguide/automation-awssupport-installec2rescue.html)
— including account-wide `ssm:ListCommandInvocations`. Omit this policy to keep
that grant off the principal.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMAutomationInstall",
      "Effect": "Allow",
      "Action": "ssm:StartAutomationExecution",
      "Resource": [
        "arn:aws:ssm:*::automation-definition/AWSSupport-InstallEC2Rescue:*",
        "arn:aws:ssm:*::document/AWSSupport-InstallEC2Rescue",
        "arn:aws:ssm:*:ACCOUNT_ID:automation-execution/*"
      ]
    },
    {
      "Sid": "SSMAutomationInstallDescribe",
      "Effect": "Allow",
      "Action": "ssm:DescribeAutomationExecutions",
      "Resource": "*"
    },
    {
      "Sid": "InstallRunbookRunCommand",
      "Effect": "Allow",
      "Action": [
        "ssm:ListCommands",
        "ssm:ListCommandInvocations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "InstallRunbookConfigurePackage",
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ssm:*::document/AWS-ConfigureAWSPackage",
        "arn:aws:ec2:*:ACCOUNT_ID:instance/*",
        "arn:aws:ssm:*:ACCOUNT_ID:managed-instance/*"
      ]
    }
  ]
}
```

## Authentication

### AWS Credentials

AWS credentials are passed via environment variables. Prefer `AWS_PROFILE` with
SSO or an assumed role; static keys are the least preferred option and should be
used only where neither is available.

| Variable | Description |
|----------|-------------|
| `AWS_PROFILE` | AWS CLI named profile — preferred; use with SSO or an assumed role |
| `AWS_REGION` | AWS region (required unless your `AWS_PROFILE` sets one) |
| `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | Static long-lived credentials. **Not recommended** — use only where SSO and assumed roles are both unavailable. You are responsible for rotating them. |

### MCP Client Authentication (Streamable HTTP)

When using `--transport=streamable-http`, the server requires the `AUTH_TYPE` environment variable to be explicitly set to prevent unintentional unauthenticated exposure:

| `AUTH_TYPE` | Description |
|-------------|-------------|
| `no-auth` | Explicitly disables authentication. Use only with a loopback bind (`--host 127.0.0.1`, the default); never combine it with a bind on all interfaces. |
| `oauth` | Enables OAuth 2.0 JWT Bearer token verification. Requires `AUTH_ISSUER`, `AUTH_JWKS_URI` and `AUTH_AUDIENCE`. |

Additional environment variables for `AUTH_TYPE=oauth`:

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_ISSUER` | Yes | Expected `iss` claim in the JWT (e.g., `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXX`). Must be an `https` URL. |
| `AUTH_JWKS_URI` | Yes | URL of the JWKS endpoint for verifying token signatures. Must be an `https` URL: this fetch supplies the keys behind every authentication decision, so plaintext is rejected. |
| `AUTH_AUDIENCE` | Yes | Expected `aud` claim. Required — an issuer usually mints tokens for several services, so without it a token issued for any of them would be accepted here. Tokens with a different `aud`, or none, are rejected. |

> **Note:** `AUTH_TYPE` is only required for `--transport=streamable-http`. The stdio transport (default) does not require authentication as it communicates via stdin/stdout with the parent process.

### 🔒 HTTP Mode Security Considerations

**IMPORTANT**: When using HTTP mode (`streamable-http`), please be aware of the following security considerations:

- **Single Customer Server**: This HTTP mode is intended for **single customer use only**. It is **NOT designed for multi-tenant environments** or serving multiple users simultaneously.
- **Authentication**: The server can be started with OAuth authentication, using `AUTH_TYPE=oauth`. Set `AUTH_TYPE=no-auth` to disable authentication if needed.
- **Network Security Controls**: Ensure proper network security controls are in place:
  - Bind to localhost (`127.0.0.1`) when possible
  - Configure firewall rules to restrict access
- **Encryption in Transit**: We **strongly recommend** adding encryption in transit when using HTTP mode:
  - Place a reverse proxy (e.g., nginx, ALB) with TLS in front of the server
  - Avoid transmitting sensitive data over unencrypted HTTP connections

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--all` | off | Register all 209+ ec2rl modules as MCP tools. |
| `--modules NAME,...` | (none) | Additional module names beyond the default 32. |
| `--remediate` | off | Register remediation modules (openssh, rebuildinitrd, etc.). |
| `--allow-install` | off | Allow `install_ec2rescue_linux` without elicitation consent. |
| `--allow-perfimpact` | off | Permit perfimpact modules (tcpdump, perf, strace). Off by default — only a human operator can enable this at server startup; agents cannot turn it on. |
| `--transport {stdio,streamable-http}` | `stdio` | MCP transport. |
| `--host HOST` | `127.0.0.1` | Bind host (streamable-http only). |
| `--port PORT` | `8000` | Bind port (streamable-http only). |

### Streamable HTTP example

Loopback bind, no authentication. `--host 127.0.0.1` is what makes
`AUTH_TYPE=no-auth` acceptable here — the server is reachable only from the
local machine:

```bash
AUTH_TYPE=no-auth AWS_PROFILE=your-profile AWS_REGION=us-east-1 \
  uv run awslabs.ec2rescue-for-linux-mcp-server \
    --transport streamable-http --host 127.0.0.1 --port 8080
```

To accept connections from other hosts, authenticate them. Do not widen the
bind while leaving `AUTH_TYPE=no-auth`: the tools run diagnostics as root on
your instances, so an unauthenticated listener on a routable interface hands
that to anyone who can reach the port.

```bash
AUTH_TYPE=oauth \
AUTH_ISSUER=https://your-issuer.example.com \
AUTH_JWKS_URI=https://your-issuer.example.com/.well-known/jwks.json \
AUTH_AUDIENCE=your-audience \
AWS_PROFILE=your-profile AWS_REGION=us-east-1 \
  uv run awslabs.ec2rescue-for-linux-mcp-server \
    --transport streamable-http --host 0.0.0.0 --port 8080
```

Terminate TLS in front of the server (see HTTP Mode Security Considerations
below); the server itself speaks plaintext HTTP.

Once the server is running, connect to it using the following MCP client configuration (ensure the host and port match your `--host` and `--port` settings):

```json
{
  "mcpServers": {
    "awslabs.ec2rescue-for-linux-mcp-server": {
      "type": "http",
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}
```

> **Note:** Replace `127.0.0.1` with your server's host if you've set `--host` to a different value.

### All modules with installation enabled

```bash
uv run awslabs.ec2rescue-for-linux-mcp-server --all --allow-install --remediate
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest --cov --cov-branch --cov-report=term-missing
```
