# AWS FIS MCP Server

An MCP server for designing and running controlled chaos engineering experiments on your AWS resources, helping you build more resilient cloud applications.

## Description

This MCP server bridges the gap between AI assistants and AWS Fault Injection Simulator (FIS), enabling controlled chaos engineering experiments through natural language interactions. The server implements the Model Context Protocol to expose FIS capabilities as tools that Large Language Models can understand and utilize.

With this integration, AI assistants can help users design resilience testing scenarios, identify appropriate AWS resources for fault injection, create experiment templates with precise parameters, execute controlled failures, and analyze the results—all while maintaining safety guardrails and following AWS best practices for chaos engineering.

The server provides the following MCP tools:

### AWS FIS Experiment Management Tools
- `list_fis_experiments`: Retrieves a list of available FIS experiments organized by name
- `get_experiment`: Gets detailed information about a specific experiment by ID
- `list_experiment_templates`: Lists all experiment templates with pagination support
- `get_experiment_template`: Gets details about a specific experiment template by ID
- `start_experiment`: Starts an experiment from a template (requires --allow-writes flag)

### AWS FIS Experiment Template Management Tools
- `create_experiment_template`: Creates a new FIS experiment template (requires --allow-writes flag)
- `update_experiment_template`: Updates an existing FIS experiment template

### AWS Resource Discovery Tools
   #### CloudFormation Tools
   - `list_cfn_stacks`: Lists all CloudFormation stacks with pagination support
   - `get_stack_resources`: Gets resources from a specific CloudFormation stack

   #### AWS Resource Explorer Tools
   - `list_resource_explorer_views`: Lists all Resource Explorer views
   - `create_resource_explorer_view`: Creates a new Resource Explorer view (requires --allow-writes flag)
   - `search_resources`: Searches for AWS resources using Resource Explorer based on query string and view ARN
   - `discover_resource_relationships`: Discovers relationships for a specific AWS resource using AWS Config

## Requirements

- Python 3.10+
- AWS credentials with appropriate IAM permissions
- Required Python packages (see Installation)

### Pre-requisites

## AWS Credentials

Create a `.env` file in the project root with the following AWS credentials:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token  # If using temporary credentials
```
## Install uv & python 3.10+

1. Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Setting up the environment
1. Clone this repo `git clone https://github.com/ckq-aws/aws-fis-mcp.git`
2. Change directory `cd src/aws-fis-mcp-server`
3. Run `uv sync` to install project dependencies

## AWS Documenation MCP Server Installation

To ensure AI assistants can accurately determine available FIS actions, it's essential to install the AWS Documentation MCP server alongside this server. This combination prevents hallucinations and guarantees that fault injection experiment templates contain only valid FIS actions.

For detailed installation instructions, please refer to the [AWS Documentation MCP Server README](../../src/aws-documentation-mcp-server/README.md)

## AWS FIS MCP Server Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=awslabs.aws_fis_mcp_server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzX2Zpc19tY3Bfc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit ~/.aws/amazonq/mcp.json)" --> as shown here: https://github.com/awslabs/mcp/tree/main/src/amazon-kendra-index-mcp-server#installation

Start the AWS FIS MCP server by configuring your mcp.json file as follows:

In mcp.json:
```json
{
  "mcpServers": {
    "aws_fis_tool": {
      "command": "uv",
      "args": ["awslabs.aws_fis_mcp_server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Additional Information & Troubleshooting

### Understanding MCP (Model Context Protocol)

MCP is a protocol that enables AI models to interact with external tools and data sources. It provides three main capabilities:

### 1. Tools

Tools are functions that allow AI models to perform actions in the real world. In this server, tools enable the AI to interact with AWS services like FIS, CloudFormation, and Resource Explorer. Tools have:
- A name and description
- Input parameters with types
- Return values that the AI can interpret

Example from this project:
```python
@main_mcp.tool('list_fis_experiments')
def list_all_fis_experiments():
    # Function implementation
    # Returns data that the AI can use
```

### 2. Prompts

Prompts provide context and instructions to the AI model about how to use the tools. They can include:
- Descriptions of what the tools do
- Examples of how to use them
- Guidelines for interpreting results

Prompts help the AI understand the domain (AWS FIS in this case) and make appropriate decisions.

### 3. Resources

Resources are additional data that the AI can access, such as:
- Documentation
- Examples
- Templates
- Historical data

Resources provide the AI with the information it needs to make informed decisions when using the tools.

## Troubleshooting with MCP Inspector

The MCP Inspector is a powerful tool for debugging and troubleshooting your MCP server. It runs locally and acts as a client-side portal to test your MCP server and its functions in real-time without needing to integrate with an actual LLM.

### Installing & Running MCP Inspector

1. Install Node.js if you haven't already: https://nodejs.org/en/download. This will automatically install npx which is needed to run the mcp inspector. The inspector runs directly through npx without requiring installation.
2. Change directory:
```
cd src/aws-fis-mcp-server
```
3. Run MCP Inspector:
- **Command to Start MCP Inspector**:
```
mcp dev server.py
```
4. In your terminal copy or click the link to the inspector with the pre-filled token: http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=[PRE-FILLED TOKEN]
5. Happy debugging!

### Using MCP Inspector

- **Interactive Testing**: Test your MCP server tools directly through a user-friendly interface without needing an LLM
- **Inspect Tool Calls**: View all tool calls, including parameters and return values in real-time
- **Debug Errors**: Identify where errors occur in your tool implementations with detailed error reporting
- **Test Tools Manually**: Execute tools directly with custom parameters to verify they work as expected
- **View Request/Response Flow**: See the complete interaction between the client and your MCP server
- **Analyze Performance**: Identify slow tools that might need optimization with timing metrics

### Common Issues and Solutions

1. **Authentication Errors**:
   - Check your AWS credentials in the `.env` file
   - Verify IAM permissions for the services being accessed

2. **Tool Execution Failures**:
   - Use the Inspector to view the exact error message
   - Check parameter types and values being passed

3. **Slow Performance**:
   - Look for tools that take a long time to execute
   - Consider implementing pagination or limiting result sets

4. **Connection Issues**:
   - Verify network connectivity to AWS services
   - Check for any VPC or security group restrictions

For more information on the MCP Inspector, visit the [official documentation](https://modelcontextprotocol.io/docs/tools/inspector).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Built by cquarcoo@amazon.com with ❤️
