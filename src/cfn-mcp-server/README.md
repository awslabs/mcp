# CloudFormation MCP Server

Model Context Protocol (MCP) server that enables LLMs to directly create and manage over 1,100 AWS resources through natural language using AWS Cloud Control API and Iac Generator with Infrastructure as Code best practices.

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

## Prerequisites

1. Configure AWS credentials:
   - Via AWS CLI: `aws configure`
   - Or set environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
2. Ensure your IAM role or user has the necessary permissions (see [Security Considerations](#security-considerations))

## Installation

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.cfn-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.cfn-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-named-profile"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

If you would like to prevent the MCP from taking any mutating actions (i.e. Create/Update/Delete Resource), you can specify the readonly flag as demonstrated below:

```json
{
  "mcpServers": {
    "awslabs.cfn-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.cfn-mcp-server@latest",
        "--readonly"
      ],
      "env": {
        "AWS_PROFILE": "your-named-profile"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/cfn-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.cfn-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/cfn-mcp-server:latest",
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

## Tools

### Resource Management Tools

#### get_resource_schema_information
Get schema information for an AWS resource type.
**Example**: Get the schema for AWS::S3::Bucket to understand all available properties.

#### list_resources
Lists AWS resources of a specified type across your AWS account.
**Example**: List all EC2 instances in a region.

#### get_resource
Gets detailed information about a specific AWS resource.
**Example**: Get the configuration of an EC2 instance.

#### create_resource
Creates an AWS resource with specified properties using a declarative approach.
**Example**: Create an S3 bucket with versioning and encryption enabled.

#### update_resource
Updates existing AWS resources using RFC 6902 JSON Patch operations.
**Example**: Update an RDS instance's storage capacity.

#### delete_resource
Deletes AWS resources from your account with proper validation.
**Example**: Remove an unused NAT gateway.

#### get_resource_request_status
Track the status of long-running resource operations.
**Example**: Check the status of a long-running RDS instance update operation.

### Template and Infrastructure Management Tools

#### create_template
Generate CloudFormation templates from existing resources using IaC Generator API.
**Example**: Create a YAML template for my S3 buckets and their associated resources.

#### analyze_stack
Analyze this {stack name} and return detailed resource information.
**Example**: Analyze this production-stack

#### propose_new_stacks
Propose new stacks in your AWS account with resource limits and optional template generation.
**Example**: Propose new stacks for my unmanaged resources in my AWS account.

### Resource Discovery and Analysis Tools

#### list_resources_by_filter
List AWS resources with resources from a resource scan with  filtering by type, tags, and identifiers.
**Example**: Show me all resources tagged with "environment=production".

#### list_related_resources
Find AWS resources related to specified resources using dependency analysis.
**Example**: Show me all resources related to these resource {list}

#### start_resource_scan
Initiate resource scans for specific resource types or the entire AWS account.
**Example**: Scan my AWS account.

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
                "cloudformation:DescribeStacks",
                "cloudformation:ListStackResources",
                "cloudformation:DescribeStackResources",
                "cloudformation:ListResourceScanResources",
                "cloudformation:ListResourceScanRelatedResources",
                "cloudformation:CreateGeneratedTemplate",
                "cloudformation:DescribeGeneratedTemplate",
                "cloudformation:GetGeneratedTemplate"
            ],
            "Resource": "*"
        }
    ]
}
```

## Limitations

- Operations are limited to resources supported by AWS Cloud Control API and Iac Generator
- Performance depends on the underlying AWS services' response times
- Some complex resource relationships may require multiple operations
- This MCP server can only manage resources in the AWS regions where Cloud Control API and/or Iac Generator is available
- Resource modification operations may be limited by service-specific constraints
- Rate limiting may affect operations when managing many resources simultaneously
- Some resource types might not support all operations (create, read, update, delete)
- Generated templates are primarily intended for importing existing resources into a CloudFormation stack and may not always work for creating new resources (in another account or region)
