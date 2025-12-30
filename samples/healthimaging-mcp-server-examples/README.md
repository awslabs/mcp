# HealthImaging MCP Server - Usage Examples

This directory contains comprehensive examples demonstrating how to use all 39 tools provided by the AWS HealthImaging MCP Server.

## Overview

The HealthImaging MCP Server provides 39 specialized tools for medical imaging data management:
- **21 Standard AWS API Operations**: Complete AWS HealthImaging API coverage
- **18 Advanced DICOM Operations**: Specialized medical imaging workflows

## Prerequisites

1. **MCP Server Configuration**: Add to your MCP client configuration:
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

2. **AWS Permissions**: Ensure your AWS credentials have the required HealthImaging permissions
3. **Test Data**: Use the workshop datastore ID: `ff065a6b17494ed3b3f33da4dfc60a7a`

## Tool Categories and Examples

### 1. Datastore Management (4 tools)

#### Basic Datastore Operations
```
# List all available datastores
List my HealthImaging datastores

# Get detailed information about a specific datastore
Get details for datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Create a new datastore (requires write permissions)
Create a new HealthImaging datastore named "my-medical-imaging-store"

# Delete a datastore (requires write permissions)
Delete HealthImaging datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### 2. Image Set Operations (7 tools)

#### Search and Retrieve Image Sets
```
# Advanced search with DICOM filters
Search for image sets in datastore ff065a6b17494ed3b3f33da4dfc60a7a where patient ID is "PATIENT123"

# Get detailed image set information
Get image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Extract DICOM metadata with base64 encoding
Get metadata for image set 3660db84e44321533b5f61590f06b18e in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# List version history
List versions for image set 3660db84e44321533b5f61590f06b18e in datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

#### Image Set Management
```
# Update DICOM metadata
Update metadata for image set 3660db84e44321533b5f61590f06b18e in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Copy image sets between datastores
Copy image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a to destination datastore

# Delete image set (with safety checks)
Delete image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### 3. Image Frame Operations (1 tool)

#### Frame-Level Access
```
# Retrieve individual image frames with base64 encoding
Get image frame for image set 3660db84e44321533b5f61590f06b18e in datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### 4. DICOM Import/Export Jobs (6 tools)

#### Import Operations
```
# Start DICOM import job
Start a DICOM import job for datastore ff065a6b17494ed3b3f33da4dfc60a7a with input S3 URI s3://my-bucket/dicom-data/ and role arn:aws:iam::123456789012:role/HealthImagingAccessRole

# Monitor import job status
Get DICOM import job status for job 12345 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# List all import jobs
List DICOM import jobs for datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

#### Export Operations
```
# Start DICOM export job
Start a DICOM export job for datastore ff065a6b17494ed3b3f33da4dfc60a7a with output S3 URI s3://my-bucket/export/ and role arn:aws:iam::123456789012:role/HealthImagingAccessRole

# Monitor export job status
Get DICOM export job status for job 12345 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# List all export jobs
List DICOM export jobs for datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### 5. Resource Tagging (3 tools)

#### Tag Management
```
# List existing tags
List tags for HealthImaging resource arn:aws:medical-imaging:us-east-1:123456789012:datastore/ff065a6b17494ed3b3f33da4dfc60a7a

# Add tags to resources
Tag HealthImaging resource arn:aws:medical-imaging:us-east-1:123456789012:datastore/ff065a6b17494ed3b3f33da4dfc60a7a with tags Environment=Production and Project=MedicalAI

# Remove tags from resources
Remove tags Environment and Project from HealthImaging resource arn:aws:medical-imaging:us-east-1:123456789012:datastore/ff065a6b17494ed3b3f33da4dfc60a7a
```

### 6. Enhanced Search Operations (3 tools)

#### Clinical Workflow Searches
```
# Patient-focused search
Search for all data for patient PATIENT123 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Study-centric analysis
Search for study with UID 1.2.3.4.5.6.7.8.9 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Series-level investigations
Search for series with UID 1.2.3.4.5.6.7.8.9.10 in datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### 7. Data Analysis Operations (3 tools)

#### Comprehensive Analysis
```
# Patient study overview
Get all studies for patient PATIENT123 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Series-level analysis
Get all series for patient PATIENT123 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Primary image set identification
Get primary image sets for study 1.2.3.4.5.6.7.8.9 in datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### 8. Delete Operations (5 tools)

#### Data Removal (supports compliance with "right to be forgotten/right to erasure" GDPR objectives)
```
# Complete patient data removal
Delete all studies for patient PATIENT123 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Study-level deletion
Delete study with UID 1.2.3.4.5.6.7.8.9 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Series deletion using metadata updates
Delete series with UID 1.2.3.4.5.6.7.8.9.10 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Instance-level deletion in study
Delete instance 1.2.3.4.5.6.7.8.9.10.11 from study 1.2.3.4.5.6.7.8.9 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Instance-level deletion in series
Delete instance 1.2.3.4.5.6.7.8.9.10.11 from series 1.2.3.4.5.6.7.8.9.10 in datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### 9. Metadata Update Operations (3 tools)

#### Advanced Metadata Management
```
# Get primary image set for series
Get primary image set for series 1.2.3.4.5.6.7.8.9.10 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# DICOMweb integration
Get DICOMweb studies for patient PATIENT123 in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Update patient/study metadata
Update patient and study metadata for patient PATIENT123 in datastore ff065a6b17494ed3b3f33da4dfc60a7a with new patient name "John Doe Updated"
```

### 10. Bulk Operations (2 tools)

#### Enterprise-Scale Operations
```
# Mass patient data corrections
Bulk update metadata for patient PATIENT123 in datastore ff065a6b17494ed3b3f33da4dfc60a7a with patient name "Bulk Updated Name"

# Criteria-based bulk deletion
Bulk delete image sets in datastore ff065a6b17494ed3b3f33da4dfc60a7a where modality is "CR" and study date is before "20200101"
```

### 11. DICOM Hierarchy Operations (2 tools)

#### Precision Data Management
```
# Series-level data management
Remove series 1.2.3.4.5.6.7.8.9.10 from image set 3660db84e44321533b5f61590f06b18e in datastore ff065a6b17494ed3b3f33da4dfc60a7a

# Instance-level precision removal
Remove instance 1.2.3.4.5.6.7.8.9.10.11 from image set 3660db84e44321533b5f61590f06b18e in datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

## Common Workflows

### Medical Imaging Research Workflow
1. **Discovery**: Use `list_datastores` to find available data
2. **Search**: Use `search_by_patient_id` to find specific patient data
3. **Analysis**: Use `get_patient_studies` for comprehensive overview
4. **Access**: Use `get_image_set_metadata` to extract DICOM metadata
5. **Processing**: Use `get_image_frame` to access individual frames

### Data Management Workflow
1. **Import**: Use `start_dicom_import_job` to import new DICOM data
2. **Monitor**: Use `get_dicom_import_job` to track import progress
3. **Organize**: Use `tag_resource` to organize data with metadata
4. **Update**: Use `update_image_set_metadata` for corrections
5. **Archive**: Use `start_dicom_export_job` for long-term storage

### Supporting Compliance with Right to be Forgotten/Right to Erasure Workflow
1. **Identify**: Use `search_by_patient_id` to find all patient data
2. **Analyze**: Use `get_patient_studies` to understand data scope
3. **Remove**: Use `delete_patient_studies` for complete data removal
4. **Verify**: Use `search_by_patient_id` to confirm deletion

## Error Handling

The server provides comprehensive error handling for common scenarios:

- **Authentication Errors**: Check AWS credentials and permissions
- **Resource Not Found**: Verify datastore/image set IDs exist
- **Validation Errors**: Review input parameters and formats
- **Rate Limiting**: Server handles automatic retry with exponential backoff

## Best Practices

1. **Start with Discovery**: Always use `list_datastores` to understand available resources
2. **Use Appropriate Search**: Choose between basic `search_image_sets` and specialized searches
3. **Handle Permissions**: Many operations require write permissions - test with read operations first
4. **Monitor Jobs**: Always check import/export job status before proceeding
5. **Tag Resources**: Use consistent tagging strategy for better organization
6. **Test Safely**: Use the workshop datastore for testing before production operations

## Support

For additional help:
- Review the [HealthImaging MCP Server documentation](../../src/healthimaging-mcp-server/README.md)
- Check the [AWS HealthImaging documentation](https://docs.aws.amazon.com/healthimaging/)
- Open issues in the [GitHub repository](https://github.com/awslabs/mcp-server-collection/issues)
