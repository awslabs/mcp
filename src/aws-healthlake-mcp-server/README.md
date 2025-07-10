# AWS HealthLake MCP Server

The official MCP Server for interacting with AWS HealthLake

## Available MCP Tools

### Datastore Operations
- `create_datastore` - Creates a new HealthLake datastore for storing FHIR data
- `delete_datastore` - Deletes a HealthLake datastore and all of its data
- `describe_datastore` - Returns detailed information about a specific datastore
- `list_datastores` - Returns a list of all datastores in your account with optional filtering
- `get_datastore_capabilities` - Get the FHIR capabilities statement for a datastore

### FHIR CRUD Operations
- `read_fhir_resource` - Retrieves a specific FHIR resource by ID with optional version support
- `search_fhir_resources` - Searches for FHIR resources based on query parameters
- `search_fhir_resources_advanced` - Advanced search with include, revinclude, and sort parameters
- `search_all_resources` - Search across all resource types in a datastore
- `create_fhir_resource` - Creates a new FHIR resource with conditional create support
- `update_fhir_resource` - Updates an existing FHIR resource with optimistic concurrency control
- `patch_fhir_resource` - Patch a FHIR resource using JSON Patch or FHIRPath operations
- `delete_fhir_resource` - Deletes a FHIR resource with conditional delete support
- `get_fhir_resource_history` - Get the version history of a FHIR resource with filtering
- `get_fhir_resource_compartment` - Get resources from a FHIR compartment (e.g., Patient compartment)

### FHIR Bundle and Batch Operations
- `create_fhir_bundle` - Create a FHIR Bundle with multiple resources for batch processing

### FHIR Resource Templates and Validation
- `validate_fhir_resource` - Validate a FHIR resource structure and provide feedback
- `validate_fhir_resource_against_profile` - Validate a FHIR resource against a specific profile
- `create_patient_template` - Create a FHIR Patient resource template with common fields
- `create_observation_template` - Create a FHIR Observation resource template

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
- **Enhanced FHIR API**: Direct FHIR resource access with proper HealthLake FHIR API implementation
- **Advanced Search**: Support for _include, _revinclude, and _sort parameters
- **Bundle Operations**: Create and process FHIR Bundles for batch operations
- **Resource Templates**: Pre-built templates for common FHIR resources
- **Validation**: Built-in FHIR resource validation and profile-based validation
- **Version History**: Access to resource version history and capabilities
- **Optimistic Concurrency**: Support for If-Match headers for safe updates
- **Conditional Operations**: Support for conditional create, update, and delete
- **Compartment Search**: Search within FHIR compartments (e.g., Patient compartment)
- **Patch Operations**: Support for JSON Patch and FHIRPath patch operations
- **Error Handling**: Comprehensive FHIR OperationOutcome error handling

### Common Use Cases

1. **Healthcare Data Migration**: Import existing FHIR data from other systems
2. **Data Analytics**: Export FHIR data for analysis and reporting
3. **Compliance and Backup**: Create secure backups of healthcare data
4. **Integration**: Connect with other healthcare systems and applications
5. **Patient Record Management**: Create, read, update, and delete individual patient records
6. **Batch Processing**: Process multiple FHIR resources in a single transaction
7. **Data Validation**: Validate FHIR resources before storing them
8. **Template-based Creation**: Use templates to create standardized FHIR resources

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
        "healthlake:ListTagsForResource",
        "healthlake:ReadResource",
        "healthlake:SearchWithGet",
        "healthlake:SearchWithPost",
        "healthlake:CreateResource",
        "healthlake:UpdateResource",
        "healthlake:DeleteResource"
      ],
      "Resource": "*"
    }
  ]
}
```

For read-only access, remove the Create, Delete, Start, Tag, Untag, CreateResource, UpdateResource, and DeleteResource actions.

## Examples

### Creating a Datastore

```python
# Create a basic FHIR R4 datastore
create_datastore(
    datastore_type_version="R4",
    datastore_name="my-healthcare-datastore"
)
```

### Working with FHIR Resources

```python
# Retrieve a patient by ID
patient = read_fhir_resource(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    resource_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b"
)

# Retrieve a specific version of a patient
patient_v2 = read_fhir_resource(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    resource_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b",
    version_id="2"
)

# Search for patients by name
patients = search_fhir_resources(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    query_parameters={"name": "Smith"}
)

# Advanced search with includes
patients_with_observations = search_fhir_resources_advanced(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    search_parameters={"name": "Smith"},
    include_parameters=["Patient:general-practitioner"],
    sort_parameters=["family", "given"],
    count=10
)

# Search across all resource types
all_resources = search_all_resources(
    datastore_id="1234567890abcdef1234567890abcdef",
    query_parameters={"_lastUpdated": "gt2023-01-01"},
    count=50
)

# Create a new patient using template
patient_template = create_patient_template(
    family_name="Doe",
    given_names=["John", "Michael"],
    gender="male",
    birth_date="1970-01-01",
    identifier_system="http://hospital.example.org/mrn",
    identifier_value="MRN123456",
    phone="+1-555-123-4567",
    email="john.doe@example.com"
)

# Validate the patient resource
validation_result = validate_fhir_resource(patient_template, "Patient")
if validation_result["valid"]:
    # Create the patient with conditional create to prevent duplicates
    new_patient = create_fhir_resource(
        datastore_id="1234567890abcdef1234567890abcdef",
        resource_type="Patient",
        resource_data=patient_template,
        if_none_exist="identifier=http://hospital.example.org/mrn|MRN123456"
    )

# Create an observation using template
observation_template = create_observation_template(
    patient_reference="Patient/04c704c4-5d2d-4308-9c33-1690a6e47a6b",
    code_system="http://loinc.org",
    code_value="8867-4",
    code_display="Heart rate",
    status="final",
    value_quantity={
        "value": 72,
        "unit": "beats/min",
        "system": "http://unitsofmeasure.org",
        "code": "/min"
    },
    category_code="vital-signs"
)

# Create the observation
new_observation = create_fhir_resource(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Observation",
    resource_data=observation_template
)

# Update a patient's information with optimistic concurrency control
update_fhir_resource(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    resource_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b",
    resource_data={
        "resourceType": "Patient",
        "id": "04c704c4-5d2d-4308-9c33-1690a6e47a6b",
        "name": [
            {
                "family": "Doe",
                "given": ["John", "Michael"]
            }
        ],
        "gender": "male",
        "birthDate": "1970-01-01"
    },
    if_match="W/\"1\""  # Only update if version is 1
)

# Patch a patient's phone number using JSON Patch
patch_fhir_resource(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    resource_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b",
    patch_operations=[
        {
            "op": "replace",
            "path": "/telecom/0/value",
            "value": "+1-555-999-8888"
        }
    ],
    patch_format="json-patch"
)

# Delete a patient record with version check
delete_fhir_resource(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    resource_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b",
    if_match="W/\"2\""  # Only delete if version is 2
)
```

### Working with FHIR Compartments

```python
# Get all resources in a patient's compartment
patient_compartment = get_fhir_resource_compartment(
    datastore_id="1234567890abcdef1234567890abcdef",
    compartment_type="Patient",
    compartment_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b"
)

# Get only observations in a patient's compartment
patient_observations = get_fhir_resource_compartment(
    datastore_id="1234567890abcdef1234567890abcdef",
    compartment_type="Patient",
    compartment_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b",
    resource_type="Observation",
    query_parameters={"category": "vital-signs"}
)
```

### Advanced Validation

```python
# Validate a resource against a specific profile
validation_result = validate_fhir_resource_against_profile(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_data=patient_template,
    profile_url="http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
)

if validation_result.get("resourceType") == "OperationOutcome":
    # Handle validation errors
    for issue in validation_result.get("issue", []):
        print(f"Validation {issue['severity']}: {issue.get('diagnostics', '')}")
```

### Working with FHIR Bundles

```python
# Create a bundle with multiple resources
bundle_resources = [
    {
        "resourceType": "Patient",
        "name": [{"family": "Smith", "given": ["Jane"]}],
        "gender": "female",
        "birthDate": "1985-03-15"
    },
    {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "29463-7",
                "display": "Body Weight"
            }]
        },
        "subject": {"reference": "Patient/temp-id"},
        "valueQuantity": {
            "value": 65,
            "unit": "kg",
            "system": "http://unitsofmeasure.org"
        }
    }
]

bundle_result = create_fhir_bundle(
    datastore_id="1234567890abcdef1234567890abcdef",
    bundle_resources=bundle_resources,
    bundle_type="transaction"
)
```

### Getting Resource History and Capabilities

```python
# Get resource version history with filtering
history = get_fhir_resource_history(
    datastore_id="1234567890abcdef1234567890abcdef",
    resource_type="Patient",
    resource_id="04c704c4-5d2d-4308-9c33-1690a6e47a6b",
    count=10,  # Get last 10 versions
    since="2023-01-01T00:00:00Z"  # Only versions since this date
)

# Get datastore capabilities
capabilities = get_datastore_capabilities(
    datastore_id="1234567890abcdef1234567890abcdef"
)

# Check what resource types are supported
supported_resources = []
for rest in capabilities.get("rest", []):
    for resource in rest.get("resource", []):
        supported_resources.append(resource["type"])

print(f"Supported resource types: {supported_resources}")
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
