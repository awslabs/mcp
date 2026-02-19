# AWS HealthImaging MCP Server

## Overview

The AWS HealthImaging MCP Server enables AI assistants to interact with AWS HealthImaging services through the Model Context Protocol (MCP). It provides comprehensive medical imaging data lifecycle management with **39 specialized tools** for DICOM operations, datastore management, and advanced medical imaging workflows.

This server acts as a bridge between AI assistants and AWS HealthImaging, allowing you to search, retrieve, and manage medical imaging data while maintaining proper security controls and HIPAA compliance considerations.

## Prerequisites

- You must have an AWS account with HealthImaging access and credentials properly configured. Please refer to the official documentation [here ↗](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) for guidance. We recommend configuring your credentials using the `AWS_PROFILE` environment variable. If not specified, the system follows boto3's default credential selection order.
- Ensure you have Python 3.10 or newer installed. You can download it from the [official Python website](https://www.python.org/downloads/) or use a version manager such as [pyenv](https://github.com/pyenv/pyenv).
- (Optional) Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for faster dependency management and improved Python environment handling.

## 📦 Installation Methods

Choose the installation method that best fits your workflow and get started with your favorite assistant with MCP support, like Kiro, Cursor or Cline.

| Cursor | VS Code | Kiro |
|:------:|:-------:|:----:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.healthimaging-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuaGVhbHRoaW1hZ2luZy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthImaging%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthimaging-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22type%22%3A%22stdio%22%7D) | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.healthimaging-mcp-server&config=%7B%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22awslabs.healthimaging-mcp-server%40latest%22%5D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D) |

### ⚡ Using uv

Add the following configuration to your MCP client config file (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

**For Linux/MacOS users:**

```json
{
  "mcpServers": {
    "awslabs.healthimaging-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.healthimaging-mcp-server@latest"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**For Windows users:**

```json
{
  "mcpServers": {
    "awslabs.healthimaging-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.healthimaging-mcp-server@latest",
        "awslabs.healthimaging-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 🐍 Using Python (pip)

> [!TIP]
> It's recommended to use a virtual environment because the AWS CLI version of the MCP server might not match the locally installed one
> and can cause it to be downgraded. In the MCP client config file you can change `"command"` to the path of the python executable in your
> virtual environment (e.g., `"command": "/workspace/project/.venv/bin/python"`).

**Step 1: Install the package**
```bash
pip install awslabs.healthimaging-mcp-server
```

**Step 2: Configure your MCP client**
Add the following configuration to your MCP client config file (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.healthimaging-mcp-server": {
      "command": "python",
      "args": [
        "-m",
        "awslabs.healthimaging_mcp_server.server"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 🐳 Using Docker

You can isolate the MCP server by running it in a Docker container.

```json
{
  "mcpServers": {
    "awslabs.healthimaging-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_REGION=us-east-1",
        "--volume",
        "/full/path/to/.aws:/app/.aws",
        "awslabs/healthimaging-mcp-server:latest"
      ],
      "env": {}
    }
  }
}
```

### 🔧 Using Cloned Repository

For detailed instructions on setting up your local development environment and running the server from source, please see the [Development](#development) section below.

## 🚀 Quick Start

Once configured, you can ask your AI assistant questions such as:

- **"List all my HealthImaging datastores"**
- **"Search for CT scans for patient PATIENT123"**
- **"Get DICOM metadata for image set abc123"**

## Features

- **Comprehensive HealthImaging Support**: 39 specialized tools covering all aspects of medical imaging data lifecycle management
- **21 Standard AWS API Operations**: Full AWS HealthImaging API coverage including datastore management, import/export jobs, image sets, metadata, and resource tagging
- **18 Advanced DICOM Operations**: Specialized medical imaging workflows including patient/study/series level operations, bulk operations, and DICOM hierarchy management
- **GDPR Compliance Support**: Patient data removal and study deletion tools support "right to be forgotten/right to erasure" objectives
- **Enhanced Search Capabilities**: Patient-focused, study-focused, and series-focused searches with DICOM-aware filtering
- **Bulk Operations**: Efficient large-scale metadata updates and deletions with built-in safety limits
- **MCP Resources**: Automatic datastore discovery eliminates need for manual datastore ID entry
- **Security-First Design**: Built with healthcare security requirements in mind, supporting HIPAA compliance considerations

## Available MCP Tools

The server provides **39 comprehensive HealthImaging tools** organized into eight categories:
### Datastore Management (4 tools)
- **`create_datastore`** - Create new HealthImaging datastores with optional KMS encryption
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

## Usage Examples

### Basic Operations

List datastores (datastore discovered automatically)

```json
{
  "status": "ACTIVE"
}
```

### Advanced Search

Search image sets with DICOM criteria

```json
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

Get detailed DICOM metadata

```json
{
  "datastore_id": "discovered-from-resources",
  "image_set_id": "image-set-123",
  "version_id": "1"
}
```

## Authentication

Configure AWS credentials using any of these methods:

1. **AWS CLI**: `aws configure`
2. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
3. **IAM roles** (for EC2/Lambda)
4. **AWS profiles**: Set `AWS_PROFILE` environment variable

### Required Permissions

The server requires specific IAM permissions for HealthImaging operations. Here's a comprehensive policy:

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

### Security Best Practices

- **Principle of Least Privilege**: Create custom policies tailored to your specific use case rather than using broad permissions
- **Minimal Permissions**: Start with minimal permissions and gradually add access as needed
- **MFA Requirements**: Consider requiring multi-factor authentication for sensitive operations
- **Regular Monitoring**: Monitor AWS CloudTrail logs to track actions performed by the MCP server
- **HIPAA Compliance**: Ensure your AWS account and HealthImaging setup meet HIPAA requirements for healthcare data

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

## Development

### Local Development Setup

#### Prerequisites

- Python 3.10 or higher
- Git
- AWS account with HealthImaging access
- Code editor (VS Code recommended)

#### Setup Instructions

**Option 1: Using uv (Recommended)**

```bash
git clone <repository-url>
cd healthimaging-mcp-server
uv sync --dev
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Option 2: Using pip/venv**

```bash
git clone <repository-url>
cd healthimaging-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

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

### Project Structure

```
awslabs/healthimaging_mcp_server/
├── server.py                    # MCP server with tool handlers
├── healthimaging_operations.py  # AWS HealthImaging client operations
├── models.py                   # Pydantic validation models
├── main.py                     # Entry point
└── __init__.py                 # Package initialization
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `pytest tests/ -v`
5. Format code: `ruff format awslabs/ tests/`
6. Submit a pull request

## License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.

## Disclaimer

This AWS HealthImaging MCP Server package is provided "as is" without warranty of any kind, express or implied, and is intended for development, testing, and evaluation purposes only. We do not provide any guarantee on the quality, performance, or reliability of this package.

Users of this package are solely responsible for implementing proper security controls and MUST use AWS Identity and Access Management (IAM) to manage access to AWS resources. You are responsible for configuring appropriate IAM policies, roles, and permissions, and any security vulnerabilities resulting from improper IAM configuration are your sole responsibility.

When working with medical imaging data, ensure compliance with applicable healthcare regulations such as HIPAA, and implement appropriate safeguards for protected health information (PHI). By using this package, you acknowledge that you have read and understood this disclaimer and agree to use the package at your own risk.
