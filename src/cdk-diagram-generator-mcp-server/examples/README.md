# CDK Diagram Generator Examples

This directory contains example CDK code that can be used to test the CDK Diagram Generator MCP server.

## Examples

### simple-example.ts

A TypeScript CDK example that creates a stack with various AWS resources:
- VPC with public and private subnets
- Security groups
- Lambda functions
- DynamoDB table
- S3 bucket
- API Gateway
- IAM roles

### simple-example.py

A Python CDK example that creates the same stack as the TypeScript example.

## Using the Examples

You can use these examples to test the CDK Diagram Generator MCP server without having to install the AWS CDK or any dependencies. The examples are meant to be used as input to the diagram generator, not to be deployed.

### Using with Claude

1. Make sure the CDK Diagram Generator MCP server is installed and running
2. Ask Claude to generate a diagram from one of the examples:

```
Please generate a diagram from the CDK example at /Users/miketran/WebstormProjects/mcp/src/cdk-diagram-generator-mcp-server/examples/simple-example.ts
```

### Using the MCP Tools Directly

You can also use the MCP tools directly to generate diagrams from the examples:

#### Generate diagram from TypeScript example:

```json
{
  "path": "/Users/miketran/WebstormProjects/mcp/src/cdk-diagram-generator-mcp-server/examples",
  "outputPath": "./output/typescript-example.drawio",
  "language": "typescript"
}
```

#### Generate diagram from Python example:

```json
{
  "path": "/Users/miketran/WebstormProjects/mcp/src/cdk-diagram-generator-mcp-server/examples",
  "outputPath": "./output/python-example.drawio",
  "language": "python"
}
```

#### Generate diagram from code:

You can also generate a diagram directly from code by copying the content of one of the example files and using the `generate_diagram_from_code` tool.

## Viewing the Generated Diagrams

The generated diagrams are saved as draw.io XML files. You can open them with:

- [draw.io](https://app.diagrams.net/) (online or desktop app)
- [diagrams.net](https://www.diagrams.net/) (same as draw.io)
- VS Code with the Draw.io Integration extension

## Customizing the Examples

Feel free to modify these examples to test different AWS resources and relationships. The CDK Diagram Generator supports a wide range of AWS services and will automatically detect relationships between resources.
