# Migration Guide: CCAPI MCP Server to AWS IAC MCP Server

This guide helps you migrate from `awslabs.ccapi-mcp-server` to the [AWS IAC MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-iac-mcp-server).

## Why We're Deprecating

The original owner has departed and no service team has taken ownership. The AWS IAC MCP Server provides a unified infrastructure-as-code experience covering CloudFormation, CDK, and Terraform, and includes CloudFormation template validation, compliance checking, and deployment troubleshooting.

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

### check_environment_variables / get_aws_session_info / get_aws_account_info -- No direct replacement

**CCAPI server:** Token-based workflow requiring sequential credential validation before any resource operation.

**IAC server:** No token-based workflow. AWS credentials are validated through standard boto3 credential chain. The IAC server focuses on documentation, validation, and compliance rather than direct resource management.

### generate_infrastructure_code / explain / run_checkov -- Partial replacement

**CCAPI server:** Generated CloudFormation templates from resource properties, explained configurations to users, and ran Checkov security scans.

**IAC server:** Provides `validate_cloudformation_template` (cfn-lint) and `check_cloudformation_template_compliance` (cfn-guard) for template validation and compliance checking. No automatic template generation from properties.

### create_resource / update_resource / delete_resource / list_resources / get_resource -- No direct replacement

**CCAPI server:** Full CRUD operations on AWS resources via Cloud Control API with token-based security workflow.

**IAC server:** Does not perform direct resource operations. The IAC server is focused on infrastructure-as-code authoring assistance (documentation, validation, compliance, troubleshooting).

**Alternative:** Use the AWS CLI (`aws cloudcontrol`) for direct Cloud Control API operations, or write CloudFormation/CDK templates and deploy them through standard tooling.

### get_resource_schema_information -- Partial replacement

**CCAPI server:** Returned CloudFormation schema for any AWS resource type.

**IAC server:** Use `search_cloudformation_documentation` to look up resource type schemas and properties from official documentation.

### get_resource_request_status -- No direct replacement

**CCAPI server:** Tracked long-running Cloud Control API operations.

**Alternative:** Use the AWS CLI: `aws cloudcontrol get-resource-request-status --request-token <token>`

### create_template -- No direct replacement

**CCAPI server:** Generated CloudFormation templates from existing resources using IaC Generator.

**Alternative:** Use the AWS CLI directly:
```bash
aws cloudformation create-generated-template --generated-template-name my-template --resources ...
```

## New Capabilities in the IAC Server

The IAC server provides capabilities the CCAPI server did not have:

| Tool | Description |
|------|-------------|
| `validate_cloudformation_template` | Validate templates with cfn-lint (syntax, schema, properties) |
| `check_cloudformation_template_compliance` | Check templates against security rules with cfn-guard |
| `troubleshoot_cloudformation_deployment` | Diagnose stack failures with CloudTrail integration |
| `get_cloudformation_pre_deploy_validation_instructions` | Pre-deployment validation guidance |
| `search_cdk_documentation` | Search CDK docs, APIs, and patterns |
| `search_cloudformation_documentation` | Search CloudFormation docs and resource types |
| `search_cdk_samples_and_constructs` | Find CDK code examples and constructs |
| `cdk_best_practices` | CDK security and development guidelines |
| `read_iac_documentation_page` | Read full documentation pages |

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Direct resource CRUD via Cloud Control API | Not available | Use AWS CLI or deploy via CloudFormation/CDK |
| Token-based security workflow | Not available | Use standard IAM permissions and deployment pipelines |
| Automatic resource tagging | Not available | Define tags in CloudFormation/CDK templates |
| IaC Generator template creation | Not available | Use AWS CLI `cloudformation create-generated-template` |
| Checkov security scanning | Replaced by cfn-lint + cfn-guard | Use `validate_cloudformation_template` and `check_cloudformation_template_compliance` |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.ccapi-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.ccapi-mcp-server`
3. The old package will remain on PyPI but will not receive updates
