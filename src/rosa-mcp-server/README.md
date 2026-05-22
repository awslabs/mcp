# ROSA MCP Server

The ROSA MCP server provides AI code assistants with tools for managing Red Hat OpenShift Service on AWS (ROSA) clusters through the Model Context Protocol (MCP). It communicates directly with the OCM (OpenShift Cluster Manager) REST API and AWS APIs — no CLI tools (rosa, oc) are required on the host.

## Key features

* Manage ROSA clusters (list, describe, create, delete, upgrade) via the OCM REST API
* Manage machine pools and node pools with auto-detection of HCP vs Classic topology
* Configure identity providers (HTPasswd, GitHub, OpenID Connect, LDAP)
* Manage networking (ingresses, load balancers, route selectors)
* Kubernetes/OpenShift operations (list resources, pod logs, events, apply YAML, manage resources)
* IRSA (IAM Roles for Service Accounts) setup for fine-grained pod-level AWS access
* CloudWatch logs and metrics retrieval for ROSA clusters
* IAM role management, OIDC provider listing, and service quota verification
* Cluster autoscaler configuration, add-on management, and hibernation control
* Built-in troubleshooting guide with common ROSA issues and resolutions
* Advisor tools for instance type recommendations, config validation, and cost estimation

## Prerequisites

* [Install Python 3.10+](https://www.python.org/downloads/)
* [Install the `uv` package manager](https://docs.astral.sh/uv/getting-started/installation/)
* A Red Hat account with access to [OpenShift Cluster Manager](https://console.redhat.com/openshift)
* [Install and configure the AWS CLI with credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) (for IAM, CloudWatch, and IRSA operations)

## Authentication

### OCM API (Red Hat)

The server authenticates to the OCM API using an offline token. Configure it in one of these ways (in priority order):

1. **Environment variable**: Set `OCM_TOKEN` to your offline token from https://console.redhat.com/openshift/token
2. **OCM CLI config**: Run `ocm login --use-auth-code` or `ocm login --use-device-code` — the server reads the saved token from `~/.config/ocm/ocm.json` (Linux) or `~/Library/Application Support/ocm/ocm.json` (macOS)

If no OCM token is available, OCM-based tools are disabled but AWS-only tools (IAM, CloudWatch, Advisor) still function.

### AWS APIs

Standard AWS credential resolution: environment variables, `~/.aws/credentials`, profiles (`AWS_PROFILE`), or instance roles.

Required IAM permissions depend on which tools you use:

| Tool category | Required permissions |
|---------------|---------------------|
| CloudWatch | `logs:FilterLogEvents`, `cloudwatch:GetMetricData` |
| IAM (read) | `iam:ListRoles`, `iam:ListAttachedRolePolicies`, `iam:GetOpenIDConnectProvider` |
| IAM (write) | `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:DeleteRole`, `iam:PutRolePolicy` |
| IRSA | All IAM permissions above + `sts:GetCallerIdentity` |
| Service Quotas | `servicequotas:GetServiceQuota` |

## Installation

Configure the MCP server in your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.rosa-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.rosa-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "OCM_TOKEN": "your-offline-token-here"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

For Kiro MCP configuration, see the [Kiro IDE documentation](https://kiro.dev/docs/mcp/configuration/) or the [Kiro CLI documentation](https://kiro.dev/docs/cli/mcp/configuration/) for details.

For global configuration, edit `~/.kiro/settings/mcp.json`. For project-specific configuration, edit `.kiro/settings/mcp.json` in your project directory.

### Using OCM CLI login (no OCM_TOKEN needed)

If you prefer not to set `OCM_TOKEN`, login with the OCM CLI first:

```bash
ocm login --use-auth-code
```

The server will automatically read the saved credentials.

## Arguments

| Argument | Description |
|----------|-------------|
| `--allow-write` | Enable mutating operations (cluster create/delete, machine pool changes, IDP management, IRSA setup) |
| `--allow-sensitive-data-access` | Enable access to pod logs, events, and cluster credentials |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OCM_TOKEN` | Red Hat offline token | Read from OCM config file |
| `OCM_API_URL` | OCM API base URL | `https://api.openshift.com` |
| `AWS_REGION` | AWS region for boto3 calls | From AWS config |
| `AWS_PROFILE` | AWS profile for credentials | `default` |
| `FASTMCP_LOG_LEVEL` | Log level | `WARNING` |

## Available Tools

### Cluster Management (9 tools)
- `rosa_list_clusters` — List all ROSA clusters
- `rosa_describe_cluster` — Get detailed cluster information
- `rosa_create_cluster` — Create a new ROSA cluster (requires `--allow-write`)
- `rosa_delete_cluster` — Delete a cluster (requires `--allow-write`)
- `rosa_list_versions` — List available ROSA versions
- `rosa_list_upgrades` — List available upgrades
- `rosa_upgrade_cluster` — Schedule a cluster upgrade (requires `--allow-write`)
- `rosa_get_cluster_credentials` — Get cluster credentials
- `rosa_get_install_logs` — Get cluster install logs

### Machine Pools / Node Pools (4 tools)
- `rosa_list_machinepools` — List pools (auto-detects HCP vs Classic)
- `rosa_create_machinepool` — Create a pool with autoscaling, spot, taints/labels
- `rosa_update_machinepool` — Update pool configuration
- `rosa_delete_machinepool` — Delete a pool

### Authentication & Identity (5 tools)
- `rosa_whoami` — Show current OCM identity
- `rosa_list_idps` — List identity providers
- `rosa_create_idp` — Create IDP (HTPasswd, GitHub, OpenID, LDAP)
- `rosa_delete_idp` — Delete an IDP
- `rosa_create_admin` — Create cluster admin user

### Networking (4 tools)
- `rosa_list_ingresses` — List ingress controllers
- `rosa_create_ingress` — Create ingress (NLB/CLB, public/private)
- `rosa_update_ingress` — Update ingress configuration
- `rosa_delete_ingress` — Delete an ingress

### Kubernetes/OpenShift Operations (8 tools)
- `rosa_list_resources` — List K8s resources by kind
- `rosa_get_pod_logs` — Get pod logs
- `rosa_get_events` — Get resource events
- `rosa_apply_yaml` — Apply YAML manifests
- `rosa_get_nodes` — Get node status
- `rosa_manage_resource` — Generic CRUD for any K8s/OpenShift resource
- `rosa_list_api_versions` — List available API groups
- `rosa_generate_app_manifest` — Generate Deployment+Service+Route YAML

### IRSA — IAM Roles for Service Accounts (3 tools)
- `rosa_configure_irsa` — Create IAM role with OIDC trust policy, attach policy, annotate K8s SA
- `rosa_describe_irsa` — Find IAM roles associated with a service account
- `rosa_delete_irsa` — Delete IRSA role and remove SA annotation

### Cluster Autoscaler (4 tools)
- `rosa_get_autoscaler` — Get autoscaler configuration
- `rosa_create_autoscaler` — Create cluster autoscaler
- `rosa_update_autoscaler` — Update autoscaler settings
- `rosa_delete_autoscaler` — Delete cluster autoscaler

### Add-ons (4 tools)
- `rosa_list_available_addons` — List add-on catalog
- `rosa_list_cluster_addons` — List installed add-ons
- `rosa_install_addon` — Install an add-on
- `rosa_uninstall_addon` — Uninstall an add-on

### User Management (3 tools)
- `rosa_list_users` — List users in cluster groups
- `rosa_grant_user` — Grant dedicated-admin or cluster-admin
- `rosa_revoke_user` — Revoke admin access

### Advanced Operations (9 tools)
- `rosa_hibernate_cluster` — Hibernate a Classic cluster
- `rosa_resume_cluster` — Resume a hibernated cluster
- `rosa_get_cluster_status` — Get cluster health status
- `rosa_get_cluster_metrics` — Query cluster metrics/alerts
- `rosa_create_break_glass_credential` — Create break-glass credential (HCP)
- `rosa_get_delete_protection` — Check delete protection status
- `rosa_set_delete_protection` — Enable/disable delete protection
- `rosa_list_machine_types` — List available instance types
- `rosa_list_break_glass_credentials` — List break-glass credentials

### Operator Management (7 tools)
- `rosa_list_sts_operator_roles` — List STS operator IAM roles
- `rosa_get_cluster_operators` — Get operator health status
- `rosa_list_sts_credential_requests` — List required role templates
- `rosa_list_sts_policies` — List available STS IAM policies
- `rosa_install_operator` — Install an operator/add-on
- `rosa_uninstall_operator` — Remove an operator/add-on
- `rosa_get_operator_status` — Check installation status

### Configuration (5 tools)
- `rosa_list_tuning_configs` — List tuning configurations
- `rosa_create_tuning_config` — Create a tuning config
- `rosa_delete_tuning_config` — Delete a tuning config
- `rosa_get_kubelet_config` — Get kubelet configuration
- `rosa_update_kubelet_config` — Update kubelet config

### Monitoring — CloudWatch (2 tools)
- `rosa_get_cloudwatch_logs` — Get CloudWatch logs
- `rosa_get_cloudwatch_metrics` — Get CloudWatch metrics

### IAM & Quotas (6 tools)
- `rosa_get_account_roles` — List ROSA account IAM roles
- `rosa_get_operator_roles` — List operator roles
- `rosa_list_oidc_providers` — List OIDC providers
- `rosa_verify_quota` — Verify service quotas
- `rosa_get_policies_for_role` — List policies on a role
- `rosa_add_inline_policy` — Add inline policy to a role

### Troubleshooting (3 tools)
- `rosa_search_troubleshoot_guide` — Search KB of common ROSA issues
- `rosa_get_vpc_config` — Get VPC/subnet/SG details
- `rosa_get_metrics_guidance` — CloudWatch + Prometheus metrics reference

### Advisor (4 tools, no OCM required)
- `rosa_recommend_instance_type` — Instance type recommendations
- `rosa_validate_config` — Configuration validation
- `rosa_get_environment_preset` — Environment presets (dev/staging/prod)
- `rosa_estimate_cost` — Cost estimation

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  MCP Client (Kiro, Cursor, Claude Desktop, etc.)    │
└──────────────────────┬──────────────────────────────┘
                       │ MCP Protocol (stdio)
┌──────────────────────▼──────────────────────────────┐
│  ROSA MCP Server                                    │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ OCM Client  │  │ K8s Client   │  │ boto3     │  │
│  │ (httpx)     │  │ (kubernetes) │  │ (AWS SDK) │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘  │
└─────────┼────────────────┼─────────────────┼────────┘
          │                │                 │
          ▼                ▼                 ▼
   OCM REST API     K8s API Server    AWS APIs
   (api.openshift   (via kubeconfig   (IAM, CW,
    .com)            from OCM)         STS, SQ)
```

## Development

```bash
cd src/rosa-mcp-server

# Install dependencies
uv sync --all-groups

# Run unit tests (mocked, fast)
uv run pytest tests/unit/ -v

# Run BDD tests against live cluster
ROSA_TEST_CLUSTER_ID=<cluster-id> uv run pytest tests/step_defs/ -v

# Run only read-only live tests
uv run pytest tests/step_defs/ -m "live and readonly"

# Run advisor tests (no API needed)
uv run pytest tests/step_defs/ -m advisor

# Lint
uv run ruff check .
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.
