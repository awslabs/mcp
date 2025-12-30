# API Reference

## Overview

The HealthImaging MCP Server provides **39 comprehensive tools** for AWS HealthImaging operations, organized into eight categories:

1. **Datastore Management (4 tools)** - Create, delete, get, and list datastores
2. **DICOM Import/Export Jobs (6 tools)** - Manage DICOM data import and export workflows
3. **Image Set Operations (8 tools)** - Search, retrieve, update, and manage image sets
4. **Resource Tagging (3 tools)** - Manage tags on HealthImaging resources
5. **Enhanced Search Operations (3 tools)** - Patient, study, and series-focused searches
6. **Data Analysis Operations (8 tools)** - Patient studies, series analysis, and DICOM operations
7. **Bulk Operations (2 tools)** - Large-scale metadata updates and deletions
8. **DICOM Hierarchy Operations (2 tools)** - Series and instance removal operations

## Datastore Management Tools

### create_datastore

Create a new HealthImaging datastore.

**Parameters:**
- `datastore_name` (string, required): Name for the new datastore
- `kms_key_arn` (string, optional): KMS key ARN for encryption
- `tags` (object, optional): Tags to apply to the datastore

**Returns:**
```json
{
  "datastore_id": "string",
  "datastore_status": "CREATING"
}
```

### delete_datastore

Delete a HealthImaging datastore (IRREVERSIBLE).

**Parameters:**
- `datastore_id` (string, required): ID of the datastore to delete

**Returns:**
```json
{
  "datastore_id": "string",
  "datastore_status": "DELETING"
}
```

### get_datastore

Get detailed information about a specific datastore.

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore

**Returns:**
```json
{
  "datastore_properties": {
    "datastore_id": "string",
    "datastore_name": "string",
    "datastore_status": "CREATING|ACTIVE|DELETING|DELETED",
    "datastore_arn": "string",
    "created_at": "timestamp",
    "updated_at": "timestamp",
    "kms_key_arn": "string"
  }
}
```

### list_datastores

List all HealthImaging datastores in the AWS account.

**Parameters:**
- `datastore_status` (string, optional): Filter by status (CREATING, ACTIVE, DELETING, DELETED)
- `max_results` (integer, optional): Maximum number of results (1-100)
- `next_token` (string, optional): Token for pagination

**Returns:**
```json
{
  "datastore_summaries": [
    {
      "datastore_id": "string",
      "datastore_name": "string",
      "datastore_status": "string",
      "created_at": "timestamp",
      "updated_at": "timestamp"
    }
  ],
  "next_token": "string"
}
```

## DICOM Import/Export Jobs

### start_dicom_import_job

Start a DICOM import job from S3 to HealthImaging.

**Parameters:**
- `datastore_id` (string, required): ID of the target datastore
- `data_access_role_arn` (string, required): IAM role ARN for data access
- `input_s3_uri` (string, required): S3 URI of the input data
- `job_name` (string, optional): Name for the import job
- `client_token` (string, optional): Client token for idempotency
- `output_s3_uri` (string, optional): S3 URI for the output data
- `input_owner_account_id` (string, optional): Input owner account ID

### get_dicom_import_job

Get information about a DICOM import job.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `job_id` (string, required): ID of the import job

### list_dicom_import_jobs

List DICOM import jobs for a datastore.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `job_status` (string, optional): Filter by job status
- `next_token` (string, optional): Token for pagination
- `max_results` (integer, optional): Maximum number of results (1-50)

### start_dicom_export_job

Start a DICOM export job from HealthImaging to S3.

**Parameters:**
- `datastore_id` (string, required): ID of the source datastore
- `data_access_role_arn` (string, required): IAM role ARN for data access
- `output_s3_uri` (string, required): S3 URI for the output data
- `job_name` (string, optional): Name for the export job
- `client_token` (string, optional): Client token for idempotency
- `study_instance_uid` (string, optional): Study instance UID to export
- `series_instance_uid` (string, optional): Series instance UID to export
- `sop_instance_uid` (string, optional): SOP instance UID to export
- `submitted_before` (string, optional): Export images submitted before this date
- `submitted_after` (string, optional): Export images submitted after this date

### get_dicom_export_job

Get information about a DICOM export job.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `job_id` (string, required): ID of the export job

### list_dicom_export_jobs

List DICOM export jobs for a datastore.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `job_status` (string, optional): Filter by job status
- `next_token` (string, optional): Token for pagination
- `max_results` (integer, optional): Maximum number of results (1-50)

## Image Set Operations

### search_image_sets

Search for image sets within a datastore using optional filters.

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore
- `search_criteria` (object, optional): Search filters
- `next_token` (string, optional): Token for pagination
- `max_results` (integer, optional): Maximum number of results (1-50)

**Search Criteria Format:**
```json
{
  "filters": [
    {
      "values": [
        {
          "DICOMPatientId": "PATIENT123"
        }
      ],
      "operator": "EQUAL"
    }
  ]
}
```

### get_image_set

Get metadata for a specific image set.

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore
- `image_set_id` (string, required): The ID of the image set
- `version_id` (string, optional): Version ID of the image set

### get_image_set_metadata

Get detailed DICOM metadata for an image set (returns base64-encoded metadata).

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore
- `image_set_id` (string, required): The ID of the image set
- `version_id` (string, optional): Version ID of the image set

### list_image_set_versions

List all versions of an image set.

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore
- `image_set_id` (string, required): The ID of the image set
- `next_token` (string, optional): Token for pagination
- `max_results` (integer, optional): Maximum number of results (1-50)

### update_image_set_metadata

Update DICOM metadata for an image set.

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore
- `image_set_id` (string, required): The ID of the image set
- `latest_version_id` (string, required): Latest version ID of the image set
- `update_image_set_metadata_updates` (object, required): Metadata updates

### delete_image_set

Delete an image set (IRREVERSIBLE).

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore
- `image_set_id` (string, required): The ID of the image set
- `version_id` (string, optional): Version ID of the image set

### copy_image_set

Copy an image set.

**Parameters:**
- `datastore_id` (string, required): ID of the destination datastore
- `source_image_set_id` (string, required): ID of the source image set
- `copy_image_set_information` (object, required): Copy information
- `source_datastore_id` (string, optional): ID of the source datastore

### get_image_frame

Get a specific image frame (returns base64-encoded frame data).

**Parameters:**
- `datastore_id` (string, required): The ID of the datastore
- `image_set_id` (string, required): The ID of the image set
- `image_frame_information` (object, required): Image frame information

## Resource Tagging

### list_tags_for_resource

List tags for a HealthImaging resource.

**Parameters:**
- `resource_arn` (string, required): The ARN of the resource

### tag_resource

Add tags to a HealthImaging resource.

**Parameters:**
- `resource_arn` (string, required): The ARN of the resource to tag
- `tags` (object, required): The tags to apply

### untag_resource

Remove tags from a HealthImaging resource.

**Parameters:**
- `resource_arn` (string, required): The ARN of the resource to untag
- `tag_keys` (array, required): The tag keys to remove

## Enhanced Search Operations

### search_by_patient_id

Search for image sets by patient ID with comprehensive analysis.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `patient_id` (string, required): DICOM Patient ID
- `max_results` (integer, optional): Maximum number of results (default: 50)

### search_by_study_uid

Search for image sets by study instance UID.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `study_instance_uid` (string, required): DICOM Study Instance UID
- `max_results` (integer, optional): Maximum number of results (default: 50)

### search_by_series_uid

Search for image sets by series instance UID.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `series_instance_uid` (string, required): DICOM Series Instance UID
- `max_results` (integer, optional): Maximum number of results (default: 50)

## Data Analysis Operations

### get_patient_studies

Get all studies for a specific patient with comprehensive metadata.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `patient_id` (string, required): DICOM Patient ID

### get_patient_series

Get all series for a specific patient.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `patient_id` (string, required): DICOM Patient ID

### get_study_primary_image_sets

Get primary image sets for a specific study.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `study_instance_uid` (string, required): DICOM Study Instance UID

### delete_patient_studies

Delete all studies for a specific patient (supports compliance with "right to be forgotten/right to erasure" GDPR objectives).

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `patient_id` (string, required): DICOM Patient ID

### delete_study

Delete all image sets for a specific study.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `study_instance_uid` (string, required): DICOM Study Instance UID

### delete_series_by_uid

Delete a series by SeriesInstanceUID using metadata updates.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `series_instance_uid` (string, required): DICOM Series Instance UID to delete

### get_series_primary_image_set

Get the primary image set for a given series.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `series_instance_uid` (string, required): DICOM Series Instance UID

### get_patient_dicomweb_studies

Retrieve DICOMweb SearchStudies level information for a given patient ID.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `patient_id` (string, required): DICOM Patient ID

## Bulk Operations

### bulk_update_patient_metadata

Update patient metadata across all studies for a patient.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `patient_id` (string, required): DICOM Patient ID to update metadata for
- `metadata_updates` (object, required): Patient metadata updates to apply across all studies

### bulk_delete_by_criteria

Delete multiple image sets matching specified criteria.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `criteria` (object, required): Search criteria for image sets to delete
- `max_deletions` (integer, optional): Maximum number of image sets to delete (default: 100)

## DICOM Hierarchy Operations

### remove_series_from_image_set

Remove a specific series from an image set using DICOM hierarchy operations.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `image_set_id` (string, required): ID of the image set
- `series_instance_uid` (string, required): DICOM Series Instance UID to remove

### remove_instance_from_image_set

Remove a specific instance from an image set using DICOM hierarchy operations.

**Parameters:**
- `datastore_id` (string, required): ID of the datastore
- `image_set_id` (string, required): ID of the image set
- `series_instance_uid` (string, required): DICOM Series Instance UID containing the instance
- `sop_instance_uid` (string, required): DICOM SOP Instance UID to remove

## Error Handling

All tools return structured error responses when errors occur:

```json
{
  "error": true,
  "type": "validation_error|not_found|auth_error|service_error|server_error",
  "message": "Detailed error description"
}
```

### Common Error Types

1. **validation_error**: Invalid input parameters
2. **not_found**: Resource or datastore not found
3. **auth_error**: AWS credentials not configured
4. **service_error**: AWS HealthImaging service error
5. **server_error**: Internal server error

## Rate Limits and Best Practices

- AWS HealthImaging has API rate limits - implement exponential backoff
- Use pagination for large result sets
- Cache frequently accessed metadata
- Monitor CloudWatch metrics for throttling events
- Use bulk operations for large-scale updates/deletions

## Data Types

### Timestamps
All timestamps are in ISO 8601 format: `2024-01-01T00:00:00Z`

### IDs
- **Datastore ID**: 32-character hexadecimal string
- **Image Set ID**: 32-character hexadecimal string
- **Version ID**: Integer as string
- **Frame ID**: String identifier

### Status Values
- **Datastore Status**: CREATING, ACTIVE, DELETING, DELETED
- **Image Set State**: ACTIVE, LOCKED, DELETED
- **Job Status**: SUBMITTED, IN_PROGRESS, COMPLETED, FAILED

## Usage Examples

See the `examples/` directory and `HEALTHIMAGING_TESTING_GUIDE.md` for complete usage examples and testing scenarios.
