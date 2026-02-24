# AWS HealthImaging MCP Server

A comprehensive Model Context Protocol (MCP) server for AWS HealthImaging operations. Provides **39 tools** for complete medical imaging data lifecycle management with automatic datastore discovery.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Available Tools](#available-tools)
  - [Datastore Management](#datastore-management)
  - [Image Set Operations](#image-set-operations)
  - [DICOM Job Management](#dicom-job-management)
  - [Metadata & Frame Operations](#metadata--frame-operations)
  - [Tagging Operations](#tagging-operations)
  - [Advanced DICOM Operations](#advanced-dicom-operations)
  - [Bulk Operations](#bulk-operations)
  - [DICOM Hierarchy Operations](#dicom-hierarchy-operations)
- [Usage Examples](#usage-examples)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Features

- **39 Comprehensive HealthImaging Tools**: Complete medical imaging data lifecycle management
- **Delete Operations**: Patient data removal and study deletion tools support "right to be forgotten/right to erasure" objectives
- **Automatic Datastore Discovery**: Seamlessly find and work with existing datastores
- **DICOM Metadata Operations**: Extract and analyze medical imaging metadata
- **Image Frame Management**: Retrieve and process individual image frames
- **Search Capabilities**: Advanced search across image sets and studies
- **Bulk Operations**: Efficient patient metadata updates and deletions
- **DICOM Hierarchy**: Manipulate series and instances within image sets
- **Error Handling**: Comprehensive error handling with detailed feedback
- **Type Safety**: Full type annotations and validation

## Quick Start

### Option 1: uvx (Recommended)

```bash
uvx awslabs.healthimaging-mcp-server@latest
```

### Option 2: uv install

```bash
uv add awslabs.healthimaging-mcp-server
```

### Option 3: Docker

```bash
docker run -it --rm \
  -e AWS_REGION=us-east-1 \
  -e AWS_PROFILE=your-profile \
  -v ~/.aws:/root/.aws:ro \
  public.ecr.aws/awslabs/healthimaging-mcp-server:latest
```

## MCP Client Configuration

### Amazon Q Developer CLI

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile",
        "FASTMCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

### Other MCP Clients

For other MCP clients like Claude Desktop, add this to your configuration:

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile"
      }
    }
  }
}
```

## Available Tools

### Datastore Management
- `list_datastores` - List all HealthImaging datastores with optional filtering
- `get_datastore` - Get detailed information about a specific datastore
- `create_datastore` - Create a new HealthImaging datastore
- `delete_datastore` - Delete a datastore (with safety checks)

### Image Set Operations
- `search_image_sets` - Advanced search across image sets with DICOM criteria
- `get_image_set` - Get detailed information about a specific image set
- `get_image_set_metadata` - Retrieve complete DICOM metadata for an image set
- `list_image_set_versions` - List all versions of an image set
- `update_image_set_metadata` - Update DICOM metadata for an image set
- `delete_image_set` - Delete an image set (with safety checks)
- `copy_image_set` - Copy an image set to another datastore

### DICOM Job Management
- `start_dicom_import_job` - Start a new DICOM import job from S3
- `get_dicom_import_job` - Get status and details of an import job
- `list_dicom_import_jobs` - List all DICOM import jobs with filtering
- `start_dicom_export_job` - Start a new DICOM export job to S3
- `get_dicom_export_job` - Get status and details of an export job
- `list_dicom_export_jobs` - List all DICOM export jobs with filtering

### Metadata & Frame Operations
- `get_image_frame` - Retrieve individual image frames with pixel data

### Tagging Operations
- `list_tags_for_resource` - List all tags for a HealthImaging resource
- `tag_resource` - Add tags to a HealthImaging resource
- `untag_resource` - Remove tags from a HealthImaging resource

### Advanced DICOM Operations
- `delete_patient_studies` - Delete all studies for a specific patient (GDPR compliance)
- `delete_study` - Delete all image sets for a specific study
- `search_by_patient_id` - Search for all image sets by patient ID
- `search_by_study_uid` - Search for image sets by study instance UID
- `search_by_series_uid` - Search for image sets by series instance UID
- `get_patient_studies` - Get all studies for a specific patient
- `get_patient_series` - Get all series for a specific patient
- `get_study_primary_image_sets` - Get primary image sets for a study
- `delete_series_by_uid` - Delete a specific series by series instance UID
- `get_series_primary_image_set` - Get the primary image set for a series
- `get_patient_dicomweb_studies` - Get DICOMweb study-level information for a patient
- `delete_instance_in_study` - Delete a specific instance within a study
- `delete_instance_in_series` - Delete a specific instance within a series
- `update_patient_study_metadata` - Update patient and study metadata for an entire study

### Bulk Operations
- `bulk_update_patient_metadata` - Update patient metadata across all studies for a patient
- `bulk_delete_by_criteria` - Delete multiple image sets matching specified criteria

### DICOM Hierarchy Operations
- `remove_series_from_image_set` - Remove a specific series from an image set
- `remove_instance_from_image_set` - Remove a specific instance from an image set

## Usage Examples

### Basic Operations

```python
# List all datastores
datastores = await list_datastores()

# Get specific datastore
datastore = await get_datastore(datastore_id="12345678901234567890123456789012")

# Search for image sets
results = await search_image_sets(
    datastore_id="12345678901234567890123456789012",
    search_criteria={
        "filters": [
            {
                "values": [{"DICOMPatientId": "PATIENT123"}],
                "operator": "EQUAL"
            }
        ]
    }
)
```

### Advanced Search

```python
# Complex search with multiple filters
results = await search_image_sets(
    datastore_id="12345678901234567890123456789012",
    search_criteria={
        "filters": [
            {
                "values": [{"DICOMStudyDate": "20240101"}],
                "operator": "EQUAL"
            },
            {
                "values": [{"DICOMModality": "CT"}],
                "operator": "EQUAL"
            }
        ]
    },
    max_results=50
)
```

### DICOM Metadata

```python
# Get DICOM metadata for an image set
metadata = await get_image_set_metadata(
    datastore_id="12345678901234567890123456789012",
    image_set_id="98765432109876543210987654321098"
)

# Get specific image frame
frame = await get_image_frame(
    datastore_id="12345678901234567890123456789012",
    image_set_id="98765432109876543210987654321098",
    image_frame_information={
        "imageFrameId": "frame123"
    }
)
```

## Authentication

### Required Permissions

Your AWS credentials need the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "medical-imaging:ListDatastores",
                "medical-imaging:GetDatastore",
                "medical-imaging:CreateDatastore",
                "medical-imaging:DeleteDatastore",
                "medical-imaging:ListImageSets",
                "medical-imaging:GetImageSet",
                "medical-imaging:SearchImageSets",
                "medical-imaging:CopyImageSet",
                "medical-imaging:UpdateImageSetMetadata",
                "medical-imaging:DeleteImageSet",
                "medical-imaging:GetImageFrame",
                "medical-imaging:GetImageSetMetadata",
                "medical-imaging:ListDICOMImportJobs",
                "medical-imaging:GetDICOMImportJob",
                "medical-imaging:StartDICOMImportJob"
            ],
            "Resource": "*"
        }
    ]
}
```

## Error Handling

The server provides comprehensive error handling:

- **Validation Errors**: Input validation with detailed error messages
- **AWS Service Errors**: Proper handling of AWS API errors
- **Resource Not Found**: Clear messages for missing resources
- **Permission Errors**: Helpful guidance for access issues
- **Rate Limiting**: Automatic retry with exponential backoff

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify AWS credentials are configured
   - Check IAM permissions
   - Ensure correct AWS region

2. **Resource Not Found**
   - Verify datastore/image set IDs
   - Check resource exists in specified region
   - Confirm access permissions

3. **Import Job Failures**
   - Check S3 bucket permissions
   - Verify DICOM file format
   - Review import job logs

### Debug Mode

Enable debug logging:

```bash
export FASTMCP_LOG_LEVEL=DEBUG
uvx awslabs.healthimaging-mcp-server@latest
```

## Development

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/awslabs/mcp-server-collection.git
cd mcp-server-collection/src/healthimaging-mcp-server
```

2. Install dependencies:
```bash
uv sync --dev
```

3. Run tests:
```bash
uv run python -m pytest tests/ -v
```

4. Run the server locally:
```bash
uv run python -m awslabs.healthimaging_mcp_server
```

### Testing

The server includes comprehensive tests with 99% coverage:

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run with coverage
uv run python -m pytest tests/ -v --cov=awslabs.healthimaging_mcp_server --cov-report=html
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/awslabs/mcp-server-collection/blob/main/CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/awslabs/mcp-server-collection/blob/main/LICENSE) file for details.

## Support

For support, please:
1. Check the [troubleshooting section](#troubleshooting)
2. Review [AWS HealthImaging documentation](https://docs.aws.amazon.com/healthimaging/)
3. Open an issue in the [GitHub repository](https://github.com/awslabs/mcp-server-collection/issues)
