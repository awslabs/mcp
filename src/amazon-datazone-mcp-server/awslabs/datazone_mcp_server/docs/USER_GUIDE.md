# AWS DataZone MCP Server User Guide

Get started using the AWS DataZone MCP server to manage your AWS DataZone resources through MCP-compatible clients like Claude for Desktop.

## What we'll be building

Many data teams need to manage AWS DataZone resources - domains, projects, assets, glossaries, and environments - but switching between AWS Console, CLI, and various SDKs can be cumbersome. Let's use MCP to solve that!

This server exposes **25+ tools** for comprehensive AWS DataZone management:
- **Domain Management**: Get domains, create domain units, manage permissions
- **Project Management**: Create projects, manage memberships, configure profiles
- **Data Management**: Create assets, publish to catalog, manage subscriptions
- **Glossary Management**: Create glossaries and terms for data governance
- **Environment Management**: List environments, create connections

Then we'll connect the server to an MCP host (in this case, Claude for Desktop):

> **Why Claude for Desktop and not Claude.ai?**
> Because servers run locally, MCP currently only supports desktop hosts. Remote hosts are in active development.

## Core MCP Concepts

MCP servers can provide three main types of capabilities:

1. **Resources**: File-like data that can be read by clients (like API responses or file contents)
2. **Tools**: Functions that can be called by the LLM (with user approval) ← **This is our focus**
3. **Prompts**: Pre-written templates that help users accomplish specific tasks

The AWS DataZone MCP server primarily focuses on **tools** that wrap AWS DataZone API operations.

## Prerequisites

### Knowledge Requirements
- Familiarity with AWS DataZone concepts (domains, projects, assets)
- Basic understanding of AWS IAM and permissions
- Some experience with LLMs like Claude

### System Requirements
- Python 3.10 or higher
- AWS credentials configured (AWS CLI, environment variables, or IAM roles)
- Existing AWS DataZone domain (required for most operations)

## Set up your environment

### 1. Install the AWS DataZone MCP Server

```bash
# Install via pip
pip install datazone-mcp-server

# Or install from source
git clone https://github.com/wangtianren/datazone-mcp-server.git
cd datazone-mcp-server
pip install -e .
```

### 2. Configure AWS Credentials

The server requires AWS credentials with DataZone permissions:

**Option A: AWS CLI**
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: IAM Roles** (recommended for EC2/Lambda)
Ensure your instance has an IAM role with DataZone permissions.

### 3. Set DataZone Domain (Optional)

For convenience, set your default DataZone domain:
```bash
export DATAZONE_DOMAIN_ID=dzd_your_domain_id
```

### 4. Verify Setup

Test that everything is working:
```bash
# Run the server in test mode
python -m datazone_mcp_server.server --help

# Or test a simple connection
python -c "
import asyncio
from mcp import create_client

async def test():
    client = await create_client('stdio', ['python', '-m', 'datazone_mcp_server.server'])
    tools = await client.list_tools()
    print(f'Found {len(tools.tools)} tools')

asyncio.run(test())
"
```

## Available Tools

The AWS DataZone MCP server provides **25+ tools** organized into 5 categories:

### Domain Management Tools
- `get_domain` - Retrieve domain information
- `create_domain` - Create a new DataZone domain
- `list_domain_units` - List organizational units
- `create_domain_unit` - Create domain organizational units
- `get_domain_unit` - Get domain unit details
- `update_domain_unit` - Update domain unit properties
- `add_entity_owner` - Add ownership to entities
- `add_policy_grant` - Grant permissions via policies
- `list_policy_grants` - List existing policy grants
- `remove_policy_grant` - Remove policy grants
- `search` - Search across DataZone entities

### Project Management Tools
- `create_project` - Create new projects
- `get_project` - Get project details
- `list_projects` - List projects in domain
- `create_project_membership` - Add members to projects
- `list_project_profiles` - List project profiles
- `create_project_profile` - Create project profiles

### Data Management Tools
- `get_asset` - Retrieve asset information
- `create_asset` - Create new data assets
- `publish_asset` - Publish assets to catalog
- `get_listing` - Get asset listings
- `search_listings` - Search published assets
- `create_data_source` - Create data sources
- `get_data_source` - Get data source details
- `start_data_source_run` - Trigger data source runs
- `create_subscription_request` - Request asset access
- `accept_subscription_request` - Approve access requests
- `get_subscription` - Get subscription details
- `get_form_type` - Get metadata form types
- `list_form_types` - List available form types
- `create_form_type` - Create custom form types

### Glossary Management Tools
- `create_glossary` - Create business glossaries
- `get_glossary` - Get glossary details
- `create_glossary_term` - Create glossary terms
- `get_glossary_term` - Get term definitions

### Environment Management Tools
- `list_environments` - List project environments
- `create_connection` - Create external connections
- `get_connection` - Get connection details
- `list_connections` - List available connections

## Testing with Claude for Desktop

First, make sure you have [Claude for Desktop installed](https://claude.ai/download). **Make sure it's updated to the latest version.**

### Configure Claude for Desktop

Open your Claude for Desktop configuration file:

**macOS/Linux:**
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
code $env:AppData\Claude\claude_desktop_config.json
```

Add the DataZone MCP server to your configuration:

```json
{
    "mcpServers": {
        "datazone": {
            "command": "python",
            "args": [
                "-m",
                "datazone_mcp_server.server"
            ],
            "env": {
                "DATAZONE_DOMAIN_ID": "dzd_your_domain_id",
                "AWS_DEFAULT_REGION": "us-east-1"
            }
        }
    }
}
```

Save the file and **restart Claude for Desktop completely**.

### Verify Integration

Look for the "Search and tools"  icon in Claude for Desktop. After clicking it, you should see the DataZone tools listed:

- **25+ tools** should be available
- Each tool should have clear descriptions
- Tools should be organized by category

## Usage Examples

Once connected, you can use natural language to interact with your DataZone resources:

### Domain Operations
```
"What domains do I have access to?"
"Get details for domain dzd_abc123"
"Create a domain unit called 'Data Engineering' under the root unit"
```

### Project Management
```
"List all projects in my domain"
"Create a new project called 'Customer Analytics' in domain dzd_abc123"
"Add user john.doe@company.com to project prj_123456"
```

### Data Asset Management
```
"What data assets are available in project prj_123456?"
"Create a new table asset called 'customer_data' in project prj_123456"
"Publish asset ast_789012 to the data catalog"
"Search for assets related to 'customer'"
```

### Glossary Management
```
"Create a glossary called 'Business Terms' in project prj_123456"
"Add a glossary term 'Customer LTV' with definition 'Customer Lifetime Value'"
"What glossary terms are defined for project prj_123456?"
```

### Environment & Connections
```
"List environments in project prj_123456"
"Create a connection to our data warehouse in environment env_789012"
"What connections are available in project prj_123456?"
```

## What's happening under the hood

When you ask a question:

1. **Claude analyzes** your request and available DataZone tools
2. **Claude selects** the appropriate tool(s) to use
3. **MCP client executes** the chosen tool(s) through our server
4. **Our server calls** the AWS DataZone API with your credentials
5. **Results are returned** to Claude via MCP protocol
6. **Claude formulates** a natural language response with the data
7. **Response is displayed** to you in a user-friendly format

## Troubleshooting

### Claude for Desktop Integration Issues

**Getting logs from Claude for Desktop**

Claude.app logging related to MCP is written to log files:

**macOS:**
```bash
# Check Claude's logs for errors
tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
```

**Windows:**
```powershell
# Check Claude's logs
Get-Content -Tail 20 -Wait "$env:AppData\Claude\Logs\mcp*.log"
```

**Server not showing up in Claude**

1. Check your `claude_desktop_config.json` file syntax
2. Verify the Python environment can run the server
3. Test the server independently: `python -m datazone_mcp_server.server`
4. Restart Claude for Desktop completely

**Common Configuration Issues**

**Issue: "ImportError: attempted relative import with no known parent package"**

This happens when the server is run directly as `server.py` instead of as a module.

**Correct configuration:**
```json
{
    "mcpServers": {
        "datazone": {
            "command": "/path/to/uv",
            "args": [
                "--directory",
                "/path/to/datazone-mcp-server",
                "run",
                "python",
                "-m",
                "datazone_mcp_server.server"
            ]
        }
    }
}
```

**Incorrect configuration:**
```json
{
    "mcpServers": {
        "datazone": {
            "command": "/path/to/uv",
            "args": [
                "--directory",
                "/path/to/datazone-mcp-server/src/datazone_mcp_server/",
                "run",
                "server.py"
            ]
        }
    }
}
```

**Issue: Server starts but tools fail silently**

This is often due to missing environment variables or incorrect working directory.

**Add environment variables:**
```json
{
    "mcpServers": {
        "datazone": {
            "command": "/path/to/uv",
            "args": ["--directory", "/path/to/datazone-mcp-server", "run", "python", "-m", "datazone_mcp_server.server"],
            "env": {
                "AWS_DEFAULT_REGION": "us-east-1",
                "AWS_REGION": "us-east-1",
                "DATAZONE_DOMAIN_ID": "dzd_your_domain_id"
            }
        }
    }
}
```

**Issue: "Server not found" with uv installation**

If you have uv installed via different methods, the path may vary:

```bash
# Check where uv is installed
which uv

# Common locations:
# Homebrew: /opt/homebrew/bin/uv
# User install: /Users/username/.local/bin/uv
# System install: /usr/local/bin/uv
```

Use the actual path returned by `which uv` in your configuration.

**Tool calls failing silently**

If Claude attempts to use tools but they fail:

1. Check Claude's logs for errors
2. Verify AWS credentials are configured correctly
3. Test AWS DataZone access: `aws datazone list-domains`
4. Check your IAM permissions for DataZone operations

### AWS DataZone Issues

**Error: "NoCredentialsError"**

Your AWS credentials aren't configured properly:

```bash
# Verify credentials
aws sts get-caller-identity

# If this fails, reconfigure:
aws configure
```

**Error: "AccessDeniedException"**

You don't have sufficient DataZone permissions:

1. Verify your IAM user/role has DataZone permissions
2. Check you're in the correct AWS region
3. Ensure the DataZone domain exists and you have access

**Error: "ResourceNotFoundException"**

The specified resource (domain, project, asset) doesn't exist:

1. Verify your `DATAZONE_DOMAIN_ID` is correct
2. Check the resource exists in the AWS Console
3. Ensure you're using the correct identifiers

**Error: "ValidationException"**

Invalid parameters were provided:

1. Check parameter formats (domain IDs start with `dzd_`)
2. Verify required parameters are provided
3. Check string length and character restrictions

**Performance Issues**

If operations are slow:

1. Check your AWS region latency
2. Verify network connectivity to AWS
3. Consider using AWS regions closer to your location

### Advanced Debugging

**Enable verbose logging:**

```bash
# Set environment variable for detailed logs
export DATAZONE_MCP_DEBUG=true
python -m datazone_mcp_server.server
```

**Test individual tools:**

```python
import asyncio
from mcp import create_client

async def test_tool():
    client = await create_client("stdio", ["python", "-m", "datazone_mcp_server.server"])

    # Test domain listing
    result = await client.call_tool("list_domains", {})
    print(result.content[0].text)

asyncio.run(test_tool())
```

## Best Practices

### Security
- Use IAM roles instead of access keys when possible
- Follow principle of least privilege for DataZone permissions
- Don't commit AWS credentials to version control
- Rotate access keys regularly

### Performance
- Set `DATAZONE_DOMAIN_ID` to avoid repeated domain lookups
- Use specific identifiers rather than searching when possible
- Consider AWS region proximity for better latency

### Organization
- Use consistent naming conventions for projects and assets
- Leverage domain units to organize large DataZone domains
- Create glossaries early to establish common terminology

## Next Steps

### Advanced Usage
- **[Examples](../examples/)** - See comprehensive usage examples
- **[Best Practices](../examples/best_practices/)** - Learn recommended patterns
- **[Workflows](../examples/workflows/)** - End-to-end workflow examples

### Integration
- **[Building Custom Clients](https://modelcontextprotocol.io/quickstart/client)** - Create your own MCP client
- **[MCP Specification](https://modelcontextprotocol.io/)** - Understand the MCP protocol
- **[AWS DataZone API](https://docs.aws.amazon.com/datazone/latest/APIReference/)** - Learn the underlying AWS APIs

### Contributing
- **[Contributing Guide](../CONTRIBUTING.md)** - Help improve the server
- **[GitHub Issues](https://github.com/wangtianren/datazone-mcp-server/issues)** - Report bugs or request features

---

**Need help?** Check out our [troubleshooting guide](./TROUBLESHOOTING.md) or open an [issue](https://github.com/wangtianren/datazone-mcp-server/issues).
