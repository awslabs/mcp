# HealthImaging MCP Server

A comprehensive Model Context Protocol (MCP) server for AWS HealthImaging operations. Provides **39 tools** for complete medical imaging data lifecycle management with automatic datastore discovery and advanced DICOM operations.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
  - [Option 1: uvx (Recommended)](#option-1-uvx-recommended)
  - [Option 2: uv install](#option-2-uv-install)
  - [Option 3: Docker](#option-3-docker)
- [Docker](#docker)
  - [Quick Start with Docker](#quick-start-with-docker)
  - [Building Locally](#building-locally)
  - [MCP Client Configuration for Docker](#mcp-client-configuration-for-docker)
  - [Environment Variables](#environment-variables)
- [Prerequisites](#prerequisites)
- [MCP Client Configuration](#mcp-client-configuration)
  - [Amazon Q Developer CLI](#amazon-q-developer-cli)
  - [Other MCP Clients](#other-mcp-clients)
- [Available Tools](#available-tools)
  - [Datastore Management](#datastore-management)
  - [Image Set Operations](#image-set-operations)
  - [Image Frame Operations](#image-frame-operations)
  - [MCP Resources](#mcp-resources)
- [Usage Examples](#usage-examples)
  - [Basic Operations](#basic-operations)
  - [Advanced Search](#advanced-search)
  - [DICOM Metadata](#dicom-metadata)
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

- **39 Comprehensive HealthImaging Tools**: Complete medical imaging data lifecycle management
- **21 Standard AWS API Operations**: Full AWS HealthImaging API coverage including datastore management, import/export jobs, image sets, metadata, and resource tagging
- **18 Advanced DICOM Operations**: Specialized medical imaging workflows including patient/study/series level operations, bulk operations, and DICOM hierarchy management
- **Delete Operations**: Patient data removal, study deletion, supports compliance with "right to be forgotten/right to erasure" GDPR objectives
- **Metadata Updates**: Patient corrections, study modifications, series/instance management
- **Enhanced Search**: Patient-focused, study-focused, and series-focused searches with DICOM-aware filtering
- **Data Analysis**: Patient studies overview, series analysis, primary image set filtering, DICOMweb integration
- **Bulk Operations**: Efficient large-scale metadata updates and deletions with safety limits
- **DICOM Hierarchy Operations**: Series and instance removal with deep DICOM knowledge
- **Import/Export Jobs**: Complete DICOM data import and export workflow management
- **MCP Resources**: Automatic datastore discovery - no manual datastore IDs needed
- **DICOM Metadata**: Access detailed medical imaging metadata with base64 encoding for binary data
- **AWS Integration**: SigV4 authentication with automatic credential handling
- **Error Handling**: Structured error responses with specific error types
- **Docker Support**: Production-ready containerization
- **Type Safety**: Comprehensive Pydantic models for all operations

## Quick Start

Choose your preferred installation method:

### Option 1: uvx (Recommended)

```bash
# Install and run latest version automatically
uvx awslabs.healthimaging-mcp-server@latest
```

### Option 2: uv install

```bash
uv tool install awslabs.healthimaging-mcp-server
awslabs.healthimaging-mcp-server
```

### Option 3: Docker

```bash
# Build and run with Docker
docker build -t healthimaging-mcp-server .
docker run -e AWS_ACCESS_KEY_ID=xxx -e AWS_SECRET_ACCESS_KEY=yyy healthimaging-mcp-server
```

[↑ Back to Table of Contents](#table-of-contents)

## Docker

### Quick Start with Docker

```bash
# Run with environment variables
docker run -e AWS_ACCESS_KEY_ID=your_key -e AWS_SECRET_ACCESS_KEY=your_secret -e AWS_REGION=us-east-1 awslabs/healthimaging-mcp-server

# Run with AWS profile (mount credentials)
docker run -v ~/.aws:/root/.aws -e AWS_PROFILE=your-profile awslabs/healthimaging-mcp-server
```

### Building Locally

```bash
# Build the image
docker build -t healthimaging-mcp-server .

# Run locally built image
docker run -e AWS_ACCESS_KEY_ID=your_key -e AWS_SECRET_ACCESS_KEY=your_secret healthimaging-mcp-server
```

### MCP Client Configuration for Docker

**Amazon Q Developer CLI:**
```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-e", "AWS_ACCESS_KEY_ID=your_key",
        "-e", "AWS_SECRET_ACCESS_KEY=your_secret",
        "-e", "AWS_REGION=us-east-1",
        "awslabs/healthimaging-mcp-server"
      ]
    }
  }
}
```

**With AWS credentials mounted:**
```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-v", "~/.aws:/root/.aws",
        "-e", "AWS_PROFILE=your-profile",
        "awslabs/healthimaging-mcp-server"
      ]
    }
  }
}
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes* |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes* |
| `AWS_REGION` | AWS region | Yes |
| `AWS_PROFILE` | AWS profile name | No |

*Not required if using IAM roles or mounted credentials

[↑ Back to Table of Contents](#table-of-contents)

## Prerequisites

- **Python 3.10+** (required by MCP framework)
- **AWS credentials** configured
- **AWS HealthImaging access** with appropriate permissions

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
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile-name"
      }
    }
  }
}
```

### Other MCP Clients

See `examples/mcp_config.json` for additional configuration examples.

[↑ Back to Table of Contents](#table-of-contents)

## Available Tools

The server provides **39 comprehensive HealthImaging tools** organized into eight categories:

### Datastore Management (4 tools)
- **`create_datastore`** - Create new HealthImaging datastores with optional KMS encryption
- **`delete_datastore`** - Delete HealthImaging datastores (IRREVERSIBLE)
- **`get_datastore`** - Get detailed datastore information including endpoints and metadata
- **`list_datastores`** - List all HealthImaging datastores with optional status filtering

### DICOM Import/Export Jobs (6 tools)
- **`start_dicom_import_job`** - Start DICOM import jobs from S3 to HealthImaging
- **`get_dicom_import_job`** - Get import job status and details
- **`list_dicom_import_jobs`** - List import jobs with status filtering
- **`start_dicom_export_job`** - Start DICOM export jobs from HealthImaging to S3
- **`get_dicom_export_job`** - Get export job status and details
- **`list_dicom_export_jobs`** - List export jobs with status filtering

### Image Set Operations (8 tools)
- **`search_image_sets`** - Advanced image set search with DICOM criteria and pagination
- **`get_image_set`** - Retrieve specific image set metadata and status
- **`get_image_set_metadata`** - Get detailed DICOM metadata with base64 encoding
- **`list_image_set_versions`** - List all versions of an image set
- **`update_image_set_metadata`** - Update DICOM metadata (patient corrections, study modifications)
- **`delete_image_set`** - Delete individual image sets (IRREVERSIBLE)
- **`copy_image_set`** - Copy image sets between datastores or within datastore
- **`get_image_frame`** - Get specific image frames with base64 encoding

### Resource Tagging (3 tools)
- **`list_tags_for_resource`** - List tags for HealthImaging resources
- **`tag_resource`** - Add tags to HealthImaging resources
- **`untag_resource`** - Remove tags from HealthImaging resources

### Enhanced Search Operations (3 tools)
- **`search_by_patient_id`** - Patient-focused search with study/series analysis
- **`search_by_study_uid`** - Study-focused search with primary image set filtering
- **`search_by_series_uid`** - Series-focused search across image sets

### Data Analysis Operations (8 tools)
- **`get_patient_studies`** - Get comprehensive study-level DICOM metadata for patients
- **`get_patient_series`** - Get all series UIDs for patient-level analysis
- **`get_study_primary_image_sets`** - Get primary image sets for studies (avoid duplicates)
- **`delete_patient_studies`** - Delete all studies for a patient (supports compliance with "right to be forgotten/right to erasure" GDPR objectives)
- **`delete_study`** - Delete entire studies by Study Instance UID
- **`delete_series_by_uid`** - Delete series using metadata updates
- **`get_series_primary_image_set`** - Get primary image set for series
- **`get_patient_dicomweb_studies`** - Get DICOMweb study-level information
- **`delete_instance_in_study`** - Delete specific instances in studies
- **`delete_instance_in_series`** - Delete specific instances in series
- **`update_patient_study_metadata`** - Update Patient/Study metadata for entire studies

### Bulk Operations (2 tools)
- **`bulk_update_patient_metadata`** - Update patient metadata across multiple studies with safety checks
- **`bulk_delete_by_criteria`** - Delete multiple image sets by search criteria with safety limits

### DICOM Hierarchy Operations (2 tools)
- **`remove_series_from_image_set`** - Remove specific series from image sets using DICOM hierarchy
- **`remove_instance_from_image_set`** - Remove specific instances from image sets using DICOM hierarchy

### MCP Resources

The server automatically exposes HealthImaging datastores as MCP resources, enabling:
- **Automatic discovery** of available datastores
- **No manual datastore ID entry** required
- **Status visibility** (ACTIVE, CREATING, etc.)
- **Metadata access** (creation date, endpoints, etc.)

[↑ Back to Table of Contents](#table-of-contents)

## Usage Examples

### Basic Operations

```json
// List datastores (datastore discovered automatically)
{
  "status": "ACTIVE"
}
```

### Advanced Search

```json
// Search image sets with DICOM criteria
{
  "datastore_id": "discovered-from-resources",
  "search_criteria": {
    "filters": [
      {
        "values": [{"DICOMPatientId": "PATIENT123"}],
        "operator": "EQUAL"
      }
    ]
  },
  "max_results": 50
}
```

### DICOM Metadata

```json
// Get detailed DICOM metadata
{
  "datastore_id": "discovered-from-resources",
  "image_set_id": "image-set-123",
  "version_id": "1"
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
        "medical-imaging:CreateDatastore",
        "medical-imaging:DeleteDatastore",
        "medical-imaging:GetDatastore",
        "medical-imaging:ListDatastores",
        "medical-imaging:StartDICOMImportJob",
        "medical-imaging:GetDICOMImportJob",
        "medical-imaging:ListDICOMImportJobs",
        "medical-imaging:StartDICOMExportJob",
        "medical-imaging:GetDICOMExportJob",
        "medical-imaging:ListDICOMExportJobs",
        "medical-imaging:SearchImageSets",
        "medical-imaging:GetImageSet",
        "medical-imaging:GetImageSetMetadata",
        "medical-imaging:GetImageFrame",
        "medical-imaging:ListImageSetVersions",
        "medical-imaging:UpdateImageSetMetadata",
        "medical-imaging:DeleteImageSet",
        "medical-imaging:CopyImageSet",
        "medical-imaging:ListTagsForResource",
        "medical-imaging:TagResource",
        "medical-imaging:UntagResource"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-dicom-bucket/*",
        "arn:aws:s3:::your-dicom-bucket"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/*"
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
- `service_error` - AWS HealthImaging service error
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
export AWS_LOG_LEVEL=DEBUG
awslabs.healthimaging-mcp-server
```

[↑ Back to Table of Contents](#table-of-contents)

## Development

### Local Development Setup

#### Option 1: Using uv (Recommended)

```bash
git clone <repository-url>
cd healthimaging-mcp-server
uv sync --dev
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Option 2: Using pip/venv

```bash
git clone <repository-url>
cd healthimaging-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

#### Option 3: Using conda

```bash
git clone <repository-url>
cd healthimaging-mcp-server

# Create conda environment
conda create -n healthimaging-mcp python=3.10
conda activate healthimaging-mcp

# Install dependencies
pip install -e ".[dev]"
```

### Running the Server Locally

```bash
# After activating your virtual environment
python -m awslabs.healthimaging_mcp_server.main

# Or using the installed script
awslabs.healthimaging-mcp-server
```

### Development Workflow

```bash
# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=awslabs/healthimaging_mcp_server --cov-report=html

# Format code
ruff format awslabs/ tests/

# Lint code
ruff check awslabs/ tests/
pyright awslabs/

# Run all checks
pre-commit run --all-files
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
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=awslabs/healthimaging_mcp_server --cov-report=html

# Format code
ruff format awslabs/ tests/

# Lint code
ruff check awslabs/ tests/
pyright awslabs/

# Run all checks (recommended)
pre-commit run --all-files
```

**Test Results**: All 5 tests pass successfully, covering:
- Tool handler functionality
- Response formatting
- Input validation
- Server initialization
- Error handling

### Project Structure

```
awslabs/healthimaging_mcp_server/
├── server.py                    # MCP server with tool handlers
├── healthimaging_operations.py  # AWS HealthImaging client operations
├── models.py                   # Pydantic validation models
├── main.py                     # Entry point
└── __init__.py                 # Package initialization
```

[↑ Back to Table of Contents](#table-of-contents)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `pytest tests/ -v`
5. Format code: `ruff format awslabs/ tests/`
6. Submit a pull request

[↑ Back to Table of Contents](#table-of-contents)

## License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.

[↑ Back to Table of Contents](#table-of-contents)

## Support

For issues and questions:
- Check the troubleshooting section above
- Review AWS HealthImaging documentation
- Open an issue in the repository

[↑ Back to Table of Contents](#table-of-contents)
