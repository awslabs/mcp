# CloudWatch Application Signals MCP Server

An MCP (Model Context Protocol) server that provides tools for monitoring and analyzing AWS services using [AWS Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html).

This server enables AI assistants like Claude, GitHub Copilot, and Amazon Q to help you monitor service health, analyze performance metrics, track SLO compliance, and investigate issues using distributed tracing.

## Features

### Available Tools

1. **`list_monitored_services`** - List all services monitored by AWS Application Signals
   - Get an overview of all monitored services
   - See service names, types, and key attributes
   - Identify which services are being tracked

2. **`get_service_detail`** - Get detailed information about a specific service
   - Understand service configuration and deployment
   - View available CloudWatch metrics
   - Find associated log groups

## Installation

### Installing via Smithery

To install CloudWatch Application Signals MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/awslabs.cloudwatch-appsignals-mcp-server):

```bash
npx @smithery/cli install awslabs.cloudwatch-appsignals-mcp-server --client claude
```

### Installing via Cursor

To install CloudWatch Application Signals MCP Server for Cursor automatically:

[![Install in Cursor](https://img.shields.io/badge/Install%20in%20Cursor-Install-blue?style=for-the-badge&logo=cursor&logoColor=white)](https://cursor.com/settings/extensions/install?server=awslabs.cloudwatch-appsignals-mcp-server)

### Installing via `uv`

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *awslabs.cloudwatch-appsignals-mcp-server*.

### Installing via Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  When installing a development or unpublished server, add the `--directory` flag:

  ```json
  {
    "mcpServers": {
      "awslabs.cloudwatch-appsignals-mcp-server": {
        "command": "uvx",
        "args": ["--from", "/absolute/path/to/cloudwatch-appsignals-mcp-server", "awslabs.cloudwatch-appsignals-mcp-server"]
      }
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>

  ```json
  {
    "mcpServers": {
      "awslabs.cloudwatch-appsignals-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.cloudwatch-appsignals-mcp-server"]
      }
    }
  }
  ```
</details>

### Installing for Amazon Q (Preview)

- Start Q Developer from [here](https://q.aws/chat).
- Click on "Manage Connectors" and choose MCP Client.
- Click "Add New Context Connector," enter a name like "CloudWatch AppSignals," and enter the command in the format: `uvx awslabs.cloudwatch-appsignals-mcp-server`.
- Verify it shows "Connected" in green under the connector.

### Debugging

You can use the MCP inspector to debug the server. For `uvx` installations:

```bash
npx @modelcontextprotocol/inspector uvx awslabs.cloudwatch-appsignals-mcp-server
```

Or if you've installed the package in a specific directory:

```bash
cd /path/to/cloudwatch-appsignals-mcp-server
npx @modelcontextprotocol/inspector uv run awslabs.cloudwatch-appsignals-mcp-server
```

## Usage Examples

### Example 1: Getting Started with Service Monitoring
```
User: "What services are being monitored by Application Signals?"
Assistant: I'll check what services are currently being monitored by AWS Application Signals.

[Uses list_monitored_services tool]

I found 3 services being monitored:

• Service: api-gateway-service
  Type: AWS::ApiGateway::RestApi
  Key Attributes:
    Name: api-gateway-service
    Type: AWS::ApiGateway::RestApi
    Environment: production

• Service: order-service
  Type: AWS::ECS::Service
  Key Attributes:
    Name: order-service
    Type: AWS::ECS::Service
    Environment: production
    Platform: ECS

• Service: payment-lambda
  Type: AWS::Lambda::Function
  Key Attributes:
    Name: payment-lambda
    Type: AWS::Lambda::Function
    Environment: production
```

### Example 2: Investigating Service Details
```
User: "Tell me more about the order-service"
Assistant: I'll get detailed information about the order-service.

[Uses get_service_detail tool]

Here are the details for order-service:

Key Attributes:
  Name: order-service
  Type: AWS::ECS::Service
  Environment: production

Additional Attributes:
  Platform: ECS
  Application: ecommerce-app
  Telemetry.SDK: opentelemetry-1.9.0

Metric References (15 total):
  • AWS/ApplicationSignals/Latency
    Type: GAUGE
    Dimensions: Service=order-service, Operation=GetOrder

  • AWS/ApplicationSignals/ErrorRate
    Type: GAUGE
    Dimensions: Service=order-service, Operation=CreateOrder

Log Group References (2 total):
  • /aws/ecs/order-service
  • /aws/application-signals/order-service
```

## Configuration

### Required AWS Permissions

The server requires the following AWS IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "application-signals:ListServices",
        "application-signals:GetService",
        "application-signals:ListServiceLevelObjectives",
        "application-signals:GetServiceLevelObjective",
        "application-signals:BatchGetServiceLevelObjectiveBudgetReport",
        "cloudwatch:GetMetricData",
        "logs:GetQueryResults",
        "logs:StartQuery",
        "logs:StopQuery",
        "xray:GetTraceSummaries",
        "xray:BatchGetTraces"
      ],
      "Resource": "*"
    }
  ]
}
```

### Environment Variables

- `AWS_REGION` - AWS region (defaults to us-east-1)
- `MCP_CLOUDWATCH_APPSIGNALS_LOG_LEVEL` - Logging level (defaults to INFO)

### AWS Credentials

This server uses the standard AWS credential chain via boto3. It will automatically use credentials from:
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.)
- AWS credentials file (`~/.aws/credentials`)
- AWS config file (`~/.aws/config`)
- IAM roles (when running on EC2, ECS, Lambda, etc.)
- And other standard AWS credential providers

No additional credential configuration is needed beyond your standard AWS setup.

## Development

This server is part of the AWS Labs MCP collection. For development and contribution guidelines, please see the main repository documentation.

## License

This project is licensed under the Apache License, Version 2.0. See the LICENSE file for details.
