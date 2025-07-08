# AWS HealthLake MCP Server

The official MCP Server for interacting with AWS HealthLake

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

## Instructions

The AWS HealthLake MCP Server provides comprehensive tools for managing HealthLake datastores and FHIR data operations. Each tool maps directly to HealthLake API operations and supports all relevant parameters.

To use these tools, ensure you have proper AWS credentials configured with appropriate permissions for HealthLake operations. The server will automatically use credentials from environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN) or other standard AWS credential sources.

All tools support an optional `region_name` parameter to specify which AWS region to operate in. If not provided, it will use the AWS_REGION environment variable or default to 'us-west-2'.

### Key Features

- **FHIR R4 Support**: Full support for FHIR R4 standard for healthcare data interoperability
- **Secure Data Storage**: Server-side encryption with AWS KMS integration
- **Identity Provider Integration**: Support for SMART on FHIR authorization
- **Bulk Operations**: Import and export large datasets efficiently
- **Comprehensive Monitoring**: Track job status and progress for all operations

### Common Use Cases

1. **Healthcare Data Migration**: Import existing FHIR data from other systems
2. **Data Analytics**: Export FHIR data for analysis and reporting
3. **Compliance and Backup**: Create secure backups of healthcare data
4. **Integration**: Connect with other healthcare systems and applications

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS HealthLake services
   - Consider setting up Read-only permission if you don't want the LLM to modify any resources

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

or docker after a successful `docker build -t awslabs/healthlake-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.healthlake-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "awslabs/healthlake-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Environment Variables

- `HEALTHLAKE_MCP_READONLY`: Set to "true" to enable read-only mode (default: "false")
- `AWS_REGION`: AWS region to use (default: "us-west-2")
- `AWS_PROFILE`: AWS profile to use (default: "default")
- `FASTMCP_LOG_LEVEL`: Logging level (default: "ERROR")

## Required AWS Permissions

The following IAM permissions are required for full functionality:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "healthlake:CreateFHIRDatastore",
        "healthlake:DeleteFHIRDatastore",
        "healthlake:DescribeFHIRDatastore",
        "healthlake:ListFHIRDatastores",
        "healthlake:StartFHIRImportJob",
        "healthlake:StartFHIRExportJob",
        "healthlake:DescribeFHIRImportJob",
        "healthlake:DescribeFHIRExportJob",
        "healthlake:ListFHIRImportJobs",
        "healthlake:ListFHIRExportJobs",
        "healthlake:TagResource",
        "healthlake:UntagResource",
        "healthlake:ListTagsForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

For read-only access, remove the Create, Delete, Start, Tag, and Untag actions.

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

## Support

For issues and feature requests, please refer to the main MCP repository at https://github.com/awslabs/mcp
