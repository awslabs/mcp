# Security Policy

The AWS API MCP Server exposes 55 tools to AI agents — tools that can read, write, and
irreversibly destroy AWS infrastructure. Without guardrails, a single hallucination or
prompt injection can trigger real-world side effects: unexpected charges, modified
resources, or deleted infrastructure.

This document covers:

1. [Tool Risk Categories](#tool-risk-categories) — how every tool is classified by impact
2. [Enforcing Guardrails with Intercept](#enforcing-guardrails-with-intercept) — YAML
   policy enforcement via an external proxy
3. [Built-in JSON Policy](#built-in-json-policy) — native per-command blocking without a proxy
4. [Reporting Security Vulnerabilities](#reporting-security-vulnerabilities)

---

## Tool Risk Categories

Every tool exposed by this server falls into one of five risk categories. Use these
classifications to decide which tools to restrict, rate-limit, or require confirmation for.

| Category | Count | Risk | Description |
|---|---|---|---|
| **Read** | 25 | Safe | Informational only — no AWS state is changed |
| **Write** | 3 | Medium | Creates or modifies AWS resources |
| **Execute** | 3 | High | Runs arbitrary code or authenticated AWS API calls |
| **Destructive** | 2 | Critical | Irreversible — permanently deletes resources or infrastructure |
| **Analyze** | 22 | Varies | Advisory, diagnostic, or multi-step tools — review individually |

### Read (25 tools)

These tools retrieve information only. Safe to allow unrestricted.

| Tool | Description |
|---|---|
| `describe_log_groups` | List metadata about CloudWatch log groups |
| `get_active_alarms` | Identify currently active CloudWatch alarms |
| `get_alarm_history` | Retrieve alarm state change history |
| `get_bestpractices` | Get AWS development and deployment guidance |
| `get_cdk_best_practices` | Retrieve AWS CDK best practices |
| `get_cloudwatch_logs` | Access CloudWatch logs for EKS |
| `get_cloudwatch_metrics` | Retrieve CloudWatch metrics for EKS |
| `get_eks_vpc_config` | Retrieve VPC configuration for EKS |
| `get_k8s_events` | List Kubernetes events |
| `get_logs_insight_query_results` | Retrieve CloudWatch Insights query results |
| `get_pod_logs` | Retrieve Kubernetes pod logs |
| `get_regional_availability` | Check regional availability for AWS services |
| `get_resource` | Retrieve specific AWS resource details |
| `get_schema` | Get CloudFormation schema for resources |
| `list_api_versions` | List available Kubernetes API versions |
| `list_k8s_resources` | List Kubernetes resources by kind |
| `list_knowledge_bases` | List available Bedrock knowledge bases |
| `list_regions` | List all AWS regions |
| `list_resources` | Enumerate resources of specified types |
| `query_sql` | Execute read-only SQL queries against S3 Tables |
| `read_documentation` | Retrieve AWS docs as markdown |
| `retrieve_agent_sop` | Search AWS operational procedures |
| `search_cdk_documentation` | Search CDK docs and constructs |
| `search_cfn_documentation` | Query CloudFormation docs and patterns |
| `search_documentation` | Search across AWS documentation |

### Write (3 tools)

These tools create or modify AWS resources. Consider requiring confirmation or rate-limiting.

| Tool | Description |
|---|---|
| `create_resource` | Create AWS resources declaratively |
| `create_table_from_csv` | Convert CSV files to S3 Tables |
| `update_resource` | Update existing AWS resources |

### Execute (3 tools)

These tools run arbitrary code or make authenticated AWS API calls. Restrict carefully —
especially `call_aws`, which can invoke any AWS CLI command.

| Tool | Description |
|---|---|
| `call_aws` | Execute authenticated AWS API calls (any service, any operation) |
| `execute_log_insights_query` | Run CloudWatch Logs Insights queries |
| `invoke_lambda` | Execute Lambda functions |

### Destructive (2 tools)

These tools permanently delete AWS resources or infrastructure. **Deny by default** in
production agent deployments.

| Tool | Description |
|---|---|
| `delete_resource` | Delete AWS resources |
| `tf_destroy` | Destroy Terraform-managed infrastructure |

### Analyze (22 tools)

These tools perform analysis, validation, or multi-step operations. Risk varies — some
can make real changes to AWS infrastructure or Kubernetes resources. Review each tool
individually before allowing unrestricted agent access.

| Tool | Can mutate state? |
|---|---|
| `tf_apply` | Yes — applies Terraform changes |
| `manage_k8s_resource` | Yes — can create, update, or delete Kubernetes resources |
| `manage_eks_stacks` | Yes — manages CloudFormation stacks |
| All others in this category | No — read-only or advisory |

| Tool | Description |
|---|---|
| `analyze_log_group` | Detect anomalies and errors in CloudWatch logs |
| `analyze_metric` | Analyze CloudWatch metric trends |
| `analyze_stack_failures` | Diagnose failed CloudFormation stacks |
| `azureterraformbestpractices` | Get Terraform best practices for Azure |
| `bedrock_kb_retrieve` | Query Bedrock knowledge bases |
| `cancel_logs_insight_query` | Cancel in-progress CloudWatch queries |
| `check_cdk_nag_suppressions` | Validate CDK Nag suppressions |
| `dynamodb_data_model_validation` | Validate DynamoDB data models |
| `dynamodb_data_modeling` | Interactive DynamoDB data modeling |
| `explain_cdk_nag_rule` | Explain specific CDK Nag security rules |
| `manage_eks_stacks` | Manage EKS CloudFormation stacks |
| `manage_k8s_resource` | Create, update, or delete Kubernetes resources |
| `source_db_analyzer` | Extract schema from existing databases |
| `suggest_aws_commands` | Get AWS CLI command syntax help |
| `tf_apply` | Apply Terraform changes to infrastructure |
| `tf_init` | Initialise Terraform working directory |
| `tf_output` | Retrieve Terraform output values |
| `tf_plan` | Generate Terraform execution plan |
| `tf_state_list` | List resources in Terraform state |
| `tf_validate` | Validate Terraform configuration |
| `validate_cfn_security` | Check CloudFormation compliance |
| `validate_cfn_template` | Validate CloudFormation syntax and schema |

---

## Enforcing Guardrails with Intercept

[Intercept](https://github.com/PolicyLayer/Intercept) is an open-source MCP proxy
(Apache 2.0) that sits between AI agents and MCP servers. It evaluates every
`tools/call` request against YAML policies and blocks violations before they reach the
server — no SDK changes or code modifications required.

### Quick Start

**Block `delete_resource` outright:**

```yaml
delete_resource:
  rules:
    - name: "block resource deletion"
      action: "deny"
      on_deny: "Deleting AWS resources via agent is not permitted"
```

**Rate-limit `call_aws` to prevent runaway API usage:**

```yaml
call_aws:
  rules:
    - name: "rate limit aws api calls"
      rate_limit: 10/minute
```

**Deny `tf_destroy` to prevent infrastructure destruction:**

```yaml
tf_destroy:
  rules:
    - name: "require confirmation for terraform destroy"
      action: "deny"
      on_deny: "Infrastructure destruction requires manual approval — run tf destroy manually"
```

### Full Policy Template

A ready-to-use YAML scaffold covering all 55 tools — grouped by category with empty rule
slots — is available at:

**[PolicyLayer/Intercept — policies/aws.yaml](https://github.com/PolicyLayer/Intercept/blob/main/policies/aws.yaml)**

Fill in the `rules:` blocks for the tools you want to restrict. The default policy
(`default: "allow"`) passes through any tool not explicitly listed.

---

## Built-in JSON Policy

For teams that don't want to run a proxy, this server has a native policy mechanism that
blocks or gates specific AWS CLI commands before they execute.

**File location:** `~/.aws/aws-api-mcp/mcp-security-policy.json`

```json
{
  "policy": {
    "denyList": [
      "aws ec2 terminate-instances",
      "aws s3 rb",
      "aws cloudformation delete-stack"
    ],
    "elicitList": [
      "aws rds delete-db-instance",
      "aws lambda delete-function"
    ]
  }
}
```

> **Note:** `denyList` entries must exactly match the CLI command string that `call_aws`
> passes to the AWS CLI. Partial matches and wildcards are not supported. To block
> `call_aws` at the MCP tool level regardless of arguments, use Intercept instead.

- **`denyList`** — blocks listed AWS CLI commands outright. The agent receives an error
  and cannot proceed.
- **`elicitList`** — requires explicit user confirmation before the command executes.
  Falls back to deny if the MCP client does not support elicitation.

### Comparison: Two Enforcement Options

| | Intercept (YAML proxy) | Built-in JSON policy |
|---|---|---|
| **Mechanism** | External proxy layer | Native server config file |
| **Format** | YAML | JSON |
| **Granularity** | Per MCP tool name | Per AWS CLI command |
| **Rate limiting** | Yes | No |
| **Setup** | Separate process | JSON file in `~/.aws/` |
| **Best for** | Full MCP-layer guardrails | Quick per-command blocking |

---

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please **do not** open a
public GitHub issue.

Report it via the [AWS Vulnerability Reporting Page](http://aws.amazon.com/security/vulnerability-reporting/)
or by email to [aws-security@amazon.com](mailto:aws-security@amazon.com).

For more details, see [.github/SECURITY](../../.github/SECURITY).
