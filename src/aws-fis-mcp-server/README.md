# AWS FIS MCP Server

A Model Context Protocol (MCP) server that enables Large Language Models (LLMs) to plan, create, and execute AWS Fault Injection Simulator (FIS) experiments.

## Description

This project provides a Model Context Protocol (MCP) server that enables LLMs to interact with AWS Fault Injection Simulator (FIS). It allows AI assistants to plan, create, and execute fault injection experiments in AWS environments.

## Features

- **FIS Experiment Management**
  - List all FIS experiments
  - Get detailed experiment information
  - Start and monitor experiments
  - Create experiment templates

- **CloudFormation Integration**
  - List CloudFormation stacks
  - Get stack resources

- **Resource Explorer**
  - List AWS resources
  - Create and manage resource views

## Requirements

- Python 3.10+
- AWS credentials with appropriate permissions
- Required Python packages (see Installation)

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -e .
   ```

## Configuration

Create a `.env` file in the project root with the following AWS credentials:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token  # If using temporary credentials
```

## Usage

Run the MCP server:

```bash
python main.py
```

The server provides the following MCP tools:

### AWS FIS Tools
- `list_fis_experiments`: Retrieves a list of available FIS experiments
- `get_experiment`: Gets detailed information about a specific experiment
- `list_experiment_templates`: Lists all experiment templates
- `get_experiment_template`: Gets details about a specific template
- `start_experiment`: Starts an experiment and monitors its status

### CloudFormation Tools
- `list_cfn_stacks`: Lists all CloudFormation stacks
- `get_stack_resources`: Gets resources from a specific stack

### Resource Explorer Tools
- `list_resources`: Lists AWS resources
- `list_views`: Lists resource explorer views
- `create_view`: Creates a new resource view

## Understanding MCP (Model Context Protocol)

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

The MCP Inspector is a powerful tool for debugging and troubleshooting your MCP server. It allows you to:

### Setting Up MCP Inspector

1. Install the MCP Inspector:
   ```bash
   pip install mcp-inspector
   ```

2. Run your MCP server in one terminal:
   ```bash
   python main.py
   ```

3. In another terminal, start the MCP Inspector:
   ```bash
   mcp-inspector
   ```

### Using MCP Inspector

- **Inspect Tool Calls**: View all tool calls made by the AI, including parameters and return values
- **Debug Errors**: Identify where errors occur in your tool implementations
- **Test Tools Manually**: Execute tools directly to verify they work as expected
- **View Request/Response Flow**: See the complete interaction between the AI and your MCP server
- **Analyze Performance**: Identify slow tools that might need optimization

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
