# AWS Knowledge MCP Server

A fully managed remote MCP server that provides up-to-date documentation, code samples, knowledge about the regional availability of AWS APIs and CloudFormation resources, and other official AWS content.

This MCP server is in general availability.

**Important Note**: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

### Key Features

- Real-time access to AWS documentation, API references, and architectural guidance
- Less local setup compared to client-hosted servers
- Structured access to AWS knowledge for AI agents
- Regional availability information for AWS APIs and CloudFormation resources

### AWS Knowledge capabilities

- **Best practices**: Discover best practices around using AWS APIs and services
- **API documentation**: Learn about how to call APIs including required and optional parameters and flags
- **Getting started**: Find out how to quickly get started using AWS services while following best practices
- **The latest information**: Access the latest announcements about new AWS services and features

### Tools

1. `search_documentation`: Search across all AWS documentation
2. `read_documentation`: Retrieve and convert AWS documentation pages to markdown
3. `recommend`: Get content recommendations for AWS documentation pages
4. `list_regions` _(Experimental)_: Retrieve a list of all AWS regions, including their identifiers and names
5. `get_regional_availability`_(Experimental)_: Retrieve AWS regional availability information for SDK service APIs and CloudFormation resources

### Current knowledge sources

- The latest AWS docs
- API references
- What's New posts
- Getting Started information
- Builder Center
- Blog posts
- Architectural references
- Well-Architected guidance

### Learn about AWS with natural language

- Ask questions about AWS APIs, best practices, new releases, or architectural guidance
- Get instant answers from multiple sources of AWS information
- Retrieve comprehensive guidance and information

## Configuration

You can configure the Knowledge MCP server for use with any MCP client that supports Streamable HTTP transport (HTTP) using the following URL:

```url
https://knowledge-mcp.global.api.aws
```

**Note:** The specific configuration format varies by MCP client. Below is an example for [Amazon Q CLI](https://github.com/aws/amazon-q-developer-cli). If you are using a different client, refer to your client's documentation on how to add remote MCP servers using the URL above.

**Q-CLI**

```json
{
  "mcpServers": {
    "aws-knowledge-mcp-server": {
      "url": "https://knowledge-mcp.global.api.aws",
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
    "aws-knowledge-mcp-server": {
      "command": "uvx",
      "args": ["fastmcp", "run", "https://knowledge-mcp.global.api.aws"]
    }
  }
}
```

### One-Click Installation

|   IDE   |                                                                                                                                                   Install                                                                                                                                                   |
| :-----: | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| Cursor  |                                                [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=aws-knowledge-mcp&config=eyJ1cmwiOiJodHRwczovL2tub3dsZWRnZS1tY3AuZ2xvYmFsLmFwaS5hd3MifQ==)                                                 |
| VS Code | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=aws-knowledge-mcp&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fknowledge-mcp.global.api.aws%22%7D) |

### MCP Registries

The AWS Knowledge MCP Server is available in the following official MCP registries:

- [Smithery](https://smithery.ai/server/@FaresYoussef94/aws-knowledge-mcp)
- [Cursor](https://cursor.directory/mcp/aws-knowledge-mcp-1)

We are actively working on onboarding to additional registries to make installation even easier.

### Testing and Troubleshooting

If you want to call the Knowledge MCP server directly, not through an LLM, you can use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) tool. It provides you with a UI where you can execute `tools/list` and `tools/call` with arbitrary parameters.
You can use the following command to start MCP Inspector. It will output a URL that you can navigate to in your browser. If you are having trouble connecting to the server, ensure you click on the URL from the terminal because it contains a session token for using MCP Inspector.

```
npx @modelcontextprotocol/inspector https://knowledge-mcp.global.api.aws
```

### AWS Authentication

The Knowledge MCP server does not require authentication but is subject to rate limits.

### Data Usage

Telemetry data collected through AWS Knowledge MCP server is not used for machine learning model training or improvement purposes.

### FAQs

#### 1. Should I use the local AWS Documentation MCP Server or the remote AWS Knowledge MCP Server?

The Knowledge server indexes a variety of information sources in addition to AWS Documentation including What's New Posts, Getting Started Information, guidance from the Builder Center, Blog posts, Architectural references, and Well-Architected guidance. If your MCP client supports remote servers you can easily try the Knowledge MCP server to see if it suits your needs.

#### 2. Do I need network access to use the AWS Knowledge MCP Server?

Yes, you will need to be able to access the public internet to access the AWS Knowledge MCP Server.

#### 3. Do I need an AWS account?

No. You can get started with the Knowledge MCP server without an AWS account. The Knowledge MCP is subject to the [AWS Site Terms](https://aws.amazon.com/terms/)
