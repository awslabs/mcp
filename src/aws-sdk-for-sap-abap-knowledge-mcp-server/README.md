# AWS SDK for SAP ABAP Knowledge MCP Server

A fully managed remote MCP server that provides AI coding assistants with specialized knowledge about the [AWS SDK for SAP ABAP](https://aws.amazon.com/sdk-for-sap-abap/), enabling them to generate accurate ABAP code for AWS service integrations.

The MCP server uses the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction), an open standard for connecting AI assistants to external knowledge sources. The server is updated daily in sync with AWS SDK for SAP ABAP releases, so your IDE always has access to current, accurate SDK information.

The AWS SDK for SAP ABAP Knowledge MCP Server is available at no additional cost. You only pay for the AWS resources and services that you consume in your SAP applications with the ABAP SDK.

> **Important Note:** Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

## Key Features

- **Accurate code generation**: Your AI coding assistant gains deep knowledge of ABAP-specific patterns, method signatures, data types, and exception handling. This eliminates common errors and significantly reduces compilation errors and debugging time.
- **Instant SDK discovery**: The MCP server exposes the complete AWS SDK for SAP ABAP knowledge base, covering 200+ AWS services. You can discover available services, operations, and data types without manually searching documentation.
- **Always up to date**: The knowledge base is updated daily in sync with SDK releases. New services and updated method signatures are immediately available to your IDE.
- **Zero installation**: Setup requires only pasting a URL into your IDE's MCP configuration. No local software installation, no dependency management, and no IT approval process is required.

## Supported IDEs

The AWS SDK for SAP ABAP Knowledge MCP Server works with any AI-enabled IDE that supports the Model Context Protocol (MCP). Supported IDEs include:

- [Kiro](https://kiro.dev/)
- Amazon Q for Eclipse
- Any other MCP-compatible IDE or AI assistant

## What the MCP server can do

Once connected, your AI coding assistant can use the following capabilities:

- **Service discovery**: List and search all AWS services available in the AWS SDK for SAP ABAP, including service metadata and factory class names.
- **Operation details**: Retrieve ABAP method signatures, input parameters, return types, and exception types for any SDK operation.
- **Data type definitions**: Look up ABAP structure definitions for SDK data types, including field names and types that respect ABAP's 8-character naming limit.
- **Code examples**: Retrieve working ABAP code examples for specific operations, covering common use cases for each service.
- **Session and client creation**: Generate boilerplate ABAP code for creating SDK sessions, initializing service clients, and calling operations with correct exception handling.

For example, you can prompt your AI assistant with requests such as:

- "Write ABAP code to read a message from an SQS queue."
- "Generate ABAP code to invoke an Amazon Bedrock model for text generation."
- "Show me how to upload a file to Amazon S3 from ABAP."

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
https://sdk-for-sap-abap-knowledge-mcp.global.api.aws/mcp
```

> **Note:** The specific configuration format varies by MCP client. Below is an example for Kiro. If you are using a different client, refer to your client's documentation on how to add remote MCP servers using the URL above.

### Kiro

```json
{
  "mcpServers": {
    "abap-sdk-knowledge": {
      "url": "https://sdk-for-sap-abap-knowledge-mcp.global.api.aws/mcp",
      "disabled": false,
      "autoApprove": ["*"]
    }
  }
}
```

The `autoApprove` setting allows your IDE to use the MCP server's tools without prompting for approval on each request. This is safe because the MCP server is read-only and does not modify any data or execute code.

If the client you are using does not support HTTP transport for MCP or if it encounters issues during setup, you can use the `fastmcp` utility to proxy from stdio to HTTP transport. Below is a configuration example for the `fastmcp` utility.

### fastmcp

```json
{
  "mcpServers": {
    "abap-sdk-knowledge": {
      "command": "uvx",
      "args": ["fastmcp", "run", "https://sdk-for-sap-abap-knowledge-mcp.global.api.aws/mcp"]
    }
  }
}
```

## Testing and Troubleshooting

If you want to call the server directly, not through an LLM, you can use the MCP Inspector tool. It provides you with a UI where you can execute `tools/list` and `tools/call` with arbitrary parameters.

```bash
npx @modelcontextprotocol/inspector https://sdk-for-sap-abap-knowledge-mcp.global.api.aws/mcp
```

After saving the configuration, your IDE will connect to the MCP server automatically. No restart is required in most IDEs. You can verify the connection by asking your AI assistant a question about the AWS SDK for SAP ABAP, such as "What AWS services are available in the AWS SDK for SAP ABAP?"

If your IDE does not connect to the MCP server, verify that your IDE supports the Model Context Protocol and that the configuration file syntax matches your IDE's requirements.

## Relationship to the AWS Knowledge MCP Server

This server complements the [AWS Knowledge MCP Server](../aws-knowledge-mcp-server/) rather than replacing it:

- **AWS Knowledge MCP Server**: General AWS documentation, API references, troubleshooting, architectural guidance across all AWS services and SDKs
- **AWS SDK for SAP ABAP Knowledge MCP Server**: Deep, specialized knowledge about ABAP-specific SDK patterns - class names, method signatures, ABAP data type definitions, and code generation for the ABAP language

Used together, they give ABAP developers both broad AWS knowledge and precise SDK coding assistance. You can also configure the [AWS Knowledge MCP Server](../aws-knowledge-mcp-server/) for general AWS service information, architectural guidance, and troubleshooting. The two servers are especially effective together for developers who are new to AWS.

## AWS Authentication

The MCP server endpoint uses HTTPS and does not require authentication. Your IDE communicates with the server only when you ask your AI assistant questions related to AWS SDK for SAP ABAP usage. Your proprietary business logic and SAP application code remain within your development environment.

## Important considerations

- The MCP server provides read-only access to SDK knowledge. It does not execute ABAP code or connect to SAP systems.
- The MCP server covers only the AWS SDK for SAP ABAP. It does not provide general ABAP programming assistance unrelated to AWS SDK for SAP ABAP usage.
- The MCP server does not support custom or third-party ABAP libraries.
- Generated code examples are starting points. Review and test all generated code before using it in production.
- The quality and format of generated code may vary depending on your IDE's AI assistant capabilities.

## FAQs

### 1. What is the AWS SDK for SAP ABAP Knowledge MCP server?

The AWS SDK for SAP ABAP Knowledge MCP server is a specialized knowledge resource that enables AI coding assistants to generate accurate ABAP code for AWS integrations. It provides authoritative, daily-updated knowledge about the AWS SDK for SAP ABAP to any AI-enabled IDE that supports MCP.

### 2. How do I set up the server?

Paste the server URL (`https://sdk-for-sap-abap-knowledge-mcp.global.api.aws/mcp`) into your IDE's MCP configuration. No software installation, dependency management, or authentication is required.

### 3. What AWS services does the server know about?

The server covers the entire AWS SDK for SAP ABAP - over 200 AWS services including Amazon S3, Amazon SQS, Amazon SNS, Amazon Bedrock, Amazon Textract, Amazon Rekognition, AWS Lambda, Amazon DynamoDB, and many more. The knowledge base is updated daily in sync with SDK releases.

### 4. Do I need an AWS account?

No. You can use the server without an AWS account. The server provides knowledge about the SDK - you will need an AWS account and the SDK installed on your SAP system to actually run the generated code.

### 5. How does this server differ from the AWS Knowledge MCP Server?

The AWS Knowledge MCP Server provides general AWS documentation and guidance across all services and SDKs. This server provides deep, specialized knowledge specific to the ABAP SDK - including ABAP class names, method signatures, strict type definitions, and code generation that follows ABAP conventions (8-character parameter limits, factory patterns, exception hierarchies). The two servers work well together.

### 6. Does my code get sent to AWS when using this server?

The MCP server endpoint uses HTTPS and does not require authentication. Your IDE communicates with the server only when you ask your AI assistant questions related to AWS SDK for SAP ABAP usage. Your proprietary business logic and SAP application code remain within your development environment. The server only receives queries about AWS SDK usage and responds with relevant syntax, type definitions, and code examples.

