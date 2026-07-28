# Migration Guide: CCAPI MCP Server to AWS IAC MCP Server

This guide helps you migrate from `awslabs.ccapi-mcp-server` to the [AWS IAC MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-iac-mcp-server).

## Why We're Deprecating

The AWS IAC MCP Server provides a unified infrastructure-as-code experience focused on IaC authoring best practices. While the CCAPI server enabled direct resource manipulation via Cloud Control API, the IAC server encourages an IaC-first workflow with CloudFormation documentation search, template validation (cfn-lint), compliance checking (cfn-guard), deployment troubleshooting, and adds CDK documentation, samples, and best practices.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-iac-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Tool-by-Tool Migration

### get_resource_schema_information

**CCAPI server:** Returned the full CloudFormation schema for any AWS resource type.

**IAC server:** Use `search_cloudformation_documentation` to look up resource type schemas and properties from official CloudFormation documentation.

### list_resources

**CCAPI server:** Listed all resources of a specified type via Cloud Control API.

**IAC server:** No direct replacement. The IAC server focuses on IaC authoring, not resource inventory.

**Alternative:** Use the AWS CLI:
```bash
aws cloudcontrol list-resources --type-name AWS::S3::Bucket
```

### get_resource

**CCAPI server:** Retrieved details of a specific AWS resource via Cloud Control API.

**IAC server:** No direct replacement.

**Alternative:** Use the AWS CLI:
```bash
aws cloudcontrol get-resource --type-name AWS::S3::Bucket --identifier my-bucket
```

### update_resource

**CCAPI server:** Updated resources via Cloud Control API with RFC 6902 JSON Patch operations.

**IAC server:** No direct replacement. The IAC server encourages managing resources through CloudFormation stacks or CDK apps rather than direct API updates.

**Alternative:** Update resources through CloudFormation stack updates or use the AWS CLI:
```bash
aws cloudcontrol update-resource --type-name AWS::S3::Bucket --identifier my-bucket --patch-document '[...]'
```

### create_resource

**CCAPI server:** Created AWS resources via Cloud Control API with security scanning and token-based workflow.

**IAC server:** No direct replacement. Write a CloudFormation template, validate it with `validate_cloudformation_template`, check compliance with `check_cloudformation_template_compliance`, then deploy via `aws cloudformation deploy`.

### delete_resource

**CCAPI server:** Deleted AWS resources via Cloud Control API with confirmation workflow.

**IAC server:** No direct replacement.

**Alternative:** Delete resources through CloudFormation stack deletion or use the AWS CLI:
```bash
aws cloudcontrol delete-resource --type-name AWS::S3::Bucket --identifier my-bucket
```

### get_resource_request_status

**CCAPI server:** Tracked long-running Cloud Control API operations.

**IAC server:** Use `troubleshoot_cloudformation_deployment` to diagnose stack operation failures. For tracking individual Cloud Control API requests, use the AWS CLI:
```bash
aws cloudcontrol get-resource-request-status --request-token <token>
```

### create_template

**CCAPI server:** Generated CloudFormation templates from existing resources using IaC Generator.

**IAC server:** No direct replacement.

**Alternative:** Use the AWS CLI:
```bash
aws cloudformation create-generated-template --generated-template-name my-template --resources '[...]'
aws cloudformation describe-generated-template --generated-template-name my-template
aws cloudformation get-generated-template --generated-template-name my-template --format YAML
```

### generate_infrastructure_code / explain / run_checkov

**CCAPI server:** Token-based workflow for generating infrastructure code, explaining changes to users, and running Checkov security scans.

**IAC server:** The security validation workflow is replaced by:
- `validate_cloudformation_template` for syntax and schema validation with cfn-lint
- `check_cloudformation_template_compliance` for security and compliance checks with cfn-guard

## New Capabilities in the IAC Server

The IAC server provides capabilities the CCAPI server did not have:

| Tool | Description |
|------|-------------|
| `validate_cloudformation_template` | Validate templates with cfn-lint (syntax, schema, properties) |
| `check_cloudformation_template_compliance` | Check templates against security rules with cfn-guard |
| `troubleshoot_cloudformation_deployment` | Diagnose stack failures with CloudTrail integration |
| `get_cloudformation_pre_deploy_validation_instructions` | Pre-deployment validation guidance |
| `search_cdk_documentation` | Search CDK docs, APIs, and patterns |
| `search_cloudformation_documentation` | Search CloudFormation resource types and docs |
| `search_cdk_samples_and_constructs` | Find CDK code examples and constructs |
| `cdk_best_practices` | CDK security and development guidelines |
| `read_iac_documentation_page` | Read full AWS documentation pages |

## Workflow Change

### Before (CCAPI Server)

1. Use `check_environment_variables()` and `get_aws_session_info()` to verify credentials
2. Use `generate_infrastructure_code()` to prepare resource properties
3. Use `explain()` to show user what will be created
4. Use `run_checkov()` to scan for security issues
5. Use `create_resource()` to create resources directly via Cloud Control API
6. Optionally use `create_template()` to generate a template from created resources

### After (IAC Server)

1. Use `search_cloudformation_documentation` to look up resource properties
2. Write a CloudFormation template or CDK app
3. Use `validate_cloudformation_template` to check for errors with cfn-lint
4. Use `check_cloudformation_template_compliance` to verify security compliance with cfn-guard
5. Deploy via `aws cloudformation deploy` or `cdk deploy`
6. Use `troubleshoot_cloudformation_deployment` if deployment fails

The IAC server encourages an **IaC-first workflow** where you define resources in templates rather than creating them directly through API calls.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Direct resource CRUD via Cloud Control API | Not available | Use AWS CLI `aws cloudcontrol` or deploy via CloudFormation/CDK |
| IaC Generator template creation | Not available | Use AWS CLI `aws cloudformation create-generated-template` |
| Token-based security workflow | Replaced | Use `validate_cloudformation_template` and `check_cloudformation_template_compliance` |
| Checkov security scanning | Replaced | cfn-guard provides compliance checking |
| Readonly mode (`--readonly` flag) | Not applicable | IAC server does not perform resource mutations |
| Default tagging (MANAGED_BY tags) | Not applicable | Apply tags in CloudFormation templates |
| AWS session/account info display | Not applicable | Use AWS CLI `aws sts get-caller-identity` |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.ccapi-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.ccapi-mcp-server`
3. The old package will remain on PyPI but will not receive updates
