# Agent Guardrails for AWS API MCP Server

## Overview

The AWS API MCP Server provides AI agents with direct access to AWS services through the AWS CLI. This document explains the tools available, their risk profiles, and how to configure guardrails to ensure safe agent deployments.

## Tools Provided

The AWS API MCP Server exposes **2-3 tools** to AI agents:

### 1. `call_aws` (High Risk)

**Purpose:** Executes AWS CLI commands directly against your AWS account.

**Risk Level:** HIGH - This tool can perform any AWS CLI operation, including destructive actions like deleting resources, terminating instances, or modifying security configurations.

**Capabilities:**
- Executes single or batch AWS CLI commands (up to 20 commands)
- Supports all AWS services and operations available via AWS CLI
- Handles pagination with `max_results` parameter
- Supports region expansion with `--region *`
- Can access local files if `AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS=true`

**Example Commands:**
```bash
aws s3 ls
aws ec2 describe-instances
aws iam delete-user --user-name example-user  # DESTRUCTIVE
aws rds delete-db-instance --db-instance-identifier prod-db  # DESTRUCTIVE
```

### 2. `suggest_aws_commands` (Low Risk)

**Purpose:** Suggests AWS CLI commands based on natural language queries.

**Risk Level:** LOW - Read-only tool that only returns command suggestions without executing them.

**Capabilities:**
- Returns up to 10 most likely AWS CLI commands with confidence scores
- Calls external AWS endpoint for suggestions
- Does not execute any commands or access AWS resources

### 3. `get_execution_plan` (Low Risk, Experimental)

**Purpose:** Provides structured, step-by-step guidance for complex AWS tasks.

**Risk Level:** LOW - Read-only tool that returns procedural guidance.

**Availability:** Only available when `EXPERIMENTAL_AGENT_SCRIPTS=true`

**Capabilities:**
- Returns agent scripts with detailed procedures
- Supports custom scripts via `AWS_API_MCP_AGENT_SCRIPTS_DIR`
- Does not execute any commands

---

## AWS CLI Command Risk Categories

Since `call_aws` can execute any AWS CLI command, understanding command risk levels is critical for policy configuration.

### Read-Only Operations (Safe)

These commands retrieve information without modifying AWS resources.

**Examples:**
- `aws ec2 describe-instances`
- `aws s3 ls`
- `aws iam list-users`
- `aws rds describe-db-instances`
- `aws lambda list-functions`
- `aws cloudformation describe-stacks`
- `aws logs describe-log-groups`
- `aws dynamodb describe-table`
- `aws ecs list-clusters`
- `aws eks describe-cluster`
- `aws cloudwatch get-metric-statistics`
- `aws ssm get-parameter`

### Mutating Operations (Moderate Risk)

These commands create or modify AWS resources but are generally reversible.

**Examples:**
- `aws ec2 create-security-group`
- `aws s3 cp` (upload files)
- `aws iam create-user`
- `aws lambda create-function`
- `aws dynamodb put-item`
- `aws ec2 start-instances`
- `aws ec2 stop-instances`
- `aws rds modify-db-instance`
- `aws cloudformation update-stack`
- `aws ecs update-service`
- `aws ssm put-parameter`
- `aws secretsmanager create-secret`

### Destructive Operations (High Risk)

These commands permanently delete or destroy AWS resources and are **irreversible**.

**Critical Examples:**
- `aws iam delete-user` - Permanently deletes IAM user
- `aws iam delete-role` - Permanently deletes IAM role
- `aws s3 rm` - Deletes S3 objects (may be unrecoverable)
- `aws s3api delete-bucket` - Permanently deletes S3 bucket
- `aws ec2 terminate-instances` - Permanently terminates EC2 instances
- `aws rds delete-db-instance` - Permanently deletes RDS database
- `aws dynamodb delete-table` - Permanently deletes DynamoDB table
- `aws lambda delete-function` - Permanently deletes Lambda function
- `aws cloudformation delete-stack` - Deletes entire CloudFormation stack
- `aws ecs delete-cluster` - Deletes ECS cluster
- `aws eks delete-cluster` - Deletes EKS cluster
- `aws secretsmanager delete-secret` - Deletes secret (with recovery window)
- `aws kms schedule-key-deletion` - Schedules KMS key deletion
- `aws route53 delete-hosted-zone` - Deletes DNS hosted zone
- `aws elasticache delete-cache-cluster` - Deletes ElastiCache cluster
- `aws redshift delete-cluster` - Deletes Redshift cluster

---

## Built-in Security Policy

The AWS API MCP Server includes a native security policy mechanism that controls which commands agents can execute.

### Policy File Location

**Path:** `~/.aws/aws-api-mcp/mcp-security-policy.json`

This file is automatically loaded when the server starts. If the file doesn't exist, no policy restrictions are applied (all commands allowed).

### Policy Schema

```json
{
  "version": "1.0",
  "policy": {
    "denyList": [],
    "elicitList": []
  }
}
```

### denyList

Commands in the `denyList` are **completely blocked** and will never be executed.

**Use for:** Commands that should never be allowed under any circumstances.

**Format:** `"aws <service> <operation>"`
- Service: AWS CLI service name (e.g., `iam`, `s3api`, `ec2`)
- Operation: Kebab-case operation name (e.g., `delete-user`, `terminate-instances`)

**Example:**
```json
{
  "version": "1.0",
  "policy": {
    "denyList": [
      "aws iam delete-user",
      "aws iam delete-role",
      "aws iam delete-policy",
      "aws s3api delete-bucket",
      "aws ec2 terminate-instances",
      "aws rds delete-db-instance",
      "aws dynamodb delete-table"
    ],
    "elicitList": []
  }
}
```

### elicitList

Commands in the `elicitList` require **explicit user consent** before execution.

**Use for:** Commands that are sometimes necessary but require human approval.

**Behavior:**
- Agent requests permission via MCP elicitation mechanism
- User must explicitly approve or deny the command
- If client doesn't support elicitation, command is treated as DENIED

**Example:**
```json
{
  "version": "1.0",
  "policy": {
    "denyList": [
      "aws iam delete-user",
      "aws ec2 terminate-instances"
    ],
    "elicitList": [
      "aws ec2 stop-instances",
      "aws lambda delete-function",
      "aws s3 rm",
      "aws cloudformation delete-stack",
      "aws ecs delete-service"
    ]
  }
}
```

### Command Format Requirements

**Important:** The policy uses exact string matching with NO wildcard support.

**Correct Format:**
- ✅ `"aws iam delete-user"`
- ✅ `"aws s3api delete-bucket"`
- ✅ `"aws ec2 terminate-instances"`

**Incorrect Format:**
- ❌ `"aws iam delete-*"` (wildcards not supported)
- ❌ `"aws iam *"` (wildcards not supported)
- ❌ `"iam delete-user"` (missing "aws" prefix)
- ❌ `"aws iam deleteUser"` (wrong case format)

### Complete Working Example

```json
{
  "version": "1.0",
  "policy": {
    "denyList": [
      "aws iam delete-user",
      "aws iam delete-role",
      "aws iam delete-policy",
      "aws iam delete-group",
      "aws s3api delete-bucket",
      "aws ec2 terminate-instances",
      "aws rds delete-db-instance",
      "aws dynamodb delete-table",
      "aws kms schedule-key-deletion",
      "aws route53 delete-hosted-zone"
    ],
    "elicitList": [
      "aws ec2 stop-instances",
      "aws ec2 reboot-instances",
      "aws lambda delete-function",
      "aws s3 rm",
      "aws s3 sync",
      "aws cloudformation delete-stack",
      "aws ecs delete-service",
      "aws secretsmanager delete-secret"
    ]
  }
}
```

---

## Environment-Based Controls

The AWS API MCP Server provides additional security controls via environment variables.

### REQUIRE_MUTATION_CONSENT

**Environment Variable:** `REQUIRE_MUTATION_CONSENT=true`

**Effect:** All non-read-only operations require explicit user consent before execution.

**Use Case:** Maximum safety mode - agent must ask permission for any command that modifies AWS resources.

**How It Works:**
- Server automatically identifies read-only vs mutating operations
- Mutating operations trigger MCP elicitation (user approval prompt)
- If client doesn't support elicitation, mutating operations are blocked

**Example:**
```bash
export REQUIRE_MUTATION_CONSENT=true
# Agent can freely execute: aws ec2 describe-instances
# Agent must ask permission for: aws ec2 stop-instances
```

### READ_OPERATIONS_ONLY_MODE

**Environment Variable:** `READ_OPERATIONS_ONLY_MODE=true`

**Effect:** Only read-only operations are allowed. All mutating operations are blocked.

**Use Case:** Safe exploration mode - agent can query AWS resources but cannot make any changes.

**How It Works:**
- Server maintains a list of read-only operations
- Any command not on the read-only list is automatically blocked
- No user consent option - mutating operations are completely denied

**Example:**
```bash
export READ_OPERATIONS_ONLY_MODE=true
# Agent can execute: aws s3 ls, aws ec2 describe-instances
# Agent CANNOT execute: aws s3 cp, aws ec2 stop-instances
```

### AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS

**Environment Variable:** `AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS=true`

**Default:** `false` (restricted access)

**Effect:** Controls whether `call_aws` can access local files for upload operations.

**Security Implications:**
- When `false`: Agent cannot upload local files to AWS (e.g., `aws s3 cp local-file s3://bucket/`)
- When `true`: Agent can read and upload any local file accessible to the server process

**Recommendation:** Keep at `false` unless file uploads are explicitly required and the agent environment is trusted.

---

## Best Practices

### 1. Start with Restrictive Policies

Begin with a deny-by-default approach and gradually allow specific operations as needed.

**Recommended Baseline Policy:**
```json
{
  "version": "1.0",
  "policy": {
    "denyList": [
      "aws iam delete-user",
      "aws iam delete-role",
      "aws iam delete-policy",
      "aws s3api delete-bucket",
      "aws ec2 terminate-instances",
      "aws rds delete-db-instance",
      "aws dynamodb delete-table",
      "aws lambda delete-function",
      "aws cloudformation delete-stack"
    ],
    "elicitList": [
      "aws ec2 stop-instances",
      "aws ec2 reboot-instances",
      "aws s3 rm",
      "aws iam create-user",
      "aws iam attach-user-policy"
    ]
  }
}
```

### 2. Use Environment Controls for Development

For development and testing environments, use `READ_OPERATIONS_ONLY_MODE` or `REQUIRE_MUTATION_CONSENT`:

```bash
# Safe exploration mode
export READ_OPERATIONS_ONLY_MODE=true

# Or require approval for all changes
export REQUIRE_MUTATION_CONSENT=true
```

### 3. Test Policies Before Production

Before deploying agent workflows to production:
1. Test with `READ_OPERATIONS_ONLY_MODE=true` first
2. Verify agent can complete read-only tasks
3. Gradually enable mutating operations via `elicitList`
4. Monitor agent behavior and adjust policies
5. Only move to production after thorough testing

### 4. Apply Principle of Least Privilege

- Only allow commands the agent actually needs
- Use `denyList` for operations that should never be allowed
- Use `elicitList` for operations that need human oversight
- Regularly review and tighten policies based on actual usage

### 5. Monitor and Audit

- Review agent command execution logs regularly
- Track which commands are being blocked or requiring consent
- Adjust policies based on legitimate needs vs risky behavior
- Set up CloudTrail logging for all AWS API calls

### 6. Layer Security Controls

Combine multiple security mechanisms:
- **IAM Policies:** Restrict what the AWS credentials can do
- **Security Policy File:** Control what commands the agent can attempt
- **Environment Variables:** Add runtime safety controls
- **MCP Client Controls:** Use client-side approval workflows

---

## Policy Priority and Interaction

When multiple security mechanisms are configured, they are evaluated in this priority order:

1. **denyList** (highest priority) - Command is completely blocked
2. **elicitList** - Command requires user consent
3. **READ_OPERATIONS_ONLY_MODE** - Only read operations allowed
4. **REQUIRE_MUTATION_CONSENT** - All mutations require consent
5. **IAM Permissions** - AWS credentials must have permission
6. **Default** - Command is allowed (if all above pass)

**Example Scenario:**
```json
Policy: { "denyList": ["aws ec2 terminate-instances"] }
Environment: REQUIRE_MUTATION_CONSENT=true
Command: aws ec2 terminate-instances

Result: DENIED (denyList takes priority, no consent prompt shown)
```

```json
Policy: { "elicitList": ["aws ec2 stop-instances"] }
Environment: READ_OPERATIONS_ONLY_MODE=true
Command: aws ec2 stop-instances

Result: DENIED (READ_OPERATIONS_ONLY_MODE blocks all mutations)
```

---

## Getting Started

### Step 1: Create Your Policy File

```bash
mkdir -p ~/.aws/aws-api-mcp
cat > ~/.aws/aws-api-mcp/mcp-security-policy.json << 'POLICY'
{
  "version": "1.0",
  "policy": {
    "denyList": [
      "aws iam delete-user",
      "aws ec2 terminate-instances",
      "aws rds delete-db-instance"
    ],
    "elicitList": [
      "aws ec2 stop-instances",
      "aws s3 rm"
    ]
  }
}
POLICY
```

### Step 2: Configure Environment Variables

```bash
# For maximum safety during testing
export REQUIRE_MUTATION_CONSENT=true

# Or for read-only exploration
export READ_OPERATIONS_ONLY_MODE=true
```

### Step 3: Start the Server

```bash
cd src/aws-api-mcp-server
python -m awslabs.aws_api_mcp_server.server
```

### Step 4: Test Your Configuration

Try executing commands through your MCP client and verify:
- Read-only commands execute without prompts
- Commands in `elicitList` trigger consent prompts
- Commands in `denyList` are blocked completely

---

## Additional Resources

- **AWS API MCP Server README:** `src/aws-api-mcp-server/README.md`
- **Security Policy Implementation:** `src/aws-api-mcp-server/awslabs/aws_api_mcp_server/core/security/policy.py`
- **AWS CLI Command Reference:** https://docs.aws.amazon.com/cli/latest/reference/
- **MCP Protocol Specification:** https://modelcontextprotocol.io/

---

## Summary

The AWS API MCP Server provides powerful AWS access to AI agents through the `call_aws` tool. To deploy safely:

1. **Understand the risk:** `call_aws` can execute any AWS CLI command, including destructive operations
2. **Use the built-in security policy:** Configure `denyList` and `elicitList` in `~/.aws/aws-api-mcp/mcp-security-policy.json`
3. **Enable environment controls:** Use `REQUIRE_MUTATION_CONSENT` or `READ_OPERATIONS_ONLY_MODE` for additional safety
4. **Start restrictive:** Begin with tight policies and gradually allow operations as needed
5. **Test thoroughly:** Validate agent behavior in safe environments before production deployment
6. **Monitor continuously:** Review logs and adjust policies based on actual usage patterns

By following these guardrails, you can safely leverage AI agents to automate AWS operations while maintaining control and preventing accidental or malicious resource destruction.
