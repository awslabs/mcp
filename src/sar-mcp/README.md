# AWS Service Reference MCP Server

This MCP server provides tools to interact with the AWS Programmatic Service Reference, allowing you to:
- List all available AWS services
- Get API actions for specific AWS services
- Get condition keys supported by specific API actions
- Get resource types supported by specific API actions
- Get action properties for specific API actions (such as write or list capabilities)

## Installation

1. Make sure you have Python 3.10 or higher installed
2. Clone this repository
3. Install the required dependencies:

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Server

You can run the server directly:

```bash
python aws_service_reference.py
```

### Using with Claude Desktop

1. Open your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the server configuration:

```json
{
    "mcpServers": {
        "aws-service-reference": {
            "command": "python",
            "args": ["/ABSOLUTE/PATH/TO/aws_service_reference.py"]
        }
    }
}
```

Replace `/ABSOLUTE/PATH/TO/` with the actual path to where you saved the server file.

3. Restart Claude Desktop

### Available Tools

The server provides five tools:

1. `list_aws_services`: Lists all available AWS services
2. `get_service_actions`: Gets API actions for a specific AWS service
3. `get_action_condition_keys`: Gets condition keys supported by a specific API action
4. `get_action_resource_types`: Gets resource types supported by a specific API action
5. `get_action_properties`: Gets action properties for a specific API action (such as write or list capabilities)

### Example Usage in Claude

Once connected, you can ask Claude questions like:

- "What AWS services are available?"
- "Show me all the API actions for the S3 service"
- "What condition keys are supported by the s3:PutObject action?"
- "What resource types can I use with the ec2:RunInstances action?"
- "What are the action properties of s3:PutObject?"

### Example: Using the get_action_properties Tool

The `get_action_properties` tool provides information about what an action is capable of, such as whether it has write or list capabilities. This is useful when creating IAM policies and understanding the nature of different API actions.

```python
# Example response for get_action_properties with s3:PutObject
Action properties for s3:PutObject:
IsList: False
IsPermissionManagement: False
IsTaggingOnly: False
IsWrite: True
```

You can use this information to:
- Identify write operations that modify resources
- Find permission management actions that should be carefully controlled
- Distinguish between read-only and write operations
- Identify actions that only modify tags

## Development

### Testing with MCP Inspector

You can test the server using the MCP Inspector:

```bash
mcp dev aws_service_reference.py
```

### Dependencies

The project uses the following dependencies (specified in `requirements.txt`):
- `mcp[cli]>=0.1.0`: The Model Context Protocol SDK with CLI tools
- `httpx>=0.26.0`: Modern HTTP client for making API requests

## Troubleshooting

If you encounter issues:

1. Verify your Python version is 3.10 or higher
2. Ensure all dependencies are installed correctly:
   ```bash
   pip install -r requirements.txt
   ```
3. Check the Claude Desktop logs:
   - macOS: `~/Library/Logs/Claude/mcp*.log`
   - Windows: `%APPDATA%\Claude\logs\mcp*.log`
4. Make sure you're using absolute paths in the Claude Desktop configuration

## License

This project is licensed under the MIT License. 