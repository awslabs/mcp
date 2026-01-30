# AWS HealthImaging MCP Server

A comprehensive Model Context Protocol (MCP) server for AWS HealthImaging operations. Provides **21 tools** for complete medical imaging data lifecycle management with automatic datastore discovery.

## Features

- **21 Comprehensive HealthImaging Tools**: Complete medical imaging data lifecycle management
- **Delete Operations**: Patient data removal and study deletion tools support "right to be forgotten/right to erasure" objectives
- **Automatic Datastore Discovery**: Seamlessly find and work with existing datastores
- **DICOM Metadata Operations**: Extract and analyze medical imaging metadata
- **Image Frame Management**: Retrieve and process individual image frames
- **Search Capabilities**: Advanced search across image sets and studies
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
- `list_datastores` - List all HealthImaging datastores
- `get_datastore` - Get detailed datastore information
- `create_datastore` - Create new datastore
- `delete_datastore` - Delete datastore (with safety checks)

### Image Set Operations
- `list_image_sets` - List image sets with filtering
- `get_image_set` - Get detailed image set information
- `search_image_sets` - Advanced search across image sets
- `copy_image_set` - Copy image sets between datastores
- `update_image_set_metadata` - Update image set metadata
- `delete_image_set` - Delete image sets (with safety checks)

### Image Frame Operations
- `get_image_frame` - Retrieve individual image frames
- `get_image_set_metadata` - Extract DICOM metadata
- `list_dicom_import_jobs` - List import job status
- `get_dicom_import_job` - Get import job details
- `start_dicom_import_job` - Start new import jobs

### MCP Resources
- `list_mcp_resources` - List available MCP resources
- `get_mcp_resource` - Get specific resource details

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
