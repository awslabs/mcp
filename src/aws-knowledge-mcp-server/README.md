# AWS Knowledge MCP Server

A fully managed remote MCP server that provides up-to-date documentation, code samples, and other official AWS content.

This MCP server is currently in preview release and is intended for testing and evaluation purposes.

**Important Note**: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

### Key Features
- Real-time access to AWS documentation, API references, and architectural guidance
- Less local setup compared to client-hosted servers
- Structured access to AWS knowledge for AI agents

### AWS Knowledge capabilities
- **Best practices**: Discover best practices around using AWS APIs and services
- **API documentation**: Learn about how to call APIs including required and optional parameters and flags
- **Getting started**: Find out how to quickly get started using AWS services while following best practices
- **The latest information**: Access the latest announcements about new AWS services and features

### Tools
1. `search_documentation`: Search across all AWS documentation
2. `read_documentation`: Retrieve and convert AWS documentation pages to markdown
3. `recommend`: Get content recommendations for AWS documentation pages

### Current knowledge sources
- The latest AWS docs
- API references
- What's New posts
- Getting Started information
- Builder Center
- Blog posts
- Architectural references
- Well-Architected guidance

### FAQs

#### 1. Should I use the local AWS Documentation MCP Server or the remote AWS Knowledge MCP Server?
The Knowledge server indexes a variety of information sources in addition to AWS Documentation including What's New Posts, Getting Started Information, guidance from the Builder Center, Blog posts, Architectural references, and Well-Architected guidance. If your MCP client supports remote servers you can easily try the Knowledge MCP server to see if it suits your needs.

#### 2. Do I need network access to use the AWS Knowledge MCP Server?
Yes, you will need to be able to access the public internet to access the AWS Knowledge MCP Server.

#### 3. Do I need an AWS account?
No. You can get started with the Knowledge MCP server without an AWS account. The Knowledge MCP is subject to the [AWS Site Terms](https://aws.amazon.com/terms/)

### Learn about AWS with natural language

- Ask questions about AWS APIs, best practices, new releases, or architectural guidance
- Get instant answers from multiple sources of AWS information
- Retrieve comprehensive guidance and information

## Prerequisites

You can configure the Knowledge server for use with any MCP client that supports Streamable HTTP transport (HTTP), such as Cursor, using the following configuration:

```json
{
    "mcpServers": {
        "aws-knowledge-mcp-server": {
            "url": "https://knowledge-mcp.global.api.aws"
        }
    }
}
```

If the client you use does not support HTTP transport for MCP or if it encounters issues during setup, we recommend to use either the [mcp-remote](https://github.com/geelen/mcp-remote) or [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy) utility to proxy from stdio to HTTP transport. Clients that fall in this category may include Kiro, Cline, Q CLI and Claude Desktop. Find below configuration examples for both utilities.

**mcp-remote**

```json
{
    "mcpServers": {
        "aws-knowledge-mcp-server": {
            "command": "npx",
            "args": [
                "mcp-remote",
                "https://knowledge-mcp.global.api.aws"
            ]
        }
    }
}
```

**mcp-proxy**

```json
{
    "mcpServers": {
        "aws-knowledge-mcp-server": {
            "command": "uvx",
            "args": [
                "mcp-proxy",
                "--transport",
                "streamablehttp",
                "https://knowledge-mcp.global.api.aws"
            ]
        }
    }
}
```

### Using Cursor

If you use Cursor, you can use the following instructions to get started:

1. Install Cursor: https://cursor.com/home
2. Add AWS MCP Server to Cursor MCP configuration
  - Cursor supports two levels of MCP configuration:
    - Global Configuration: `~/.cursor/mcp.json` - Applies to all workspaces
    - Workspace Configuration: `.cursor/mcp.json` - Specific to the current workspace
    Both files are optional; either, one, or both can exist. Please create a file you want to use if it doesn’t exist.

```json
{
  "mcpServers": {
    "aws-knowledge-mcp-server": {
      "url": "https://knowledge-mcp.global.api.aws"
    }
  }
}
```

### Testing and Troubleshooting
If you want to call the Knowledge MCP server directly, not through an LLM, you can use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) tool. It provides you with a UI where you can execute `tools/list` and `tools/call` with arbitrary parameters.
You can use the following command to start MCP Inspector. It will output a URL that you can navigate to in your browser. If you are having trouble connecting to the server, ensure you click on the URL from the terminal because it contains a session token for using MCP Inspector.

```
npx @modelcontextprotocol/inspector https://knowledge-mcp.global.api.aws
```

### AWS Authentication
The Knowledge MCP server does not require authentication but is subject to rate limits.
