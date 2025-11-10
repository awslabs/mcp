# MCP Inspector Setup Guide for AWS HealthOmics MCP Server

This guide provides step-by-step instructions for setting up and running the MCP Inspector with the AWS HealthOmics MCP server for development and testing purposes.

## Overview

The MCP Inspector is a web-based tool that allows you to interactively test and debug MCP servers. It provides a user-friendly interface to explore available tools, test function calls, and inspect responses.

## Prerequisites

Before starting, ensure you have the following installed:

1. **uv** (Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Node.js and npm** (for MCP Inspector):
   - Download from [nodejs.org](https://nodejs.org/) or use a package manager

3. **MCP Inspector** (no installation needed, runs via npx):
   ```bash
   # No installation required - runs directly via npx
   npx @modelcontextprotocol/inspector --help
   ```

4. **AWS CLI** (configured with appropriate credentials):
   ```bash
   aws configure
   ```

## Setup Methods

### Method 1: Using Source Code (Recommended for Development)

This method is ideal when you're developing or modifying the HealthOmics MCP server.

1. **Navigate to the HealthOmics server directory** (IMPORTANT - must be in this directory):
   ```bash
   cd src/aws-healthomics-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:

   **Option A: Create a `.env` file** in the server directory:
   ```bash
   cat > .env << EOF
   export AWS_REGION=us-east-1
   export AWS_PROFILE=your-aws-profile
   export FASTMCP_LOG_LEVEL=DEBUG
   export HEALTHOMICS_DEFAULT_MAX_RESULTS=10
   export GENOMICS_SEARCH_S3_BUCKETS=s3://your-genomics-bucket/,s3://another-bucket/
   EOF
   ```

   **Option B: Export them directly**:
   ```bash
   export AWS_REGION=us-east-1
   export AWS_PROFILE=your-aws-profile
   export FASTMCP_LOG_LEVEL=DEBUG
   export HEALTHOMICS_DEFAULT_MAX_RESULTS=10
   export GENOMICS_SEARCH_S3_BUCKETS=s3://your-genomics-bucket/,s3://another-bucket/
   ```

4. **Start the MCP Inspector with source code** (run from `src/aws-healthomics-mcp-server` directory):

   **Option A: Using .env file (recommended)**:
   ```bash
   # Source the .env file to load environment variables
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Option B: Using .env file with one command**:
   ```bash
   # Load .env and run in one command
   source .env && npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Option C: Using MCP Inspector's environment variable support**:
   ```bash
   npx @modelcontextprotocol/inspector \
     -e AWS_REGION=us-east-1 \
     -e AWS_PROFILE=your-profile \
     -e FASTMCP_LOG_LEVEL=DEBUG \
     -e HEALTHOMICS_DEFAULT_MAX_RESULTS=100 \
     -e GENOMICS_SEARCH_S3_BUCKETS=s3://your-bucket/ \
     uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Option D: Direct execution without .env**:
   ```bash
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   **Important**: You must run these commands from the `src/aws-healthomics-mcp-server` directory for the module imports to work correctly.

### Method 2: Using the Installed Package

This method uses the published package, suitable for testing the released version.

1. **Install the server globally**:
   ```bash
   uvx install awslabs.aws-healthomics-mcp-server
   ```

2. **Set environment variables**:
   ```bash
   export AWS_REGION=us-east-1
   export AWS_PROFILE=your-aws-profile
   export FASTMCP_LOG_LEVEL=DEBUG
   export HEALTHOMICS_DEFAULT_MAX_RESULTS=10
   export GENOMICS_SEARCH_S3_BUCKETS=s3://your-genomics-bucket/
   ```

3. **Start the MCP Inspector**:
   ```bash
   npx @modelcontextprotocol/inspector uvx awslabs.aws-healthomics-mcp-server
   ```

### Method 3: Using a Configuration File

This method allows you to save your configuration for repeated use.

1. **Create a configuration file** (`healthomics-inspector-config.json`):

   **For source code development**:
   ```json
   {
     "command": "uv",
     "args": ["run", "-m", "awslabs.aws_healthomics_mcp_server.server"],
     "env": {
       "AWS_REGION": "us-east-1",
       "AWS_PROFILE": "your-aws-profile",
       "FASTMCP_LOG_LEVEL": "DEBUG",
       "HEALTHOMICS_DEFAULT_MAX_RESULTS": "10",
       "GENOMICS_SEARCH_S3_BUCKETS": "s3://your-genomics-bucket/,s3://shared-references/"
     }
   }
   ```

   **Alternative for direct Python execution**:
   ```json
   {
     "command": "uv",
     "args": ["run", "python", "awslabs/aws_healthomics_mcp_server/server.py"],
     "env": {
       "AWS_REGION": "us-east-1",
       "AWS_PROFILE": "your-aws-profile",
       "FASTMCP_LOG_LEVEL": "DEBUG",
       "HEALTHOMICS_DEFAULT_MAX_RESULTS": "10",
       "GENOMICS_SEARCH_S3_BUCKETS": "s3://your-genomics-bucket/,s3://shared-references/"
     }
   }
   ```

2. **Start the inspector with the config**:
   ```bash
   npx @modelcontextprotocol/inspector --config healthomics-inspector-config.json
   ```

## Environment Variables Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `AWS_REGION` | AWS region for HealthOmics operations | `us-east-1` | `us-west-2` |
| `AWS_PROFILE` | AWS CLI profile for authentication | (default profile) | `genomics-dev` |
| `FASTMCP_LOG_LEVEL` | Server logging level | `WARNING` | `DEBUG`, `INFO`, `ERROR` |
| `HEALTHOMICS_DEFAULT_MAX_RESULTS` | Default pagination limit | `10` | `50` |
| `GENOMICS_SEARCH_S3_BUCKETS` | S3 buckets for genomics file search | (none) | `s3://bucket1/,s3://bucket2/path/` |

### Testing-Specific Variables

These variables are primarily for testing against mock services:

| Variable | Description | Example |
|----------|-------------|---------|
| `HEALTHOMICS_SERVICE_NAME` | Override service name for testing | `omics-mock` |
| `HEALTHOMICS_ENDPOINT_URL` | Override endpoint URL for testing | `http://localhost:8080` |

## Using the MCP Inspector

Once started, the MCP Inspector will be available at `http://localhost:5173`.

### Initial Testing Steps

1. **Verify Connection**: The inspector should show "Connected" status
2. **List Tools**: You should see all available HealthOmics MCP tools
3. **Test Basic Functionality**:
   - Try `GetAHOSupportedRegions` (requires no parameters)
   - Test `ListAHOWorkflows` to verify AWS connectivity

### Available Tools Categories

The HealthOmics MCP server provides tools in several categories:

- **Workflow Management**: Create, list, and manage workflows
- **Workflow Execution**: Start runs, monitor progress, manage tasks
- **Analysis & Troubleshooting**: Performance analysis, failure diagnosis, log access
- **File Discovery**: Search for genomics files across storage systems
- **Workflow Validation**: Lint WDL and CWL workflow definitions
- **Utility Tools**: Region information, workflow packaging

### Example Test Scenarios

1. **List Available Regions**:
   - Tool: `GetAHOSupportedRegions`
   - Parameters: None
   - Expected: List of AWS regions where HealthOmics is available

2. **List Workflows**:
   - Tool: `ListAHOWorkflows`
   - Parameters: `max_results: 5`
   - Expected: List of workflows in your account

3. **Search for Files**:
   - Tool: `SearchGenomicsFiles`
   - Parameters: `search_terms: ["fastq"]`, `file_type: "fastq"`
   - Expected: FASTQ files from configured S3 buckets

## Troubleshooting

### Common Issues and Solutions

#### 1. Connection Failed
**Symptoms**: Inspector shows "Disconnected" or connection errors

**Solutions**:
- Check that the server process is running
- Verify no other process is using the same port
- Check server logs for error messages

#### 2. AWS Authentication Errors
**Symptoms**: Tools return authentication or permission errors

**Solutions**:
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Test HealthOmics access
aws omics list-workflows --region us-east-1

# Check AWS profile
echo $AWS_PROFILE
```

#### 3. No Tools Visible
**Symptoms**: Inspector connects but shows no available tools

**Solutions**:
- Check server startup logs for import errors
- Verify all dependencies are installed: `uv sync`
- Ensure you're using the correct server command

#### 4. Region Not Supported
**Symptoms**: HealthOmics API calls fail with region errors

**Solutions**:
- Use `GetAHOSupportedRegions` to see available regions
- Update `AWS_REGION` to a supported region
- Common supported regions: `us-east-1`, `us-west-2`, `eu-west-1`

#### 5. S3 Access Issues for File Search
**Symptoms**: `SearchGenomicsFiles` returns empty results or errors

**Solutions**:
- Verify S3 bucket permissions
- Check `GENOMICS_SEARCH_S3_BUCKETS` configuration
- Ensure buckets exist and contain genomics files

### Debug Mode

For detailed debugging, start with maximum logging:

```bash
export FASTMCP_LOG_LEVEL=DEBUG
cd src/aws-healthomics-mcp-server
npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
```

### Log Analysis

Server logs will show:
- Tool registration and initialization
- AWS API calls and responses
- Error details and stack traces
- Performance metrics

## Security Considerations

### Local Development

The MCP Inspector runs locally and connects directly to your MCP server:
- ✅ No external network exposure by default
- ✅ Runs on localhost for development and testing
- ✅ Direct connection to your local server process
- ⚠️ Ensure your AWS credentials are properly secured
- ⚠️ Be cautious when testing with production AWS accounts

### AWS Credentials

Ensure your AWS credentials have appropriate permissions:
- HealthOmics read/write access
- S3 read access for configured buckets
- CloudWatch Logs read access for log retrieval
- IAM PassRole permissions for workflow execution

## Advanced Configuration

### Custom Port

To run the inspector on a different port:

```bash
mcp-inspector --insecure --port 8080 uv run -m awslabs.aws_healthomics_mcp_server.server
```

### Multiple Server Testing

You can run multiple MCP servers simultaneously by using different ports and configuration files.

### Integration with Development Workflow

For active development:

1. Use Method 1 (source code) for immediate testing of changes
2. Set up file watching to restart the server on code changes
3. Use DEBUG logging to trace execution
4. Keep the inspector open in a browser tab for quick testing

## Using Environment Variables

### Working with .env Files

If you have a `.env` file in your `src/aws-healthomics-mcp-server` directory, you can use it in several ways:

1. **Source the .env file before running** (recommended):
   ```bash
   cd src/aws-healthomics-mcp-server
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

2. **Load and run in one command**:
   ```bash
   cd src/aws-healthomics-mcp-server
   source .env && npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

3. **Use a shell script** (create `run-inspector.sh`):
   ```bash
   #!/bin/bash
   cd src/aws-healthomics-mcp-server
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

   Then run:
   ```bash
   chmod +x run-inspector.sh
   ./run-inspector.sh
   ```

### Environment Variable Format

Your `.env` file should contain export statements:
```bash
export AWS_REGION=us-east-1
export AWS_PROFILE=default
export FASTMCP_LOG_LEVEL=DEBUG
export HEALTHOMICS_DEFAULT_MAX_RESULTS=100
export GENOMICS_SEARCH_S3_BUCKETS=s3://omics-data/,s3://broad-references/
```

### Verifying Environment Variables

To check if your environment variables are loaded correctly:
```bash
source .env
echo "AWS_REGION: $AWS_REGION"
echo "AWS_PROFILE: $AWS_PROFILE"
echo "FASTMCP_LOG_LEVEL: $FASTMCP_LOG_LEVEL"
echo "GENOMICS_SEARCH_S3_BUCKETS: $GENOMICS_SEARCH_S3_BUCKETS"
```

## Development and Testing from Source Code

### Quick Start for Developers

If you're working on the HealthOmics MCP server source code:

1. **One-time setup**:
   ```bash
   cd src/aws-healthomics-mcp-server
   uv sync
   # Create or edit your .env file with your settings
   ```

2. **Start testing** (from the `src/aws-healthomics-mcp-server` directory):
   ```bash
   source .env
   npx @modelcontextprotocol/inspector uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

3. **Make changes to the code** and restart the inspector to test them immediately.

### Testing Individual Components

You can also test the server components independently:

1. **Test server startup** (from `src/aws-healthomics-mcp-server` directory):
   ```bash
   uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

2. **Run with Python module syntax**:
   ```bash
   uv run python -m awslabs.aws_healthomics_mcp_server.server
   ```

3. **Test with different log levels**:
   ```bash
   FASTMCP_LOG_LEVEL=DEBUG uv run python awslabs/aws_healthomics_mcp_server/server.py
   ```

### Development Tips

- **Code changes**: The server needs to be restarted after code changes
- **Environment variables**: Set them once in your shell session or use a `.env` file
- **Debugging**: Use `FASTMCP_LOG_LEVEL=DEBUG` to see detailed execution logs
- **Testing tools**: Use the inspector's tool testing interface to verify individual functions

## Additional Resources

- [MCP Inspector Documentation](https://modelcontextprotocol.io/docs/tools/inspector)
- [AWS HealthOmics Documentation](https://docs.aws.amazon.com/omics/)
- [HealthOmics MCP Server README](./README.md)
- [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

## Support

For issues specific to the HealthOmics MCP server:
1. Check the server logs for detailed error messages
2. Verify AWS permissions and region availability
3. Test AWS connectivity independently of the MCP server
4. Review the main README.md for configuration requirements

For MCP Inspector issues:
- Refer to the [official MCP documentation](https://modelcontextprotocol.io/)
- Check the inspector's GitHub repository for known issues
