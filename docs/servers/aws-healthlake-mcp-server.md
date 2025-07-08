# AWS HealthLake MCP Server

The AWS HealthLake MCP Server provides tools for interacting with AWS HealthLake through the Model Context Protocol. It enables AI assistants to perform operations on AWS HealthLake resources, such as creating datastores, importing and exporting FHIR data, and managing tags.

## Available MCP Tools

### Datastore Operations
- `create_datastore` - Creates a new HealthLake datastore for storing FHIR data
- `delete_datastore` - Deletes a HealthLake datastore and all of its data
- `describe_datastore` - Returns detailed information about a specific datastore
- `list_datastores` - Returns a list of all datastores in your account with optional filtering

### Import/Export Operations
- `start_fhir_import_job` - Starts a job to import FHIR data into a datastore
- `start_fhir_export_job` - Starts a job to export FHIR data from a datastore
- `describe_fhir_import_job` - Returns detailed information about a specific import job
- `describe_fhir_export_job` - Returns detailed information about a specific export job
- `list_fhir_import_jobs` - Returns a list of import jobs for a datastore with optional filtering
- `list_fhir_export_jobs` - Returns a list of export jobs for a datastore with optional filtering

### Tagging Operations
- `tag_resource` - Adds tags to a HealthLake resource
- `untag_resource` - Removes tags from a HealthLake resource
- `list_tags_for_resource` - Lists all tags associated with a HealthLake resource

## Key Features

- **FHIR R4 Support**: Full support for FHIR R4 standard for healthcare data interoperability
- **Secure Data Storage**: Server-side encryption with AWS KMS integration
- **Identity Provider Integration**: Support for SMART on FHIR authorization
- **Bulk Operations**: Import and export large datasets efficiently
- **Comprehensive Monitoring**: Track job status and progress for all operations

## Installation

Add the MCP to your favorite agentic tools. (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.healthlake-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.healthlake-mcp-server@latest"],
      "env": {
        "HEALTHLAKE_MCP_READONLY": "true",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Examples

### Creating a Datastore

```python
# Create a basic FHIR R4 datastore
create_datastore(
    datastore_type_version="R4",
    datastore_name="my-healthcare-datastore"
)
```

### Starting an Import Job

```python
# Import FHIR data from S3
start_fhir_import_job(
    input_data_config={
        "S3Uri": "s3://my-bucket/fhir-data/"
    },
    job_output_data_config={
        "S3Configuration": {
            "S3Uri": "s3://my-bucket/import-output/",
            "KmsKeyId": "<your-kms-key-id>"
        }
    },
    datastore_id="1234567890abcdef1234567890abcdef",
    data_access_role_arn="<your-iam-role-arn>",
    job_name="my-import-job"
)
```

### Listing Datastores

```python
# List all datastores
list_datastores()

# List datastores with filtering
list_datastores(
    filter_dict={
        "DatastoreName": "my-datastore",
        "DatastoreStatus": "ACTIVE"
    }
)
```

## Security Considerations

- Always use IAM roles with least privilege access
- Enable server-side encryption for sensitive healthcare data
- Use VPC endpoints when possible to keep traffic within AWS network
- Regularly audit access logs and permissions
- Consider using SMART on FHIR for fine-grained authorization
