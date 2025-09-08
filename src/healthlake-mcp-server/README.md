# HealthLake MCP Server

A Model Context Protocol (MCP) server for AWS HealthLake FHIR operations. Provides 11 tools for comprehensive FHIR resource management with automatic datastore discovery.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Option 1: uvx (Recommended)](#option-1-uvx-recommended)
  - [Option 2: uv install](#option-2-uv-install)
  - [Option 3: Docker](#option-3-docker)
- [MCP Client Configuration](#mcp-client-configuration)
  - [Amazon Q Developer CLI](#amazon-q-developer-cli)
  - [Docker Configuration](#docker-configuration)
  - [Other MCP Clients](#other-mcp-clients)
- [Read-Only Mode](#read-only-mode)
- [Available Tools](#available-tools)
  - [Datastore Management](#datastore-management)
  - [FHIR Resource Operations (CRUD)](#fhir-resource-operations-crud)
  - [Advanced Search](#advanced-search)
  - [Job Management](#job-management)
  - [MCP Resources](#mcp-resources)
- [Usage Examples](#usage-examples)
  - [Basic Resource Operations](#basic-resource-operations)
  - [Advanced Search](#advanced-search-1)
  - [Patient Everything](#patient-everything)
- [Authentication](#authentication)
  - [Required Permissions](#required-permissions)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Debug Mode](#debug-mode)
- [Development](#development)
  - [Local Development Setup](#local-development-setup)
  - [Running the Server Locally](#running-the-server-locally)
  - [Development Workflow](#development-workflow)
  - [IDE Setup](#ide-setup)
  - [Testing](#testing)
  - [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Features

- **11 FHIR Tools**: Complete CRUD operations (6 read-only, 5 write), advanced search, patient-everything, job management
- **Read-Only Mode**: Security-focused mode that blocks all mutating operations while preserving read access
- **MCP Resources**: Automatic datastore discovery - no manual datastore IDs needed
- **Advanced Search**: Chained parameters, includes, revIncludes, modifiers, and date/number prefixes with pagination
- **AWS Integration**: SigV4 authentication with automatic credential handling and region support
- **Comprehensive Testing**: 235 tests with 96% coverage ensuring reliability
- **Task Automation**: Poethepoet integration for streamlined development workflow
- **Error Handling**: Structured error responses with specific error types and helpful messages
- **Docker Support**: Containerized deployment with flexible authentication options

## Prerequisites

- **Python 3.10+** (required by MCP framework)
- **AWS credentials** configured
- **AWS HealthLake access** with appropriate permissions

[↑ Back to Table of Contents](#table-of-contents)

## Quick Start

Choose your preferred installation method:

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.healthlake-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuaGVhbHRobGFrZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUiLCJNQ1BfTE9HX0xFVkVMIjoiV0FSTklORyJ9fQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthLake%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthlake-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22MCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |

### Option 1: uvx (Recommended)

```bash
# Install and run latest version automatically
uvx awslabs.healthlake-mcp-server@latest
```

### Option 2: uv install

```bash
uv tool install awslabs.healthlake-mcp-server
awslabs.healthlake-mcp-server
```

### Option 3: Docker

```bash
# Build and run with Docker
docker build -t healthlake-mcp-server .
docker run -e AWS_ACCESS_KEY_ID=xxx -e AWS_SECRET_ACCESS_KEY=yyy healthlake-mcp-server

# Or use pre-built image with environment variables
docker run -e AWS_ACCESS_KEY_ID=your_key -e AWS_SECRET_ACCESS_KEY=your_secret -e AWS_REGION=us-east-1 awslabs/healthlake-mcp-server

# With AWS profile (mount credentials)
docker run -v ~/.aws:/root/.aws -e AWS_PROFILE=your-profile awslabs/healthlake-mcp-server

# Read-only mode
docker run -e AWS_ACCESS_KEY_ID=your_key -e AWS_SECRET_ACCESS_KEY=your_secret -e AWS_REGION=us-east-1 awslabs/healthlake-mcp-server --readonly
```

[↑ Back to Table of Contents](#table-of-contents)

## MCP Client Configuration

### Amazon Q Developer CLI

Add to your MCP configuration file:

**Location:**
- macOS: `~/.aws/amazonq/mcp.json`
- Linux: `~/.config/amazon-q/mcp.json`
- Windows: `%APPDATA%\Amazon Q\mcp.json`

**Configuration:**
```json
{
  "mcpServers": {
    "healthlake": {
      "command": "uvx",
      "args": ["awslabs.healthlake-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile-name",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Read-Only Configuration:**
```json
{
  "mcpServers": {
    "healthlake-readonly": {
      "command": "uvx",
      "args": ["awslabs.healthlake-mcp-server@latest", "--readonly"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile-name",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Docker Configuration

**With environment variables:**
```json
{
  "mcpServers": {
    "healthlake": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-e", "AWS_ACCESS_KEY_ID=your_key",
        "-e", "AWS_SECRET_ACCESS_KEY=your_secret",
        "-e", "AWS_REGION=us-east-1",
        "-e", "MCP_LOG_LEVEL=INFO",
        "awslabs/healthlake-mcp-server"
      ]
    }
  }
}
```

**With AWS credentials mounted:**
```json
{
  "mcpServers": {
    "healthlake": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-v", "~/.aws:/root/.aws",
        "-e", "AWS_PROFILE=your-profile",
        "-e", "MCP_LOG_LEVEL=INFO",
        "awslabs/healthlake-mcp-server"
      ]
    }
  }
}
```

**Read-Only Mode with Docker:**
```json
{
  "mcpServers": {
    "healthlake-readonly": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-e", "AWS_ACCESS_KEY_ID=your_key",
        "-e", "AWS_SECRET_ACCESS_KEY=your_secret",
        "-e", "AWS_REGION=us-east-1",
        "-e", "MCP_LOG_LEVEL=INFO",
        "awslabs/healthlake-mcp-server",
        "--readonly"
      ]
    }
  }
}
```

### Other MCP Clients

See `examples/mcp_config.json` for additional configuration examples.

[↑ Back to Table of Contents](#table-of-contents)

## Read-Only Mode

The server supports a read-only mode that prevents all mutating operations while still allowing read operations. This is useful for:

- **Safety**: Preventing accidental modifications in production environments
- **Testing**: Allowing safe exploration of FHIR resources without risk of changes
- **Auditing**: Running the server in environments where only read access should be allowed
- **Compliance**: Meeting security requirements for read-only access to healthcare data

### Enabling Read-Only Mode

Add the `--readonly` flag when starting the server:

```bash
# Using uvx
uvx awslabs.healthlake-mcp-server@latest --readonly

# Or if installed locally
python -m awslabs.healthlake_mcp_server.main --readonly
```

### Operations Available in Read-Only Mode

| Operation | Available | Description |
|-----------|-----------|-------------|
| `list_datastores` | ✅ | List all HealthLake datastores |
| `get_datastore_details` | ✅ | Get detailed datastore information |
| `read_fhir_resource` | ✅ | Retrieve specific FHIR resources |
| `search_fhir_resources` | ✅ | Advanced FHIR search operations |
| `patient_everything` | ✅ | Comprehensive patient record retrieval |
| `list_fhir_jobs` | ✅ | Monitor import/export job status |

### Operations Blocked in Read-Only Mode

| Operation | Blocked | Description |
|-----------|---------|-------------|
| `create_fhir_resource` | ❌ | Create new FHIR resources |
| `update_fhir_resource` | ❌ | Update existing FHIR resources |
| `delete_fhir_resource` | ❌ | Delete FHIR resources |
| `start_fhir_import_job` | ❌ | Start FHIR data import jobs |
| `start_fhir_export_job` | ❌ | Start FHIR data export jobs |

[↑ Back to Table of Contents](#table-of-contents)

## Available Tools

The server provides **11 comprehensive FHIR tools** organized into four categories:

### Datastore Management
- **`list_datastores`** - List all HealthLake datastores with optional status filtering
- **`get_datastore_details`** - Get detailed datastore information including endpoints and metadata

### FHIR Resource Operations (CRUD)
- **`create_fhir_resource`** - Create new FHIR resources with validation
- **`read_fhir_resource`** - Retrieve specific FHIR resources by ID
- **`update_fhir_resource`** - Update existing FHIR resources with versioning
- **`delete_fhir_resource`** - Delete FHIR resources from datastores

### Advanced Search
- **`search_fhir_resources`** - Advanced FHIR search with modifiers, chaining, includes, and pagination
- **`patient_everything`** - Comprehensive patient record retrieval using FHIR $patient-everything operation

### Job Management
- **`start_fhir_import_job`** - Start FHIR data import jobs from S3
- **`start_fhir_export_job`** - Start FHIR data export jobs to S3
- **`list_fhir_jobs`** - List and monitor import/export jobs with status filtering

### MCP Resources

The server automatically exposes HealthLake datastores as MCP resources, enabling:
- **Automatic discovery** of available datastores
- **No manual datastore ID entry** required
- **Status visibility** (ACTIVE, CREATING, etc.)
- **Metadata access** (creation date, endpoints, etc.)

[↑ Back to Table of Contents](#table-of-contents)

## Usage Examples

### Basic Resource Operations

```json
// Create a patient (datastore discovered automatically)
{
  "datastore_id": "discovered-from-resources",
  "resource_type": "Patient",
  "resource_data": {
    "resourceType": "Patient",
    "name": [{"family": "Smith", "given": ["John"]}],
    "gender": "male"
  }
}
```

### Advanced Search

```json
// Search with modifiers and includes
{
  "datastore_id": "discovered-from-resources",
  "resource_type": "Patient",
  "search_params": {
    "name:contains": "smith",
    "birthdate": "ge1990-01-01"
  },
  "include_params": ["Patient:general-practitioner"],
  "revinclude_params": ["Observation:subject"]
}
```

### Patient Everything

```json
// Get all resources for a patient
{
  "datastore_id": "discovered-from-resources",
  "patient_id": "patient-123",
  "start": "2023-01-01",
  "end": "2023-12-31"
}
```

[↑ Back to Table of Contents](#table-of-contents)

## Authentication

Configure AWS credentials using any of these methods:

1. **AWS CLI**: `aws configure`
2. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
3. **IAM roles** (for EC2/Lambda)
4. **AWS profiles**: Set `AWS_PROFILE` environment variable

### Required Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "healthlake:ListFHIRDatastores",
        "healthlake:DescribeFHIRDatastore",
        "healthlake:CreateResource",
        "healthlake:ReadResource",
        "healthlake:UpdateResource",
        "healthlake:DeleteResource",
        "healthlake:SearchWithGet",
        "healthlake:SearchWithPost",
        "healthlake:StartFHIRImportJob",
        "healthlake:StartFHIRExportJob",
        "healthlake:ListFHIRImportJobs",
        "healthlake:ListFHIRExportJobs"
      ],
      "Resource": "*"
    }
  ]
}
```

[↑ Back to Table of Contents](#table-of-contents)

## Error Handling

All tools return structured error responses:

```json
{
  "error": true,
  "type": "validation_error",
  "message": "Datastore ID must be 32 characters"
}
```

**Error Types:**
- `validation_error` - Invalid input parameters
- `not_found` - Resource or datastore not found
- `auth_error` - AWS credentials not configured
- `service_error` - AWS HealthLake service error
- `server_error` - Internal server error

[↑ Back to Table of Contents](#table-of-contents)

## Troubleshooting

### Common Issues

**"AWS credentials not configured"**
- Run `aws configure` or set environment variables
- Verify `AWS_REGION` is set correctly

**"Resource not found"**
- Ensure datastore exists and is ACTIVE
- Check datastore ID is correct (32 characters)
- Verify you have access to the datastore

**"Validation error"**
- Check required parameters are provided
- Ensure datastore ID format is correct
- Verify count parameters are within 1-100 range

### Debug Mode

Set environment variable for detailed logging:
```bash
export PYTHONPATH=.
export MCP_LOG_LEVEL=DEBUG
awslabs.healthlake-mcp-server
```

[↑ Back to Table of Contents](#table-of-contents)

## Development

### Local Development Setup

#### Option 1: Using uv (Recommended)

```bash
git clone <repository-url>
cd healthlake-mcp-server
uv sync --dev
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Option 2: Using pip/venv

```bash
git clone <repository-url>
cd healthlake-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

#### Option 3: Using conda

```bash
git clone <repository-url>
cd healthlake-mcp-server

# Create conda environment
conda create -n healthlake-mcp python=3.10
conda activate healthlake-mcp

# Install dependencies
pip install -e ".[dev]"
```

### Running the Server Locally

```bash
# After activating your virtual environment
python -m awslabs.healthlake_mcp_server.main

# Or using the installed script
awslabs.healthlake-mcp-server
```

### Development Workflow

```bash
# Run tests
poe test

# Run tests with coverage
poe test-cov

# Format code
poe format

# Lint code
poe lint

# Run all quality checks
poe check

# Clean build artifacts
poe clean

# Build package
poe build

# Run server
poe run
```

### Available Tasks

The project uses [Poethepoet](https://poethepoet.natn.io/) for task automation. Run `poe --help` to see all available tasks:

- **Testing**: `test`, `test-cov`
- **Code Quality**: `lint`, `format`, `check`, `security`
- **Build & Run**: `build`, `run`
- **Cleanup**: `clean`

### Development Workflow

```bash
# Run all checks
poe check
```

### IDE Setup

#### VS Code
1. Install Python extension
2. Select the virtual environment: `Ctrl+Shift+P` → "Python: Select Interpreter"
3. Choose `.venv/bin/python`

#### PyCharm
1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Select `.venv/bin/python`

### Testing

```bash
# Run unit tests (fast, no AWS dependencies)
poe test

# Run with coverage
poe test-cov

# Format code
poe format

# Lint code
poe lint
```

**Test Results**: 235 tests pass, 96% coverage

### Project Structure

```
awslabs/healthlake_mcp_server/
├── server.py           # MCP server with tool handlers
├── fhir_operations.py  # AWS HealthLake client operations
├── models.py          # Pydantic validation models
├── main.py            # Entry point
└── __init__.py        # Package initialization
```

[↑ Back to Table of Contents](#table-of-contents)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `poe test`
5. Format code: `poe format`
6. Submit a pull request

[↑ Back to Table of Contents](#table-of-contents)

## License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.

[↑ Back to Table of Contents](#table-of-contents)

## Support

For issues and questions:
- Check the troubleshooting section above
- Review AWS HealthLake documentation
- Open an issue in the repository

[↑ Back to Table of Contents](#table-of-contents)
