# AWS Labs Perforce MCP Server

An AWS Labs Model Context Protocol (MCP) server for Perforce version control system integration.

## Instructions

This MCP server enables Amazon Q to interact with Perforce version control system through a secure interface. It provides a comprehensive set of functions for managing Perforce repositories, streams, files, and workspaces.

### Features

- Secure connection to Perforce servers using AWS Secrets Manager
- Complete depot and stream management
- File operations (add, checkout, sync)
- Changelist management
- Client workspace configuration

### Prerequisites

- Python 3.6+
- Perforce command-line client (p4)
- AWS credentials configured (for Secrets Manager integration)
- boto3 Python package

### Setup

1. Install [UV](https://docs.astral.sh/uv/)
2. Install required Python packages:
   ```bash
   uv pip install boto3
   ```

3. Configure your AWS credentials:
   ```bash
   aws configure
   ```

4. Update your `~/.aws/amazonq/mcp.json` file:
   ```json
   {
     "mcpServers": {
       "perforce": {
          "command": "uv",
          "args": [
            "run",
            "{path}/mcp_server.py"
          ]
        }
     }
   }
   ```

### Available Tools

#### Connection Management
- `perforce___connect_to_server`: Connect using configuration file or direct parameters
- `perforce___connect_with_secret`: Connect using AWS Secrets Manager credentials

#### Depot Management
- `perforce___list_depots`: List all Perforce depots
- `perforce___create_depot`: Create a new depot
- `perforce___delete_depot`: Delete an existing depot

#### Stream Management
- `perforce___list_streams`: List available streams
- `perforce___create_stream`: Create a new stream
- `perforce___delete_stream`: Delete an existing stream
- `perforce___delete_all_files_from_stream`: Clear all files from a stream

#### File Operations
- `perforce___list_files`: List files in a depot path
- `perforce___get_file`: Retrieve file content
- `perforce___check_out`: Check out file for editing
- `perforce___add_single_file`: Add individual file
- `perforce___add_all_files_to_depot`: Bulk add files
- `perforce___sync`: Sync files from server

#### Changelist Management
- `perforce___list_changelists`: List changelists
- `perforce___create_changelist`: Create new changelist
- `perforce___submit_changes`: Submit pending changes

#### Client Workspace Management
- `perforce___create_client_workspace`: Create and configure workspace

### AWS Secrets Manager Integration

Store Perforce credentials securely using this format:
```json
{
  "server": "ssl:hostname:1666",
  "username": "your-username",
  "password": "your-password"
}
```

### Benefits

1. Secure credential management through AWS Secrets Manager
2. No hardcoded credentials in code
3. Centralized credential management
4. IAM-based access control
5. Optional credential rotation

### Troubleshooting

1. Verify AWS credentials configuration
2. Check secret existence and format in AWS Secrets Manager
3. Confirm p4 command-line client installation
4. Validate network connectivity to Perforce server

## License

This MCP server is licensed under the MIT License.

## Contributing

Keep test coverage at or above the `main` branch using:
```bash
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```
