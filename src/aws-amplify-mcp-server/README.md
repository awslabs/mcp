# AWS Amplify MCP Server

A fully managed remote MCP server that provides specialized guidance for building production-ready, full-stack applications using AWS Amplify Gen2. It addresses the challenge where AI tools generate working Amplify applications only 10% of the time due to outdated patterns, Gen1/Gen2 version confusion, and documentation ranking issues.

This MCP server is in general availability.

**Important Note**: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

### Key Features

- Production-ready code generation following Amplify Gen2 best practices
- Latest version enforcement (always uses current Amplify Gen2 and latest library versions)
- Multi-framework support for Web (React, Vue, Angular, Next.js) and Mobile (React Native, Flutter, Swift, Android)
- Complete lifecycle coverage from backend infrastructure to frontend integration to deployment
- Simplified implementations using Amplify abstractions instead of verbose AWS SDK code

### AWS Amplify capabilities

- **Backend Infrastructure**: Step-by-step guidance for implementing authentication (Cognito), data models (GraphQL + DynamoDB), storage (S3), serverless functions (Lambda), and AI features using TypeScript code-first approach
- **Frontend Integration**: Framework-specific instructions for integrating frontend applications with Amplify backend services across all supported platforms
- **Documentation Search**: Quick access to relevant Amplify Gen2 documentation excerpts for specific implementation questions
- **Deployment Workflows**: Instructions for deploying Amplify applications including sandbox vs. production workflows and configuration management

### Tools

1. `get_backend_guidance`: Returns step-by-step instructions for implementing Amplify Gen2 backend infrastructure
2. `get_frontend_guidance`: Returns framework-specific instructions for integrating frontend applications with Amplify backend services
3. `search_documentation`: Searches Amplify Gen2 documentation and returns relevant excerpts with titles, URLs, and content snippets
4. `get_deployment_guidance`: Returns deployment instructions for Amplify applications

### Build full-stack applications with natural language

- Generate backend infrastructure code using Amplify Gen2's TypeScript-first approach
- Get framework-specific frontend integration code for your chosen platform
- Search Amplify documentation for specific implementation patterns
- Learn deployment best practices for sandbox and production environments

## Configuration

You can configure the Amplify MCP server for use with any MCP client that supports Streamable HTTP transport (HTTP) using the following URL:

```url
https://amplify-mcp.global.api.aws
```

**Note:** The specific configuration format varies by MCP client. Below is an example for [Amazon Q CLI](https://github.com/aws/amazon-q-developer-cli). If you are using a different client, refer to your client's documentation on how to add remote MCP servers using the URL above.

**Q-CLI**

```json
{
  "mcpServers": {
    "aws-amplify-mcp-server": {
      "url": "https://amplify-mcp.global.api.aws",
      "type": "http"
    }
  }
}
```

If the client you are using does not support HTTP transport for MCP or if it encounters issues during setup, you can use the [fastmcp](https://github.com/jlowin/fastmcp) utility to proxy from stdio to HTTP transport. Below is a configuration example for the fastmcp utility.

**fastmcp**

```json
{
  "mcpServers": {
    "aws-amplify-mcp-server": {
      "command": "uvx",
      "args": ["fastmcp", "run", "https://amplify-mcp.global.api.aws"]
    }
  }
}
```

### One-Click Installation

|   IDE   |                                                                                                                                                   Install                                                                                                                                                   |
| :-----: | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| Cursor  |                                                [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=aws-amplify-mcp&config=eyJ1cmwiOiJodHRwczovL2FtcGxpZnktbWNwLmdsb2JhbC5hcGkuYXdzIn0=)                                                 |
| VS Code | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=aws-amplify-mcp&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Famplify-mcp.global.api.aws%22%7D) |

### Testing and Troubleshooting

If you want to call the Amplify MCP server directly, not through an LLM, you can use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) tool. It provides you with a UI where you can execute `tools/list` and `tools/call` with arbitrary parameters.
You can use the following command to start MCP Inspector. It will output a URL that you can navigate to in your browser. If you are having trouble connecting to the server, ensure you click on the URL from the terminal because it contains a session token for using MCP Inspector.

```
npx @modelcontextprotocol/inspector https://amplify-mcp.global.api.aws
```

### AWS Authentication

The Amplify MCP server does not require authentication but is subject to rate limits.

### Data Usage

Telemetry data collected through AWS Amplify MCP server is not used for machine learning model training or improvement purposes.

### FAQs

#### 1. What's the difference between Amplify Gen1 and Gen2?

Amplify Gen2 (released May 2024) is the current version that uses a TypeScript-first, code-based approach for defining backend infrastructure. Gen1 (released 2017) used CLI-based configuration. This MCP server exclusively provides Gen2 guidance to ensure you're using current best practices.

#### 2. Which frontend frameworks are supported?

The Amplify MCP server provides guidance for Web frameworks (React, Vue, Angular, Next.js) and Mobile platforms (React Native, Flutter, Swift, Android). Use the `get_frontend_guidance` tool with your specific framework to get tailored integration instructions.

#### 3. Do I need network access to use the AWS Amplify MCP Server?

Yes, you will need to be able to access the public internet to access the AWS Amplify MCP Server.

#### 4. Do I need an AWS account?

No. You can get started with the Amplify MCP server without an AWS account to learn about Amplify patterns and generate code. However, you will need an AWS account to deploy and run Amplify applications. The Amplify MCP is subject to the [AWS Site Terms](https://aws.amazon.com/terms/)

#### 5. Does this server create or modify AWS resources?

No. The Amplify MCP server provides guidance only. It does not create, modify, or manage AWS resources directly. You'll use the generated code and instructions to deploy resources through Amplify's deployment workflows.
