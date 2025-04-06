# CDK Diagram Generator MCP Server

An MCP server for generating architectural diagrams from AWS CDK code, supporting both TypeScript and Python CDK projects.

## Overview

The CDK Diagram Generator MCP server analyzes AWS CDK code (TypeScript or Python) and generates architectural diagrams in draw.io format. It can extract AWS resources and their relationships from CDK constructs, making it easy to visualize your cloud infrastructure.

## Features

- Generate draw.io compatible XML diagrams from CDK code
- Support for both TypeScript and Python CDK projects
- Automatic detection of AWS resources and their relationships
- Proper representation of VPCs as containers for resources
- Support for a wide range of AWS services
- Smart layout algorithm for better readability

## Prerequisites

- Node.js 18 or later
- npm or yarn

## Installation

### Quick Install

Run the installation script:

```bash
./install.sh
```

This will:
1. Install dependencies
2. Build the project
3. Create a configuration file for MCP

### Manual Installation

1. Install dependencies:

```bash
npm install
```

2. Build the project:

```bash
npm run build
```

3. Create the output directory:

```bash
mkdir -p output
```

## Configuration

### MCP Configuration

To use this server with MCP, add it to your MCP configuration:

#### For Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cdk-diagram-generator": {
      "command": "node",
      "args": ["/path/to/cdk-diagram-generator-mcp-server/build/index.js"],
      "env": {
        "CDK_DIAGRAM_OUTPUT_DIR": "/path/to/cdk-diagram-generator-mcp-server/output"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

#### For Claude VSCode Extension

Edit `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "cdk-diagram-generator": {
      "command": "node",
      "args": ["/path/to/cdk-diagram-generator-mcp-server/build/index.js"],
      "env": {
        "CDK_DIAGRAM_OUTPUT_DIR": "/path/to/cdk-diagram-generator-mcp-server/output"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Environment Variables

The server can be configured through environment variables:

- `CDK_DIAGRAM_OUTPUT_DIR`: Directory where generated diagrams will be saved (default: `./output`)

## Usage

### Using with Claude

Once the server is configured, you can ask Claude to generate diagrams from CDK code:

```
Please generate a diagram from my CDK project at /path/to/cdk/project
```

Or directly from code:

```
Please generate a diagram from this CDK code:

const app = new cdk.App();
const stack = new cdk.Stack(app, 'MyStack');
const vpc = new ec2.Vpc(stack, 'MyVpc');
```

### Using the MCP Tools Directly

#### Generate diagram from a CDK project directory:

```json
{
  "path": "/path/to/cdk/project",
  "outputPath": "./output/my-diagram.drawio",
  "language": "typescript"
}
```

#### Generate diagram from CDK code:

```json
{
  "code": "const app = new cdk.App();\nconst stack = new cdk.Stack(app, 'MyStack');\nconst vpc = new ec2.Vpc(stack, 'MyVpc');",
  "outputPath": "./output/my-diagram.drawio",
  "language": "typescript"
}
```

## Examples

Check out the [examples](./examples) directory for sample CDK code that you can use to test the diagram generator.

## Supported AWS Resources

The server supports a wide range of AWS resources, including:

- **EC2 and Networking**: VPC, Subnet, Security Group, Instance, NAT Gateway, Internet Gateway, Route Table
- **Lambda**: Function, Layer Version, Event Source Mapping
- **API Gateway**: REST API, Resource, Method, Deployment, Stage, HTTP API, Route, Integration
- **DynamoDB**: Table, Global Table
- **S3**: Bucket, Bucket Policy
- **CloudFront**: Distribution, Origin Access Identity
- **Step Functions**: State Machine, Activity
- **SNS**: Topic, Subscription
- **SQS**: Queue, Queue Policy
- **Cognito**: User Pool, User Pool Client, Identity Pool
- **RDS**: DB Instance, DB Cluster
- **ElastiCache**: Cache Cluster, Replication Group
- **IAM**: Role, Policy, Managed Policy
- **EventBridge**: Rule

## Development

### Project Structure

```
cdk-diagram-generator-mcp-server/
├── src/
│   ├── index.ts                # Main entry point
│   ├── parsers/                # CDK code parsers
│   │   ├── typescript-parser.ts # TypeScript CDK parser
│   │   └── python-parser.ts    # Python CDK parser
│   ├── models/                 # Data models
│   │   └── infrastructure.ts   # Infrastructure model
│   └── generators/             # Diagram generators
│       └── drawio-generator.ts # draw.io XML generator
├── examples/                   # Example CDK code
├── output/                     # Generated diagrams
├── scripts/                    # Build scripts
└── build/                      # Compiled JavaScript
```

### Building

```bash
npm run build
```

### Testing

The project includes a comprehensive test suite that tests all components of the system:

```bash
# Run all tests
npm test

# Run individual test suites
npm run test:typescript-parser   # Test TypeScript CDK parser
npm run test:python-parser       # Test Python CDK parser
npm run test:drawio-generator    # Test draw.io diagram generator
npm run test:mcp-server          # Test MCP server interface

# Run comprehensive tests
npm run test:comprehensive       # Run all comprehensive tests

# Run legacy simple tests
npm run test:simple              # ES module version
npm run test:simple:cjs          # CommonJS version
```

The test suite includes:

- **Basic Tests**: Simple tests that verify the basic functionality of each component.
  - **Parser Tests**: Tests for both TypeScript and Python CDK parsers, ensuring they correctly extract resources, connections, and VPCs from CDK code.
  - **Generator Tests**: Tests for the draw.io diagram generator, ensuring it correctly generates diagrams from infrastructure models.
  - **MCP Server Tests**: Tests for the MCP server interface, ensuring it correctly handles requests and generates diagrams.

- **Comprehensive Tests**: More thorough tests that cover edge cases and additional functionality.
  - **Parser Comprehensive Tests**: Tests that verify the parsers can handle complex CDK code with various AWS resources and relationships.
  - **Generator Comprehensive Tests**: Tests that verify the generator can create complex diagrams with many resources and connections.
  - **MCP Server Comprehensive Tests**: Tests that verify the server can handle various requests and edge cases.

- **Error Handling Tests**: Tests for error handling in all components, ensuring the server gracefully handles invalid inputs.

For more information about the tests, see the [tests/README.md](./tests/README.md) file.

### Running Locally

```bash
node build/index.js
```

## License

This project is licensed under the MIT License.
