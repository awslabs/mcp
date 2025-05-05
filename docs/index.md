# Welcome to AWS MCP Servers

A suite of specialized MCP servers that help you get the most out of AWS, wherever you use MCP.

## Available MCP Servers

### Core MCP Server

The Core MCP Server manages and coordinates other MCP servers in your environment, providing automatic installation, configuration, and management.

**Features:**

- Automatic MCP Server Management
- Planning and guidance to orchestrate MCP Servers
- UVX Installation Support
- Centralized Configuration

[Learn more about the Core MCP Server](servers/core-mcp-server.md)

### AWS Documentation MCP Server

The AWS Documentation MCP Server provides access to AWS documentation and best practices.

**Features:**

- Search Documentation using the official AWS search API
- Get content recommendations for AWS documentation pages
- Convert documentation to markdown format

[Learn more about the AWS Documentation MCP Server](servers/aws-documentation-mcp-server.md)

### AWS CDK MCP Server

The CDK MCP Server provides AWS Cloud Development Kit (CDK) best practices, infrastructure as code patterns, and security compliance with CDK Nag.

**Features:**

- CDK Best Practices
- CDK Nag Integration
- AWS Solutions Constructs
- GenAI CDK Constructs

[Learn more about the CDK MCP Server](servers/cdk-mcp-server.md)

### Amazon Nova Canvas MCP Server

The Nova Canvas MCP Server enables AI assistants to generate images using Amazon Nova Canvas.

**Features:**

- Text-based image generation
- Color-guided image generation
- Workspace integration

[Learn more about the Nova Canvas MCP Server](servers/nova-canvas-mcp-server.md)

### Amazon Bedrock Knowledge Base Retrieval MCP Server

The Bedrock Knowledge Base Retrieval MCP Server enables AI assistants to retrieve information from Amazon Bedrock Knowledge Bases.

**Features:**

- Discover knowledge bases and their data sources
- Query knowledge bases with natural language
- Filter results by data source
- Rerank results

[Learn more about the Bedrock Knowledge Base Retrieval MCP Server](servers/bedrock-kb-retrieval-mcp-server.md)

### Cost Analysis MCP Server

The Cost Analysis MCP Server enables AI assistants to analyze the cost of AWS services.

**Features:**

- Analyze and predict AWS costs before deployment
- Query cost data with natural language
- Generate cost reports and insights

[Learn more about the Cost Analysis MCP Server](servers/cost-analysis-mcp-server.md)

### AWS Lambda MCP Server

The AWS Lambda MCP Server enables AI assistants to select and run AWS Lambda functions as MCP tools.

**Features:**

- Select and run AWS Lambda functions as MCP tools
- Tool names and descriptions are taken from the AWS Lambda function configuration
- Filter functions by name, tag, or both
- Use AWS credentials to invoke the Lambda functions

[Learn more about the AWS Lambda MCP Server](servers/lambda-mcp-server.md)


### AWS Diagram MCP Server

This MCP server that seamlessly creates [diagrams](https://diagrams.mingrammer.com/) using the Python diagrams package DSL. This server allows you to generate AWS diagrams, sequence diagrams, flow diagrams, and class diagrams using Python code.

**Features:**

The Diagrams MCP Server provides the following capabilities:

1. **Generate Diagrams**: Create professional diagrams using Python code
2. **Multiple Diagram Types**: Support for AWS architecture, sequence diagrams, flow charts, class diagrams, and more
3. **Customization**: Customize diagram appearance, layout, and styling
4. **Security**: Code scanning to ensure secure diagram generation

[Learn more about the AWS Diagram MCP Server](servers/aws-diagram-mcp-server.md)

### AWS Terraform MCP Server

The Terraform MCP Server enables AWS best practices, infrastructure as code patterns, and security compliance with Checkov.

**Features:**

The Terraform MCP Server provides the following capabilities:

- Terraform Best Practices
- Security-First Development Workflow
- Checkov Integration
- AWS and AWSCC Provider Documentation
- AWS-IA GenAI Modules
- Terraform Workflow Execution

[Learn more about the AWS Terraform MCP Server](servers/terraform-mcp-server.md)

### Valkey MCP Server

The Valkey MCP Server provides a natural language interface to interact with Valkey datastores, enabling AI assistants to work with various data structures and perform complex data operations.

**Features:**

- Support for multiple data types (Strings, Lists, Sets, Sorted Sets, Hashes, Streams, etc.)
- Advanced features like server-side scripting and cluster support
- Geospatial operations and bitmap manipulations
- JSON document storage and querying
- Real-time pub/sub messaging capabilities
- Secure connections with SSL/TLS support
- Connection pooling for efficient resource management

[Learn more about the Valkey MCP Server](servers/valkey-mcp-server.md)

## Installation and Setup

Please refer to the README files in each server's directory for specific installation instructions.

## Samples

Please refer to the [samples](samples/index.md) directory for examples of how to use the MCP Servers.

## Contributing

Contributions are welcome! Please see the [contributing guidelines](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) for more information.

## Disclaimer

Before using an MCP Server, you should consider conducting your own independent assessment to ensure that your use would comply with your own specific security and quality control practices and standards, as well as the laws, rules, and regulations that govern you and your content.
