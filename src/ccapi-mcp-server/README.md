# AWS Cloud Control API (CCAPI) MCP Server

Model Context Protocol (MCP) server that enables LLMs to directly create and manage over 1,100 AWS resources through natural language using AWS Cloud Control API and IaC Generator with Infrastructure as Code best practices.

## Prerequisites

- All prerequisites listed in the [Installation and Setup](https://github.com/awslabs/mcp#installation-and-setup) section within the awslabs/mcp README should be satisfied
- Valid AWS credentials
- Ensure your IAM role or user has the necessary permissions (see [Security Considerations](#security-considerations))

## Features

- **Resource Creation**: Uses a declarative approach to create any of 1,100+ AWS resources through Cloud Control API
- **Resource Reading**: Reads all properties and attributes of specific AWS resources
- **Resource Updates**: Uses a declarative approach to apply changes to existing AWS resources
- **Resource Deletion**: Safely removes AWS resources with proper validation
- **Resource Listing**: Enumerates all resources of a specified type across your AWS environment
- **Schema Information**: Returns detailed CloudFormation schema for any resource to enable more effective operations
- **Natural Language Interface**: Transform infrastructure-as-code from static authoring to dynamic conversations
- **Partner Resource Support**: Works with both AWS-native and partner-defined resources
- **Template Generation**: Generates a template on created/existing resources for a [subset of resource types](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import-supported-resources.html)

## Secure Workflow

For resource creation and updates, the server follows this secure workflow:

1. Check for AWS credentials and display account ID and region to the user
2. Generate infrastructure code with properties and CloudFormation template
3. **Explain the configuration** - Show user exactly what will be created/modified
4. Run security scans against the template (if SECURITY_SCANNING=enabled)
5. If checks pass (or security scanning disabled with warning), attempt to create/update resource(s) with the AWS Cloud Control API
6. Automatically add default management tags to resources for tracking and support
7. Validate that the resource(s) were created/updated successfully
8. Provide a summary of what was done, including any security warnings
9. (Optional) create an IaC template that aligns to the resources it just created or updated

This workflow ensures that:

- **Full Transparency**: Users see exactly what will be created/modified before execution via the `explain()` step
- **Security Validation**: Resources are scanned for security issues before creation/modification (when enabled, default configuration)
- **Informed Consent**: Users cannot accidentally create resources without understanding the configuration
- **Audit Trail**: Default management tags are automatically applied for tracking and support
- **Flexible Security**: Security scanning can be enabled/disabled based on environment needs
- **IaC Preservation**: Users have the option to preserve their infrastructure as code
- **Multiple Formats**: Multiple IaC formats are supported for maximum flexibility

## Security Architecture

The MCP server uses a token-based workflow system that ensures:

- **Sequential validation**: Each step must be completed before the next
- **Server-side enforcement**: Tokens are generated and validated server-side
- **No bypass capability**: AI agents cannot skip security steps or fake credentials
- **Audit trail**: All operations are tracked through the token chain

This prevents AI agents from bypassing security scans, credential checks, or user explanations.

## Security Protections

The MCP server implements several critical security protections:

### Credential Awareness

- Always displays AWS account ID and region before any CREATE/UPDATE operation
- Ensures users are aware of which account will be affected by changes

### Deletion Safeguards

- Requires double confirmation for any resource deletion
- Prevents mass deletion of AWS infrastructure
- For cleanup operations, uses IaC Generator to create templates instead of direct deletion
- Provides safer alternatives with better control and rollback options

### Policy Restrictions

- Blocks creation of overly permissive IAM policies
- Prevents configurations with "AWS": "\*" as a principal
- Blocks "Effect": "Allow" combined with "Action": "_" and "Resource": "_"
- Declines requests for public access to sensitive resources
- Prevents disabling encryption for sensitive data

## Authentication

This MCP server requires authentication to an AWS account, as its primary intent is to be able to manage infrastructure. There are multiple options you have for authentication such as:

### AWS Profile

This can be set via the AWS CLI by running `aws configure` and following the instructions.

### Environment Variables

You can set environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION) by exporting them.

## Environment Variables

The MCP server supports several environment variables to control its behavior:

### AWS Configuration

| Variable      | Default                | Description                                |
| ------------- | ---------------------- | ------------------------------------------ |
| `AWS_REGION`  | _(see priority below)_ | AWS region for operations                  |
| `AWS_PROFILE` | _(empty)_              | AWS profile name to use for authentication |

**AWS Region Resolution Order:**

The MCP server follows boto3's standard region resolution chain (highest to lowest priority):

1. **Function argument**: `region` parameter passed to MCP tools (highest priority)
2. **AWS_REGION environment variable**: Explicitly set region via environment
3. **AWS profile region**: Region configured in `~/.aws/config` for the active profile
4. **Default fallback**: `us-east-1` as the final fallback

This ensures consistent behavior with other AWS tools and SDKs. The region resolution is handled automatically by boto3's credential chain.

**When to set AWS_REGION:**

- **To override region**: When you want to use a different region than the default
- **With environment variables**: When using `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` and don't want `us-east-1`
- **With profiles/SSO**: When you want to override the profile's configured region
- **Not needed**: When using AWS profiles/SSO and you want the profile's configured region, or when `us-east-1` is acceptable

### AWS Credential Chain

The server uses boto3's standard credential chain automatically:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS profile from `~/.aws/credentials` or `~/.aws/config`
3. IAM roles (EC2 instance, ECS task, EKS pod)
4. AWS SSO (if configured in profile)

**SSO Token Management**: When SSO tokens expire, the server provides clear instructions to refresh them with `aws sso login --profile your-profile`.

### Server Configuration

| Variable            | Default     | Description                                                                                                                                 |
| ------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `FASTMCP_LOG_LEVEL` | _(not set)_ | Logging level (ERROR, WARN, INFO, DEBUG)                                                                                                    |
| `SECURITY_SCANNING` | `enabled`   | Enable/disable Checkov security scanning (`enabled` or `disabled`). When disabled, shows warning but allows resource operations to proceed. |

### Default Tagging

The server automatically adds these identification tags to all supported resources:

- `MANAGED_BY`: `CCAPI-MCP-SERVER`
- `MCP_SERVER_SOURCE_CODE`: `https://github.com/awslabs/mcp/tree/main/src/ccapi-mcp-server`
- `MCP_SERVER_VERSION`: `1.0.0` (current version)

These tags help identify resources created by the MCP server for support and troubleshooting purposes. Users can add additional custom tags through conversation with the LLM.

### AWS Account Information Display

The server automatically displays AWS account information on startup:

- **AWS Profile**: The profile being used (if any)
- **Authentication Type**: How you're authenticated (SSO Profile, Standard AWS Profile, Environment Variables, Assume Role Profile)
- **AWS Account ID**: The AWS account ID
- **AWS Region**: The region where resources will be created
- **Read-only Mode**: Whether the server is in read-only mode
- **Security Scanning**: Whether Checkov security scanning is enabled

This ensures you always know which AWS account and region will be affected by operations, and what security measures are in place.

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.ccapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY2NhcGktbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Cloud%20Control%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ccapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

**Before installation, configure AWS credentials using one of these methods:**

- **AWS Profile**: Run `aws configure` and set `AWS_PROFILE` environment variable (region from profile used automatically)
- **Environment Variables**: Export `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (defaults to `us-east-1`, set `AWS_REGION` to override)
- **AWS SSO**: Configure SSO profile and set `AWS_PROFILE` (region from profile used automatically)
- **Instance Role**: Use EC2 instance role or ECS task role (automatic detection, may need `AWS_REGION`)

Ensure your IAM role or user has the necessary permissions (see [Security Considerations](#security-considerations)).

### Configuration

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.ccapi-mcp-server@latest",
        "awslabs.ccapi-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```


_Note: Uses the default region from your AWS profile. Add `"AWS_REGION": "us-west-2"` (or other desired AWS Region) to override._

**Security Scanning Disabled:**

You have control on enabling/disabling Checkov security scanning on all infrastructure before creation/updates. The following configuration will disable security scanning:

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "disabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

**Alternative configurations:**

**Using SSO via AWS IAM Identity Center:**

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-sso-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

_Note: Run `aws sso login --profile your-sso-profile` before starting the MCP server_

**Using Environment Variables for Credentials:**

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

_Note: Ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are exported in your shell_

**Read-Only Mode (Security Feature):**

To prevent the MCP server from performing any mutating actions (Create/Update/Delete), use the `--readonly` command-line flag. This is a security feature that cannot be bypassed via environment variables. Note, this is why the `DEFAULT_TAGS`, and `SECURITY_SCANNING` environment variables are omitted from the follow example. Even if they were present, the `--readonly` flag would prevent any CREATE/UPDATE/DELETE operations, which cause those environment variables to have no use:

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest", "--readonly"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/ccapi-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE  # pragma: allowlist secret
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  # pragma: allowlist secret
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk  # pragma: allowlist secret
```

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/ccapi-mcp-server:latest",
        "--readonly" // Optional paramter if you would like to restrict the MCP to only read actions
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

NOTE: Your credentials will need to be kept refreshed from your host

## Available MCP Tools

**Tool Ordering & Workflow Enforcement**: These tools are designed with parameter dependencies that enforce proper workflow order. LLMs must follow the logical sequence: environment setup → security validation → resource operations. This prevents security bypasses and ensures proper credential validation.

### Core Tools

#### check_environment_variables()

**Requirements**: None (starting point)

Checks if AWS credentials are properly configured through AWS_PROFILE or environment variables. Returns detailed information about credential source, authentication type, and configuration status.
**Example**: Verify that AWS credentials are available before performing operations.
**Returns**: `environment_token` for use with `get_aws_session_info()`, plus environment variables, AWS profile, region, authentication type (sso_profile, standard_profile, assume_role_profile, env), and configuration status.

#### get_aws_session_info()

**Requirements**: `environment_token` parameter from `check_environment_variables()`

Provides detailed information about the current AWS session including account ID, region, credential source, and masked credential information for security.
**Example**: Display which AWS account and region will be affected by operations.
**Use when**: You need detailed session info and have already called `check_environment_variables()`.
**Security**: Automatically masks sensitive credential information (shows only last 4 characters).
**Returns**: `credentials_token` for use with `generate_infrastructure_code()`

#### get_aws_account_info()

**Requirements**: None (calls `check_environment_variables()` internally)

Convenience tool that automatically calls `check_environment_variables()` internally, then `get_aws_session_info()`. Returns the same information but requires no parameters.
**Example**: "What AWS account am I using?" - Quick one-step account info.
**Use when**: You want account info quickly without calling `check_environment_variables()` first.

#### generate_infrastructure_code()

**Requirements**: `credentials_token` parameter from `get_aws_session_info()`

Prepares resource properties for Cloud Control API operations, applies default management tags, and generates a CloudFormation-format template for security scanning. **Important**: The CloudFormation service is never involved - the template is only used by Checkov for security analysis.

**Consistency guarantee**: The exact same properties object is used for both the CF template (for Checkov scanning) and passed to `create_resource()`/`update_resource()` (for CCAPI operations). This ensures what gets security-scanned is identical to what gets deployed.

**Example**: Process S3 bucket properties, apply default tags, create CF-format template for Checkov, then use the same properties for CCAPI resource creation.
**Returns**: `generated_code_token` for use with `explain()`, CloudFormation template for security scanning, and properties for explanation.
**Workflow**: generate_infrastructure_code() → explain() → run_checkov() (if enabled) → create_resource().

#### explain()

**Requirements**: `generated_code_token` from `generate_infrastructure_code()` (for infrastructure operations) OR `content` parameter (for general explanations)

Explains any data in clear, human-readable format. For infrastructure operations, this tool consumes the `generated_code_token` and returns an `explained_token` that must be used for create/update/delete operations.

**Infrastructure workflow**:

- Takes `generated_code_token` from `generate_infrastructure_code()`
- Provides comprehensive explanation of what will be created/updated/deleted
- Returns `explained_token` for use with `create_resource()`/`update_resource()`/`delete_resource()`
- **Security**: Ensures users see exactly what will be created/modified before execution.

**General data explanation**:

- Pass any data in `content` parameter
- Explains JSON, YAML, dictionaries, lists, API responses, configurations
- No token workflow required

**Example**: Explain S3 bucket configuration when fetching an existing bucket, or explain general API response data.

#### run_checkov()

**Requirements**: `explained_token` from `explain()`

Runs Checkov security and compliance scanner on server-stored CloudFormation template. Returns scan results for user review.

**Security validation behavior depends on SECURITY_SCANNING environment variable**:

- **When SECURITY_SCANNING=enabled**: This tool is required, returns scan results for user review
- **When SECURITY_SCANNING=disabled**: Shows warning, proceeds without security validation

**Example**: `run_checkov(explained_token)` - Returns security scan results.
**Returns**: `security_scan_token` for use with `create_resource()` (when security scanning enabled), plus detailed scan results.

### Resource Modification Tools (CRUDL)

#### create_resource()

**Requirements**: `credentials_token` from `get_aws_session_info()` AND `explained_token` from `explain()`

**Security Requirements**:

- When SECURITY_SCANNING=enabled: Requires `security_scan_token` from `run_checkov()`
- When SECURITY_SCANNING=disabled: Shows security warning but proceeds without validation token

Creates an AWS resource using the AWS Cloud Control API with a declarative approach. Automatically adds default management tags for tracking and support.
**Example**: Create an S3 bucket with versioning and encryption enabled.
**Security**: Uses only properties that were explained to the user via `explain()` tool.

#### get_resource()

**Requirements**: None

Gets details of a specific AWS resource using the AWS Cloud Control API.
**Example**: Get the configuration of an EC2 instance.
**Returns**: Resource identifier and detailed properties.

#### update_resource()

**Requirements**: `credentials_token` from `get_aws_session_info()` AND `explained_token` from `explain()`

**Security Requirements**:

- When SECURITY_SCANNING=enabled: Requires `security_scan_token` from `run_checkov()`
- When SECURITY_SCANNING=disabled: Shows security warning but proceeds without validation token

Updates an AWS resource using the AWS Cloud Control API with RFC 6902 JSON Patch operations.
**Example**: Update an RDS instance's storage capacity.
**Security**: Requires explanation of changes via `explain()` tool before execution.

#### delete_resource()

**Requirements**: `credentials_token` from `get_aws_session_info()` AND `explained_token` from `explain()`

Deletes an AWS resource using the AWS Cloud Control API. Requires explicit confirmation and explanation of what will be deleted.
**Example**: Remove an unused NAT gateway.
**Security**: Requires explanation of deletion impact via `explain()` tool and explicit confirmation.

#### list_resources()

**Requirements**: None

Lists AWS resources of a specified type using AWS Cloud Control API.
**Example**: List all EC2 instances in a region.

### Utility Tools

#### get_resource_schema_information()

**Requirements**: None

Get schema information for an AWS CloudFormation resource.
**Example**: Get the schema for AWS::S3::Bucket to understand all available properties.

#### get_resource_request_status()

**Requirements**: `request_token` from create/update/delete operations

Get the status of a mutation that was initiated by create/update/delete resource.
**Example**: Give me the status of the last request I made.

#### create_template()

**Requirements**: None (but typically used after resource operations)

Creates CloudFormation templates from existing AWS resources using AWS CloudFormation's IaC Generator API. **Currently only generates CloudFormation templates** in JSON or YAML format. While this MCP tool doesn't directly generate other IaC formats like Terraform or CDK, LLMs can use their native capabilities to convert the generated CloudFormation template to other formats - though this conversion happens outside the MCP server's scope.
**Example**: Generate a CloudFormation YAML template from existing S3 buckets and EC2 instances, then ask the LLM to convert it to Terraform HCL.

### Token Workflow Summary

**Example workflow for create/update operations:**

1. `check_environment_variables()` → `environment_token`
2. `get_aws_session_info(environment_token)` → `credentials_token`
3. `generate_infrastructure_code(credentials_token)` → `generated_code_token`
4. `explain(generated_code_token)` → `explained_token`
5. `run_checkov(explained_token)` → `security_scan_token` (if SECURITY_SCANNING=enabled)
6. `create_resource(credentials_token, explained_token, security_scan_token)`

**No-token tools:** `get_resource()`, `list_resources()`, `get_resource_schema_information()`, `create_template()`, `get_aws_account_info()`

## LLM Tool Selection Guidelines

**Important**: When using multiple MCP servers, LLMs may choose tools from any available server without consideration for which is most appropriate. MCP has no built-in orchestration or enforcement mechanisms at this time - LLMs can use any tool from any server at will.

### Common Tool Selection Conflicts

- **Multiple Infrastructure MCP Servers**: Using CCAPI MCP server alongside other MCP servers that perform similar functions (such as Terraform MCP, CDK MCP, CFN MCP) may cause LLMs to randomly choose between them
- **Built-in Tools**: LLMs may choose built-in tools instead of this MCP server's tools:
  - Amazon Q Developer CLI: `use_aws`, `execute_bash`, `fs_read`, `fs_write`
  - Other tools may have similar built-in AWS or system capabilities

#### The `use_aws` Problem

**Most Problematic**: The `use_aws` tool (part of Amazon Q Developer CLI) is particularly problematic because it directly competes with this MCP server's AWS operations but operates separately, meaning it won't use any of the helpful features available in this MCP server such as Checkov security scanning.

**What happens when LLM uses `use_aws`:**

- ❌ No Checkov security scanning
- ❌ No workflow validation
- ❌ No credential verification display
- ❌ No resource tagging
- ❌ CCAPI MCP Server is not involved at all

**If this happens:**

1. Tell the LLM: "Please use the CCAPI MCP Server instead for AWS operations"
2. Experiment with prompts like "Using the CCAPI MCP server, create..."
3. For a scalable solution, implement the rules/instructions mentioned below

**Note**: This is not a limitation of the CCAPI MCP Server - it's a current MCP protocol limitation. MCP has no native tool ordering concept or functionality, allowing LLMs to choose any available MCP server/tool. This flexibility is both good (choice) and problematic (undesirable sever/tool selection). We use a token-based approach to enforce some ordering in tool usage the LLM must follow, however this does not span across multiple MCP servers. It is internal to this MCP server.

### Recommendation

Consult your LLM tool's documentation (Cursor, Cline, Amazon Q Developer, etc.) for how to provide rules/context/instructions to guide MCP server/tool selection. Most support some form of instruction mechanism.

**Example instruction content:**

```markdown
# AWS Tool Selection Rules - MANDATORY FOR ALL LLM RESPONSES

## STEP 1: Always Use CCAPI MCP Server First

**TRIGGER CONDITIONS:**

- ANY mention of AWS services or resources
- ANY request involving AWS infrastructure, applications, or services
- When in doubt, default to offering CCAPI MCP Server

**REQUIRED ACTION:**
ASK: "This seems like a good fit for the AWS Cloud Control API MCP server. Would you like to use the CCAPI MCP server for this?"

## STEP 2: Only If CCAPI MCP Server Fails

**IF ERROR OCCURS:**

1. Show exact error message to user
2. Explain: "⚠️ SECURITY WARNING: Fallback tools (use_aws, aws_cli) will bypass ALL security scanning and the CCAPI MCP Server entirely."
3. Ask: "How do you want to proceed: (a) troubleshoot CCAPI MCP, (b) use unsecured AWS CLI, or (c) generate template?"
4. Wait for explicit user choice before proceeding

## FORBIDDEN ACTIONS

- Never use use_aws, aws_cli, or executeBash for AWS operations without trying CCAPI MCP Server first
- Never skip the user confirmation steps
```

## Basic Usage

Examples of how to use the AWS Infrastructure as Code MCP Server:

- "Create a new S3 bucket with versioning and encryption enabled"
- "List all EC2 instances in the production environment"
- "Update the RDS instance to increase storage to 500GB"
- "Delete unused NAT gateways in VPC-123"
- "Set up a three-tier architecture with web, app, and database layers"
- "Create a disaster recovery environment in us-east-1"
- "Configure CloudWatch alarms for all production resources"
- "Implement cross-region replication for critical S3 buckets"
- "Show me the schema for AWS::Lambda::Function"
- "Create a template for all the resources we created and modified"

## Resource Type support

Resources which are supported by this MCP and the supported operations can be found here: https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/supported-resources.html

## Security Considerations

When using this MCP server, you should consider:

- Ensuring proper IAM permissions are configured before use
- Use AWS CloudTrail for additional security monitoring
- Configure resource-specific permissions when possible instead of wildcard permissions
- Consider using resource tagging for better governance and cost management
- Review all changes made by the MCP server as part of your regular security reviews
- If you would like to restrict the MCP to readonly operations, specify --readonly True in the startup arguments for the MCP

### Required IAM Permissions

Ensure your AWS credentials have the following minimum permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudcontrol:ListResources",
        "cloudcontrol:GetResource",
        "cloudcontrol:CreateResource",
        "cloudcontrol:DeleteResource",
        "cloudcontrol:UpdateResource",
        "cloudformation:CreateGeneratedTemplate",
        "cloudformation:DescribeGeneratedTemplate",
        "cloudformation:GetGeneratedTemplate"
      ],
      "Resource": "*"
    }
  ]
}
```

## Future Enhancements

- **IaC Format Conversion**: Add support for converting CloudFormation templates to other IaC formats (Terraform HCL, CDK TypeScript, CDK Python) in the `create_template` tool

## Limitations

- Operations are limited to resources supported by AWS Cloud Control API and Iac Generator
- Performance depends on the underlying AWS services' response times
- Some complex resource relationships may require multiple operations
- This MCP server can only manage resources in the AWS regions where Cloud Control API and/or Iac Generator is available
- Resource modification operations may be limited by service-specific constraints
- Rate limiting may affect operations when managing many resources simultaneously
- Some resource types might not support all operations (create, read, update, delete)
- Generated templates are primarily intended for importing existing resources into a CloudFormation stack and may not always work for creating new resources (in another account or region)
- Template generation currently supports CloudFormation format only (JSON/YAML)
