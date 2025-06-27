# Getting Started with AWS DataZone MCP Server

Welcome! This guide will walk you through setting up and using the AWS DataZone MCP server step-by-step. In 30 minutes, you'll have a working setup and understand how to manage AWS DataZone resources through natural language.

## What You'll Learn

By the end of this guide, you'll be able to:
- Set up the AWS DataZone MCP server
- Connect it to Claude for Desktop
- Manage DataZone domains, projects, and assets through conversation
- Troubleshoot common issues
- Use the server for real data governance workflows

## Quick Overview

| Tutorial | Time | Difficulty | What You'll Do |
|----------|------|------------|----------------|
| [Quick Start](#tutorial-1-quick-start-5-minutes) | 5 min | Easy | Install and verify the server |
| [Claude Integration](#tutorial-2-claude-desktop-integration-10-minutes) | 10 min | Easy | Connect to Claude for Desktop |
| [First Operations](#tutorial-3-your-first-datazone-operations-10-minutes) | 10 min | Medium | Explore domains and projects |
| [Real Workflow](#tutorial-4-complete-data-governance-workflow-15-minutes) | 15 min | Medium | End-to-end data management |

**Total Time: ~40 minutes**

---

## Tutorial 1: Quick Start (5 minutes)

Let's get the server installed and running quickly.

### Prerequisites Check

Before we start, make sure you have:
- [ ] Python 3.10 or higher
- [ ] AWS account with DataZone access
- [ ] Basic familiarity with command line

**Check your Python version:**
```bash
python --version
# Should show Python 3.10 or higher
```

### Step 1: Install the MCP Server

```bash
# Install the AWS DataZone MCP server
pip install datazone-mcp-server

# Verify installation
python -m datazone_mcp_server.server --help
```

**Expected output:**
```
AWS DataZone MCP Server
Available tools: 38 tools across 5 categories
```

### Step 2: Configure AWS Credentials

**=Using AWS CLI (Recommended)**
```bash
# Install AWS CLI if you haven't already
pip install awscli

# Configure your credentials
aws configure
```

You'll be prompted for:
- AWS Access Key ID
- AWS Secret Access Key
- Default region
- Default output format: `json`
```

**If you have a specific DataZone domain ID:**
```json
{
    "mcpServers": {
        "aws-datazone": {
            "command": "python",
            "args": [
                "-m",
                "datazone_mcp_server.server"
            ],
            "env": {
                "AWS_DEFAULT_REGION": "us-east-1",
                "DATAZONE_DOMAIN_ID": "dzd_your_domain_id_here"
            }
        }
    }
}
```

**If you're using uv (installed from source):**

For users who cloned the repository and are using uv:

```json
{
    "mcpServers": {
        "aws-datazone": {
            "command": "/Users/username/.local/bin/uv",
            "args": [
                "--directory",
                "/path/to/datazone-mcp-server",
                "run",
                "python",
                "-m",
                "datazone_mcp_server.server"
            ],
            "env": {
                "AWS_DEFAULT_REGION": "us-east-1",
                "DATAZONE_DOMAIN_ID": "dzd_your_domain_id_here"
            }
        }
    }
}
```

**Note**: Replace `/Users/username/.local/bin/uv` with the path from `which uv` and `/path/to/datazone-mcp-server` with your actual project path.

### Step 3: Test Your Setup

```bash
# Test AWS credentials
aws sts get-caller-identity

# Test the MCP server
python -c "
import asyncio
from mcp import create_client

async def test():
    client = await create_client('stdio', ['python', '-m', 'datazone_mcp_server.server'])
    tools = await client.list_tools()
    print(f'Server running with {len(tools.tools)} tools')

asyncio.run(test())
"
```

**Success!** If you see "Server running with 38 tools", you're ready for the next tutorial.

**Troubleshooting:**
- **"ModuleNotFoundError"**: Run `pip install datazone-mcp-server` again
- **"NoCredentialsError"**: Double-check your AWS credentials setup
- **"ImportError: mcp"**: Run `pip install mcp`

---

## Tutorial 2: Claude Desktop Integration (10 minutes)

Now let's connect your server to Claude for Desktop for natural language interaction.

### Step 1: Install Claude for Desktop

1. **Download Claude for Desktop** from [claude.ai/download](https://claude.ai/download)
2. **Install** the application
3. **Launch** Claude for Desktop and verify it's working

### Step 2: Locate Configuration File

**macOS:**
```bash
# Create directory if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude

# Edit the configuration file
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
# Create directory if it doesn't exist
New-Item -ItemType Directory -Force -Path "$env:AppData\Claude"

# Edit the configuration file
notepad "$env:AppData\Claude\claude_desktop_config.json"
```

**Linux:**
```bash
# Create directory if it doesn't exist
mkdir -p ~/.config/Claude

# Edit the configuration file
nano ~/.config/Claude/claude_desktop_config.json
```

### Step 3: Configure the MCP Server

Add this configuration to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "aws-datazone": {
            "command": "python",
            "args": [
                "-m",
                "datazone_mcp_server.server"
            ],
            "env": {
                "AWS_DEFAULT_REGION": "us-east-1"
            }
        }
    }
}
```

**If you have a specific DataZone domain ID:**
```json
{
    "mcpServers": {
        "aws-datazone": {
            "command": "python",
            "args": [
                "-m",
                "datazone_mcp_server.server"
            ],
            "env": {
                "AWS_DEFAULT_REGION": "us-east-1",
                "DATAZONE_DOMAIN_ID": "dzd_your_domain_id_here"
            }
        }
    }
}
```

### Step 4: Restart Claude Desktop

1. **Quit** Claude for Desktop completely
2. **Restart** the application
3. **Look** for the tools icon  in the interface

### Step 5: Verify Integration

In Claude for Desktop, try this message:

```
Hi! I'd like to explore my AWS DataZone environment. Can you show me what tools are available?
```

**Expected Response:**
Claude should respond with information about the 38 available DataZone tools, organized into categories like Domain Management, Project Management, etc.

**Troubleshooting:**
- **No tools showing**: Check your configuration file syntax
- **Server not starting**: Verify Python can run the server independently
- **Connection errors**: Check AWS credentials are properly configured

---

## Tutorial 3: Your First DataZone Operations (10 minutes)

Let's explore your DataZone environment and perform basic operations.

### Step 1: Discover Your Domains

In Claude for Desktop, ask:

```
What DataZone domains do I have access to?
```

**What happens:**
1. Claude uses the `list_domains` tool
2. You'll see a list of available domains
3. Claude will format the results in a readable way

**Example response:**
```
I found 2 DataZone domains in your account:

1. **Analytics Domain** (dzd_abc123)
   - Status: ACTIVE
   - Created: 2024-01-15
   - Description: Domain for analytics workloads

2. **Data Lake Domain** (dzd_xyz789)
   - Status: ACTIVE
   - Created: 2024-02-01
   - Description: Central data lake domain
```

### Step 2: Explore a Specific Domain

Pick a domain ID from the previous step and ask:

```
Can you give me detailed information about domain dzd_abc123?
```

**What you'll learn:**
- Domain configuration details
- Portal URL for web access
- SSO configuration
- Creation timestamp and status

### Step 3: List Projects in Your Domain

```
What projects exist in domain dzd_abc123?
```

**You'll see:**
- Project names and IDs
- Creation dates
- Project descriptions
- Project owners

### Step 4: Explore Domain Organization

```
Show me the organizational structure of domain dzd_abc123
```

**This reveals:**
- Domain units (organizational structure)
- How the domain is organized
- Hierarchical relationships

### Step 5: Try a Search

```
Search for any assets related to "customer" in domain dzd_abc123
```

**You'll discover:**
- Existing data assets
- Published data catalog items
- Search capabilities across the domain

### Tutorial 3 Complete!

You've now explored your DataZone environment using natural language. You should understand:
- How to discover domains and projects
- How to get detailed information about resources
- How search works across DataZone

---

## Tutorial 4: Complete Data Governance Workflow (15 minutes)

Let's walk through a real-world scenario: setting up a new analytics project with proper data governance.

### Scenario
You're a data engineer setting up a new "Customer Analytics" project. You need to:
1. Create the project
2. Set up a business glossary
3. Create and publish a data asset
4. Demonstrate data discovery

### Step 1: Create a New Project

```
I need to create a new project called "Customer Analytics" in domain dzd_abc123. The project should be for analyzing customer behavior and purchasing patterns.
```

**What Claude will do:**
1. Use the `create_project` tool
2. Set appropriate parameters
3. Show you the created project details

**Expected result:**
```
Successfully created project "Customer Analytics"

Project Details:
- Project ID: prj_new123
- Domain: dzd_abc123
- Description: For analyzing customer behavior and purchasing patterns
- Status: ACTIVE
- Created: Just now
```

### Step 2: Add Yourself as Project Owner

```
Add me as an owner of project prj_new123
```

**Note:** You'll need your AWS user identifier. Claude might ask you for it, or suggest using:
```
Add user arn:aws:iam::123456789012:user/john.doe as owner of project prj_new123
```

### Step 3: Create a Business Glossary

```
Create a business glossary called "Customer Analytics Terms" in project prj_new123. This glossary will define terms used in customer analytics.
```

**Result:**
- New glossary created
- Glossary ID provided
- Ready for term definitions

### Step 4: Add Glossary Terms

```
Add a glossary term "Customer LTV" to the glossary with definition "Customer Lifetime Value - the total revenue a customer will generate over their entire relationship with the company"
```

**Then add more terms:**
```
Add another term "Churn Rate" with definition "The percentage of customers who stop using the service during a given time period"
```

### Step 5: Create a Data Asset

```
Create a new table asset called "customer_transactions" in project prj_new123. This asset represents a table containing all customer purchase transactions with columns for customer_id, transaction_date, amount, and product_category.
```

**What you'll get:**
- New asset created
- Asset ID assigned
- Metadata structure defined

### Step 6: Publish to Data Catalog

```
Publish the customer_transactions asset to the data catalog so other teams can discover it
```

**This makes your asset:**
- Discoverable by other users
- Available for subscription requests
- Part of the searchable data catalog

### Step 7: Test Discovery

```
Search for assets related to "customer" in the data catalog
```

**You should see:**
- Your newly published asset
- Any other customer-related assets
- Full search capabilities working

### Step 8: Check Your Work

```
Give me a summary of everything we've set up for the Customer Analytics project
```

**Claude will summarize:**
- Project details and membership
- Glossary and terms created
- Assets created and published
- Overall project structure

### Tutorial 4 Complete!

 **Congratulations!** You've completed a full data governance workflow:

- Created a project with proper organization
- Established business terminology through glossaries
- Created and published data assets
- Made data discoverable through the catalog
- Used natural language for all operations

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Server Not Connecting

**Symptoms:**
- No tools showing in Claude Desktop
- "Server not found" errors

**Solutions:**
```bash
# Test server independently
python -m datazone_mcp_server.server

# Check configuration syntax
python -c "import json; print(json.load(open('path/to/claude_desktop_config.json')))"

# Verify Python path
which python
```

#### 2. AWS Permission Errors

**Symptoms:**
- "AccessDeniedException"
- "NoCredentialsError"

**Solutions:**
```bash
# Verify credentials
aws sts get-caller-identity

# Test DataZone access
aws datazone list-domains

# Check IAM permissions
aws iam get-user
```

**Required IAM permissions:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "datazone:*"
            ],
            "Resource": "*"
        }
    ]
}
```

#### 3. Tool Execution Failures

**Symptoms:**
- Tools appear but fail when used
- "ValidationException" errors

**Solutions:**
1. **Check domain ID format**: Should start with `dzd_`
2. **Verify resource exists**: Check AWS Console
3. **Check parameter formats**: Review tool documentation

#### 4. Performance Issues

**Symptoms:**
- Slow responses
- Timeouts

**Solutions:**
```bash
# Set region closer to you
export AWS_DEFAULT_REGION="your-closest-region"

# Use specific domain ID
export DATAZONE_DOMAIN_ID="dzd_your_domain"

# Enable debug logging
export DATAZONE_MCP_DEBUG=true
```

### Getting Help

#### Self-Service Resources
1. **[Tool Reference](./TOOL_REFERENCE.md)** - Complete tool documentation
2. **[User Guide](./USER_GUIDE.md)** - Detailed setup and usage
3. **[Examples](../examples/)** - Code samples and patterns

#### Support Channels
1. **[GitHub Issues](https://github.com/wangtianren/datazone-mcp-server/issues)** - Bug reports and feature requests
2. **[AWS DataZone Documentation](https://docs.aws.amazon.com/datazone/)** - Official AWS documentation
3. **[MCP Documentation](https://modelcontextprotocol.io/)** - MCP protocol details

---

## Next Steps

### Explore Advanced Features

Now that you have the basics working, explore advanced capabilities:

#### 1. Complex Workflows
```
Set up a complete data pipeline with multiple assets, connections, and subscriptions
```

#### 2. Batch Operations
```
Create multiple projects at once with standardized configurations
```

#### 3. Data Subscriptions
```
Set up asset subscription workflows for data sharing between teams
```

#### 4. Advanced Search
```
Use complex search filters to find specific types of assets across multiple projects
```

### Integration Opportunities

#### 1. Custom Scripts
Create Python scripts that use the MCP server programmatically:

```python
import asyncio
from mcp import create_client

async def automate_project_setup():
    client = await create_client("stdio", ["python", "-m", "datazone_mcp_server.server"])

    # Create project
    project = await client.call_tool("create_project", {
        "domain_identifier": "dzd_abc123",
        "name": "Automated Project",
        "description": "Created via automation"
    })

    # Add more automation steps...
```

#### 2. Team Workflows
Integrate with your team's existing tools:
- CI/CD pipelines for data asset deployment
- Slack notifications for data catalog updates
- Automated compliance checking

#### 3. Custom Clients
Build your own MCP client for specific use cases:
- Web interfaces for non-technical users
- Mobile apps for data discovery
- Integration with existing data tools

### Learning Resources

#### AWS DataZone Deep Dive
- **[AWS DataZone Workshop](https://catalog.workshops.aws/amazon-datazone/en-US)**
- **[DataZone Best Practices](https://docs.aws.amazon.com/datazone/latest/userguide/best-practices.html)**
- **[Data Governance with DataZone](https://aws.amazon.com/blogs/big-data/)**

#### MCP Development
- **[Building MCP Servers](https://modelcontextprotocol.io/quickstart/server)**
- **[MCP Client Development](https://modelcontextprotocol.io/quickstart/client)**
- **[MCP Community Examples](https://github.com/modelcontextprotocol)**

---

## Quick Reference

### Essential Commands

```bash
# Start server
python -m datazone_mcp_server.server

# Test connection
python -c "from mcp import create_client; import asyncio; asyncio.run(create_client('stdio', ['python', '-m', 'datazone_mcp_server.server']).list_tools())"

# Check AWS credentials
aws sts get-caller-identity

# Verify DataZone access
aws datazone list-domains
```

### Configuration Files

**Claude Desktop Config:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%AppData%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### Environment Variables

```bash
export AWS_DEFAULT_REGION="us-east-1"
export DATAZONE_DOMAIN_ID="dzd_your_domain_id"
export DATAZONE_MCP_DEBUG="true"  # For debugging
```

### Common Natural Language Queries

```
# Discovery
"What domains do I have access to?"
"Show me all projects in domain dzd_abc123"
"Search for assets containing 'customer'"

# Creation
"Create a project called 'Analytics' in domain dzd_abc123"
"Create a glossary called 'Business Terms' in project prj_123"
"Create a table asset for customer data"

# Management
"Add user@company.com to project prj_123"
"Publish asset ast_456 to the catalog"
"Create a connection to our data warehouse"
```

---

 **You're now ready to use AWS DataZone MCP Server productively!**

This getting started guide has taken you from installation to real-world usage. You now have the foundation to manage AWS DataZone resources through natural language conversation.

**Happy data governing!**
