# AWS Knowledge MCP Server

A remote MCP server providing access to the latest AWS docs, API references, What's New Posts, Getting Started information, Builder Center, Blog posts, Architectural references, and Well-Architected guidance. 

**Important Note**: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server. 

## Features

### AWS Knowledge
- **Best practices**: Discover best practices around using AWS APIs and services
- **API documetnation**: Learn about how to call APIs including required and optional parameters and flags 
- **Getting started**: Find out how to quickly get started using AWS services while following best practices
- **The latest information**: Access the latest announcements about new AWS services and features 

### FAQs
#### Should I use the local AWS Documentation MCP Server or the remote AWS Knowledge MCP Server? 

The Knowledge server indexes a wider variety of infomration beyond documentation including What's New Posts, Getting Started Information, guidance from the Builder Center, Blog posts, Architectural references, and Well-Architected guidance. If your MCP client supports remote servers you can easily try the Knowledge MCP server to see if it suits your needs. 

#### Do I need network access to use the AWS Knowledge MCP Server? 
Yes, you'll need to be able to access the public internet to access the AWS Knowledge MCP Server. 

### Learn about AWS with natural language

- Ask questions about AWS APIs, best practices, new releases, or architectural guidance 
- Get instant answers from multiple sources of AWS information 
- Retrieve comprehensive guidnace and information  

## Prerequisites

### Using Cursor
1. Install Cursor: https://cursor.com/home
2. Add AWS MCP Server to Cursort MCP configuration
  - Cursor supports two levels of MCP configuratin:
    - Global Configuration: `~/.cursor/mcp.json` - Applies to all workspaces
    - Workspace Configuration: `.cursor/mcp.json` - Specific to the current workspace
    Both files are optional; neither, one, or both can exist. Please create a file you want to use if it doesn’t exist.

```json
# Configure AWS MCP:
{
  "mcpServers": {
    "aws-knowledge-mcp": {
      "url": "https://awsdocumentationmcpalphagateway-gh6onmmp4q.gateway.gamma.us-east-1.genesis-primitives.aws.dev/mcp"
    }
  }
}
```

###  Using Claude Code (Free tier not available)
1. Install Claude Code (requires nodejs 18+)
  - `npm install -g @anthropic-ai/claude-code`
2. Add AWS MCP Server to Claude Code
  - `claude mcp add --transport http aws-knowledge-mcp https://awsdocumentationmcpalphagateway-gh6onmmp4q.gateway.gamma.us-east-1.genesis-primitives.aws.dev/mcp`
3. Start claude code and chat with claude about your AWS account
  - `claude`
4. Verify that the MCP server is connected
  - `/mcp`
5. You should see `aws-knowledge-mcp` in the list and its connection status


### AWS Authentication

The Knowledge MCP server does not require authentication but is subject to rate limits

### Terms and Conditions  