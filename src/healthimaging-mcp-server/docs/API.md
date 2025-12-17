# API Reference

## Tools

### Data Store Tools

#### list_datastores

List all HealthImaging data stores in the AWS account.

**Parameters:**
- `max_results` (integer, optional): Maximum number of results to return. Default: 50

**Returns:**
JSON string containing:
```json
{
  "datastoreSummaries": [
    {
      "datastoreId": "string",
      "datastoreName": "string",
      "datastoreStatus": "CREATING|ACTIVE|DELETING|DELETED",
      "createdAt": "timestamp",
      "updatedAt": "timestamp"
    }
  ]
}
```

**Example:**
```json
{
  "max_results": 10
}
```

---

#### get_datastore

Get detailed information about a specific data store.

**Parameters:**
- `datastore_id` (string, required): The ID of the data store

**Returns:**
JSON string containing:
```json
{
  "datastore": {
    "datastoreId": "string",
    "datastoreName": "string",
    "datastoreStatus": "CREATING|ACTIVE|DELETING|DELETED",
    "datastoreArn": "string",
    "createdAt": "timestamp",
    "updatedAt": "timestamp"
  }
}
```

**Example:**
```json
{
  "datastore_id": "12345678901234567890123456789012"
}
```

---

### Image Set Tools

#### search_image_sets

Search for image sets within a data store using optional filters.

**Parameters:**
- `datastore_id` (string, required): The ID of the data store
- `search_criteria` (string, optional): JSON string with search filters
- `max_results` (integer, optional): Maximum number of results. Default: 50

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

**Supported DICOM Attributes:**
- `DICOMPatientId`
- `DICOMStudyId`
- `DICOMStudyInstanceUID`
- `DICOMSeriesInstanceUID`
- `DICOMStudyDate`
- `DICOMStudyDescription`

**Returns:**
JSON string containing:
```json
{
  "imageSetsMetadataSummaries": [
    {
      "imageSetId": "string",
      "version": integer,
      "createdAt": "timestamp",
      "updatedAt": "timestamp",
      "DICOMTags": {
        "DICOMPatientId": "string",
        "DICOMStudyId": "string"
      }
    }
  ]
}
```

**Example:**
```json
{
  "datastore_id": "12345678901234567890123456789012",
  "search_criteria": "{\"filters\":[{\"values\":[{\"DICOMPatientId\":\"PATIENT123\"}],\"operator\":\"EQUAL\"}]}",
  "max_results": 20
}
```

---

#### get_image_set

Get metadata for a specific image set.

**Parameters:**
- `datastore_id` (string, required): The ID of the data store
- `image_set_id` (string, required): The ID of the image set

**Returns:**
JSON string containing:
```json
{
  "imageSetId": "string",
  "versionId": "string",
  "imageSetState": "ACTIVE|LOCKED|DELETED",
  "imageSetWorkflowStatus": "CREATED|COPIED|COPYING|COPYING_WITH_READ_ONLY_ACCESS|COPY_FAILED|UPDATING|UPDATED|UPDATE_FAILED|DELETING|DELETED",
  "createdAt": "timestamp",
  "updatedAt": "timestamp",
  "deletedAt": "timestamp"
}
```

**Example:**
```json
{
  "datastore_id": "12345678901234567890123456789012",
  "image_set_id": "abcdef1234567890abcdef1234567890"
}
```

---

#### get_image_set_metadata

Get detailed DICOM metadata for an image set.

**Parameters:**
- `datastore_id` (string, required): The ID of the data store
- `image_set_id` (string, required): The ID of the image set
- `version_id` (string, optional): Specific version ID (defaults to latest)

**Returns:**
JSON string containing DICOM metadata in hierarchical format:
```json
{
  "Study": {
    "DICOM": {
      "StudyInstanceUID": "string",
      "StudyDate": "string",
      "StudyTime": "string",
      "StudyDescription": "string"
    },
    "Series": {
      "SeriesInstanceUID": {
        "DICOM": {
          "Modality": "string",
          "SeriesNumber": "string"
        },
        "Instances": {
          "SOPInstanceUID": {
            "DICOM": {
              "InstanceNumber": "string"
            },
            "ImageFrames": [
              {
                "ID": "string",
                "FrameSizeInBytes": integer
              }
            ]
          }
        }
      }
    }
  }
}
```

**Example:**
```json
{
  "datastore_id": "12345678901234567890123456789012",
  "image_set_id": "abcdef1234567890abcdef1234567890",
  "version_id": "1"
}
```

---

#### list_image_set_versions

List all versions of an image set.

**Parameters:**
- `datastore_id` (string, required): The ID of the data store
- `image_set_id` (string, required): The ID of the image set
- `max_results` (integer, optional): Maximum number of results. Default: 50

**Returns:**
JSON string containing:
```json
{
  "imageSetPropertiesList": [
    {
      "imageSetId": "string",
      "versionId": "string",
      "imageSetState": "ACTIVE|LOCKED|DELETED",
      "createdAt": "timestamp",
      "updatedAt": "timestamp"
    }
  ]
}
```

**Example:**
```json
{
  "datastore_id": "12345678901234567890123456789012",
  "image_set_id": "abcdef1234567890abcdef1234567890",
  "max_results": 10
}
```

---

### Image Frame Tools

#### get_image_frame

Get information about retrieving a specific image frame.

**Note:** This tool returns metadata about the frame. Actual binary frame data retrieval requires additional handling.

**Parameters:**
- `datastore_id` (string, required): The ID of the data store
- `image_set_id` (string, required): The ID of the image set
- `image_frame_id` (string, required): The ID of the image frame

**Returns:**
JSON string containing:
```json
{
  "datastoreId": "string",
  "imageSetId": "string",
  "imageFrameId": "string",
  "contentType": "application/octet-stream",
  "message": "Frame data available (binary data not shown)"
}
```

**Example:**
```json
{
  "datastore_id": "12345678901234567890123456789012",
  "image_set_id": "abcdef1234567890abcdef1234567890",
  "image_frame_id": "frame123456"
}
```

---

## Error Responses

All tools return error information in JSON format when an error occurs:

```json
{
  "error": "Error message describing what went wrong"
}
```

### Common Error Types

1. **Authentication Errors**: Invalid or missing AWS credentials
2. **Authorization Errors**: Insufficient IAM permissions
3. **Resource Not Found**: Specified resource doesn't exist
4. **Validation Errors**: Invalid parameter values
5. **Service Errors**: AWS service-side issues

### Error Handling Best Practices

- Check for `error` key in response
- Log errors for debugging
- Provide user-friendly error messages
- Retry transient errors with exponential backoff

---

## Rate Limits

AWS HealthImaging has API rate limits. Refer to AWS documentation for current limits:
- https://docs.aws.amazon.com/healthimaging/latest/devguide/quotas.html

### Recommendations

- Implement exponential backoff for throttled requests
- Use pagination to limit result set sizes
- Cache frequently accessed metadata
- Monitor CloudWatch metrics for throttling events

---

## Data Types

### Timestamps

All timestamps are in ISO 8601 format:
```
2024-01-01T00:00:00Z
```

### IDs

- **Datastore ID**: 32-character hexadecimal string
- **Image Set ID**: 32-character hexadecimal string
- **Version ID**: Integer as string
- **Frame ID**: String identifier

### Status Values

**Datastore Status:**
- `CREATING`: Data store is being created
- `ACTIVE`: Data store is active and available
- `DELETING`: Data store is being deleted
- `DELETED`: Data store has been deleted

**Image Set State:**
- `ACTIVE`: Image set is active
- `LOCKED`: Image set is locked
- `DELETED`: Image set has been deleted

---

## Usage Examples

See the `examples/` directory for complete usage examples.
