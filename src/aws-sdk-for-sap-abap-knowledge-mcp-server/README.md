# AWS SDK for SAP ABAP Knowledge MCP Server

A fully managed remote MCP server that provides AI coding assistants with specialized knowledge about the [AWS SDK for SAP ABAP](https://aws.amazon.com/sdk-for-sap-abap/), enabling them to generate syntactically correct ABAP code for AWS service integrations.

> **Important Note:** Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

## Key Features

- Specialized knowledge about the AWS SDK for SAP ABAP across 200+ AWS services
- ABAP-specific method signatures, data type definitions, and factory class names
- Dynamic ABAP code generation for session creation, client initialization, and operation calls
- Daily-updated knowledge base synchronized with SDK releases
- Zero installation — no local dependencies, no authentication required
- Optimized for agentic workflows with efficient context window usage

## AWS SDK for SAP ABAP Knowledge capabilities

- **Service discovery**: Find which AWS services are available in the ABAP SDK, including service names, SDK IDs, and three-letter acronyms (TLAs) used in ABAP class names
- **Operation details**: Get ABAP method signatures, parameters, and return types for any SDK operation
- **Data type definitions**: Retrieve ABAP structure definitions for input/output types used in SDK operations
- **Code examples**: Access ABAP code examples for SDK operations including method signatures and syntax demonstrations
- **Code generation**: Generate ready-to-use ABAP code for session creation, client initialization, and operation calls with correct types and exception handling

## Tools

- `list_aws_sdk_for_abap_services`: List available AWS services in the ABAP SDK with optional filtering by name, SDK ID, or TLA
- `get_aws_sdk_for_abap_service_details`: Get service metadata including factory class, client interface, and available operations
- `list_aws_sdk_for_abap_operations`: List operations for a specific service with optional filtering
- `get_aws_sdk_for_abap_operation_details`: Get detailed operation information including ABAP method signature, parameters, and return type
- `get_aws_sdk_for_abap_datatype_details`: Get ABAP structure/type definitions for SDK data types
- `list_aws_sdk_for_abap_examples`: List available code examples for a service or operation
- `get_aws_sdk_for_abap_example_details`: Get detailed ABAP code examples including method signatures and syntax
- `get_aws_sdk_for_abap_usage_create_session`: Generate ABAP code for creating an AWS SDK session with proper exception handling
- `get_aws_sdk_for_abap_usage_create_client`: Generate ABAP code for creating a service client using the factory method
- `get_aws_sdk_for_abap_usage_call_operation`: Generate ABAP code for calling an SDK operation with specified input parameters

## Configuration

You can configure the AWS SDK for SAP ABAP Knowledge MCP server for use with any MCP client that supports Streamable HTTP transport (HTTP) using the following URL:

```
https://sdk-for-sap-abap-knowledge-mcp.global.api.aws
```

> **Note:** The specific configuration format varies by MCP client. Below is an example for Kiro. If you are using a different client, refer to your client's documentation on how to add remote MCP servers using the URL above.

### Kiro

```json
{
  "mcpServers": {
    "aws-sdk-for-sap-abap-knowledge-mcp-server": {
      "url": "https://sdk-for-sap-abap-knowledge-mcp.global.api.aws",
      "type": "http",
      "disabled": false
    }
  }
}
```

If the client you are using does not support HTTP transport for MCP or if it encounters issues during setup, you can use the `fastmcp` utility to proxy from stdio to HTTP transport. Below is a configuration example for the `fastmcp` utility.

### fastmcp

```json
{
  "mcpServers": {
    "aws-sdk-for-sap-abap-knowledge-mcp-server": {
      "command": "uvx",
      "args": ["fastmcp", "run", "https://sdk-for-sap-abap-knowledge-mcp.global.api.aws"]
    }
  }
}
```

## Testing and Troubleshooting

If you want to call the server directly, not through an LLM, you can use the MCP Inspector tool. It provides you with a UI where you can execute `tools/list` and `tools/call` with arbitrary parameters.

```bash
npx @modelcontextprotocol/inspector https://sdk-for-sap-abap-knowledge-mcp.global.api.aws
```

## Relationship to the AWS Knowledge MCP Server

This server complements the [AWS Knowledge MCP Server](../aws-knowledge-mcp-server/) rather than replacing it:

- **AWS Knowledge MCP Server**: General AWS documentation, API references, troubleshooting, architectural guidance across all AWS services and SDKs
- **AWS SDK for SAP ABAP Knowledge MCP Server**: Deep, specialized knowledge about ABAP-specific SDK patterns — class names, method signatures, ABAP data type definitions, and code generation for the ABAP language

Used together, they give ABAP developers both broad AWS knowledge and precise SDK coding assistance.

## AWS Authentication

The AWS SDK for SAP ABAP Knowledge MCP server does not require authentication but is subject to rate limits.

## Data Usage

Telemetry data collected through the AWS SDK for SAP ABAP Knowledge MCP server is not used for machine learning model training or improvement purposes.

## FAQs

### 1. What is the AWS SDK for SAP ABAP Knowledge MCP server?

The AWS SDK for SAP ABAP Knowledge MCP server is a specialized knowledge resource that enables AI coding assistants to generate syntactically correct ABAP code for AWS integrations. It provides authoritative, daily-updated knowledge about the AWS SDK for SAP ABAP to any AI-enabled IDE that supports MCP.

### 2. How do I set up the server?

Paste the server URL (`https://sdk-for-sap-abap-knowledge-mcp.global.api.aws`) into your IDE's MCP configuration. No software installation, dependency management, or authentication is required.

### 3. What AWS services does the server know about?

The server covers the entire AWS SDK for SAP ABAP — over 200 AWS services including Amazon S3, Amazon SQS, Amazon SNS, Amazon Bedrock, Amazon Textract, Amazon Rekognition, AWS Lambda, Amazon DynamoDB, and many more. The knowledge base is updated daily in sync with SDK releases.

### 4. Do I need an AWS account?

No. You can use the server without an AWS account. The server provides knowledge about the SDK — you will need an AWS account and the SDK installed on your SAP system to actually run the generated code.

### 5. How does this server differ from the AWS Knowledge MCP Server?

The AWS Knowledge MCP Server provides general AWS documentation and guidance across all services and SDKs. This server provides deep, specialized knowledge specific to the ABAP SDK — including ABAP class names, method signatures, strict type definitions, and code generation that follows ABAP conventions (8-character parameter limits, factory patterns, exception hierarchies). The two servers work well together.

### 6. Does my code get sent to AWS when using this server?

The server operates as a knowledge resource for your IDE's AI assistant. Your proprietary business logic and application code remain within your development environment. The server only receives queries about AWS SDK usage and responds with relevant syntax, type definitions, and code examples.

