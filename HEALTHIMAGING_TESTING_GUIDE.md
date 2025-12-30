# HealthImaging MCP Server - Complete Testing Guide

This guide shows you how to test all 39 HealthImaging MCP tools through Kiro's interface.
Includes 21 standard AWS API operations and 18 advanced DICOM operations.

## Prerequisites
- MCP server is running and configured in `.kiro/settings/mcp.json`
- You have AWS credentials configured
- You have access to HealthImaging resources

## Test Data
Based on your environment, use these values:
- **Datastore ID**: `ff065a6b17494ed3b3f33da4dfc60a7a` (workshop) # pragma: allowlist secret
- **Image Set ID**: `3660db84e44321533b5f61590f06b18e`
- **Account ID**: `524256002118`

## Testing Instructions

### 1. Datastore Management Tools (4 tools)

#### ✅ list_datastores
```
List my HealthImaging datastores
```
**Expected**: Returns list of datastores with IDs, names, and status

#### ✅ get_datastore
```
Get details for datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns detailed datastore information

#### ⚠️ create_datastore
```
Create a new HealthImaging datastore named "test-datastore-123"
```
**Expected**: May fail with AccessDenied (requires write permissions)

#### ⚠️ delete_datastore
```
Delete HealthImaging datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: May fail with AccessDenied (requires write permissions)

---

### 2. DICOM Import Job Tools (3 tools)

#### ✅ list_dicom_import_jobs
```
List DICOM import jobs for datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns list of import jobs (may be empty)

#### ⚠️ start_dicom_import_job
```
Start a DICOM import job for datastore ff065a6b17494ed3b3f33da4dfc60a7a with input S3 URI s3://my-bucket/dicom-data/ and role arn:aws:iam::524256002118:role/HealthImagingAccessRole
```
**Expected**: May fail with AccessDenied or validation errors

#### ❌ get_dicom_import_job
```
Get DICOM import job details for datastore ff065a6b17494ed3b3f33da4dfc60a7a and job ID nonexistent-job-id
```
**Expected**: ResourceNotFoundException (no real job ID to test with)

---

### 3. DICOM Export Job Tools (3 tools)

#### ✅ list_dicom_export_jobs
```
List DICOM export jobs for datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns list of export jobs (may be empty)

#### ⚠️ start_dicom_export_job
```
Start a DICOM export job for datastore ff065a6b17494ed3b3f33da4dfc60a7a with output S3 URI s3://my-bucket/export/ and role arn:aws:iam::524256002118:role/HealthImagingAccessRole
```
**Expected**: May fail with AccessDenied or validation errors (requires write permissions)

#### ❌ get_dicom_export_job
```
Get DICOM export job details for datastore ff065a6b17494ed3b3f33da4dfc60a7a and job ID nonexistent-job-id
```
**Expected**: ResourceNotFoundException (no real job ID to test with)

---

### 4. Image Set Management Tools (7 tools)

#### ✅ search_image_sets
```
Search for image sets in datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns list of image sets with metadata

#### ✅ get_image_set
```
Get image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns image set details with properties

#### ✅ get_image_set_metadata
```
Get metadata for image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns base64-encoded metadata blob with content type

#### ✅ list_image_set_versions
```
List versions for image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns list of image set versions

#### ⚠️ update_image_set_metadata
```
Update metadata for image set 3660db84e44321533b5f61590f06b18e in datastore ff065a6b17494ed3b3f33da4dfc60a7a with latest version ID 1 and updates {"DICOMUpdates": {"updatableAttributes": {"DICOMPatientName": "Updated Name"}}}
```
**Expected**: May fail with AccessDenied (requires write permissions)

#### ⚠️ delete_image_set
```
Delete image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: May fail with AccessDenied (requires write permissions)

#### ⚠️ copy_image_set
```
Copy image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a to datastore 39cf4d86a048433c846dd025a68becef with copy information {"dicomCopies": [{"copiableAttributes": {}}]}
```
**Expected**: May fail with AccessDenied (requires write permissions)

---

### 5. Image Frame Tool (1 tool)

#### ❌ get_image_frame
```
Get image frame from datastore ff065a6b17494ed3b3f33da4dfc60a7a, image set 3660db84e44321533b5f61590f06b18e with frame information {"imageFrameId": "3660db84e44321533b5f61590f06b18e"} # pragma: allowlist secret
```
**Expected**: ResourceNotFoundException (frame ID format may be incorrect)

---

### 6. Tagging Tools (3 tools)

#### ✅ list_tags_for_resource
```
List tags for resource arn:aws:medical-imaging:us-west-2:524256002118:datastore/ff065a6b17494ed3b3f33da4dfc60a7a
```
**Expected**: Returns tags (may be empty object)

#### ⚠️ tag_resource
```
Add tags to resource arn:aws:medical-imaging:us-west-2:524256002118:datastore/ff065a6b17494ed3b3f33da4dfc60a7a with tags {"Environment": "Test", "Purpose": "Workshop"}
```
**Expected**: May fail with AccessDenied (requires write permissions)

#### ⚠️ untag_resource
```
Remove tags from resource arn:aws:medical-imaging:us-west-2:524256002118:datastore/ff065a6b17494ed3b3f33da4dfc60a7a with tag keys ["Environment", "Purpose"]
```
**Expected**: May fail with AccessDenied (requires write permissions)

---

## Quick Test Commands

You can copy and paste these commands one by one in Kiro:

### Read-Only Tests (Should Work)
```
List my HealthImaging datastores
Get details for datastore ff065a6b17494ed3b3f33da4dfc60a7a
List DICOM import jobs for datastore ff065a6b17494ed3b3f33da4dfc60a7a
Search for image sets in datastore ff065a6b17494ed3b3f33da4dfc60a7a
Get image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
Get metadata for image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
List versions for image set 3660db84e44321533b5f61590f06b18e from datastore ff065a6b17494ed3b3f33da4dfc60a7a
List tags for resource arn:aws:medical-imaging:us-west-2:524256002118:datastore/ff065a6b17494ed3b3f33da4dfc60a7a
```

### Export Job Tests (Should Work)
```
List DICOM export jobs for datastore ff065a6b17494ed3b3f33da4dfc60a7a
```

### Write Operation Tests (May Fail with AccessDenied)
```
Create a new HealthImaging datastore named "test-datastore-123"
Add tags to resource arn:aws:medical-imaging:us-west-2:524256002118:datastore/ff065a6b17494ed3b3f33da4dfc60a7a with tags {"Environment": "Test"}
```

## Expected Results Summary

| Tool Category | Expected Behavior |
|---------------|-------------------|
| **Read Operations** | ✅ Should work and return data |
| **Write Operations** | ⚠️ May fail with AccessDenied |
| **Export Jobs** | ✅ Should work and return data |
| **Invalid Resources** | ❌ Should raise ResourceNotFoundException |

## Troubleshooting

- **Connection Issues**: Restart MCP server if tools are not responding
- **AccessDenied**: Normal for write operations without proper IAM permissions
- **ResourceNotFoundException**: Expected when testing with non-existent resources

## Test Results Tracking

Create a checklist and mark each tool as you test it:

- [ ] list_datastores
- [ ] get_datastore
- [ ] create_datastore
- [ ] delete_datastore
- [ ] list_dicom_import_jobs
- [ ] start_dicom_import_job
- [ ] get_dicom_import_job
- [ ] list_dicom_export_jobs
- [ ] start_dicom_export_job
- [ ] get_dicom_export_job
- [ ] search_image_sets
- [ ] get_image_set
- [ ] get_image_set_metadata
- [ ] list_image_set_versions
- [ ] update_image_set_metadata
- [ ] delete_image_set
- [ ] copy_image_set
- [ ] get_image_frame
- [ ] list_tags_for_resource
- [ ] tag_resource
- [ ] untag_resource

**Total: 39 tools** (21 standard AWS API operations + 18 advanced DICOM operations)
