# Local Development Guide for Bedrock Advisor MCP Server

This guide provides instructions for setting up and running the Bedrock Advisor MCP Server locally for development and testing purposes.

## Prerequisites

- Python 3.10 or higher
- Virtual environment tool (venv, conda, etc.)
- AWS credentials configured (if accessing AWS services)

## Setting Up the Development Environment

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/bedrock-advisor.git
   cd bedrock-advisor
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt
   ```

## Running the Server Locally

### Direct Execution

You can run the server directly using Python:

```bash
python -m awslabs.bedrock_advisor_mcp_server.server
```

### Using MCP Configuration

To use the server with an MCP client like Kiro, Amazon Q Developer, or IDE Assistant, you need to configure it in your MCP configuration file.

1. Create or update your MCP configuration file:

   For Kiro, create or update `.kiro/settings/mcp.json` in your workspace:

   ```json
   {
     "mcpServers": {
       "bedrock-advisor-local": {
         "command": "/path/to/your/project/.venv/bin/python",
         "args": ["-m", "awslabs.bedrock_advisor_mcp_server.server"],
         "env": {
           "AWS_REGION": "us-east-1",
           "FASTMCP_LOG_LEVEL": "ERROR",
           "MCP_TRANSPORT": "stdio",
           "PYTHONPATH": "/path/to/your/project"
         },
         "cwd": "/path/to/your/project",
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

   Replace `/path/to/your/project` with the absolute path to your project directory.

2. Restart your MCP client to apply the changes.

## Configuration

The server can be configured using a `config.json` file in the project root directory. See [Configuration Guide](configuration.md) for details.

Example `config.json`:

```json
{
  "server": {
    "log_level": "INFO",
    "enable_metrics": false
  },
  "aws": {
    "region": "us-east-1",
    "profile": null,
    "endpoint_url": null
  },
  "model_data": {
    "cache_ttl_minutes": 60,
    "max_models": 100,
    "use_api": true
  },
  "recommendation": {
    "max_recommendations": 3,
    "weights": {
      "capability_match": 0.4,
      "performance": 0.2,
      "cost": 0.2,
      "availability": 0.1,
      "reliability": 0.1
    }
  },
  "availability": {
    "cache_ttl_seconds": 3600,
    "timeout_seconds": 10
  }
}
```

## Running Tests

To run the tests:

```bash
./run_tests.sh
```

To run tests with coverage:

```bash
./run_tests_with_coverage.sh
```

## Debugging

For debugging, you can set the log level to DEBUG:

```bash
export FASTMCP_LOG_LEVEL=DEBUG
python -m awslabs.bedrock_advisor_mcp_server.server
```

Or update the `config.json` file:

```json
{
  "server": {
    "log_level": "DEBUG",
    "enable_metrics": false
  },
  ...
}
```

## Common Issues

### Module Not Found Errors

If you encounter "Module not found" errors, make sure your `PYTHONPATH` environment variable includes the project directory:

```bash
export PYTHONPATH=/path/to/your/project:$PYTHONPATH
```

Or update the `PYTHONPATH` in your MCP configuration.

### AWS Credentials

If you're having issues with AWS credentials, make sure they are properly configured:

```bash
aws configure
```

Or set the environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### MCP Client Connection Issues

If your MCP client can't connect to the server:

1. Check that the server is running
2. Verify the MCP configuration paths are correct
3. Check the logs for any error messages
4. Make sure the `MCP_TRANSPORT` environment variable is set to `stdio`
