# S3 Storage Lens Metrics Reference

This resource provides information about the metrics available in S3 Storage Lens exported data and sample queries for analysis.

## Overview

Amazon S3 Storage Lens is an analytics feature that provides organization-wide visibility into object storage usage and activity trends. Storage Lens can analyze metrics across your entire organization, specific accounts, regions, buckets, or prefixes.

## Available Metrics

S3 Storage Lens collects and exports the following types of metrics:

1. **Storage metrics** - Data about the size and count of objects in your buckets
2. **Activity metrics** - Data about requests, uploads, downloads, and other operations
3. **Detailed status code metrics** - HTTP status code statistics for requests
4. **Advanced cost optimization metrics** - Data to help identify cost optimization opportunities
5. **Advanced data protection metrics** - Data about encryption and replication
6. **Access management metrics** - Data about bucket permissions and settings

## Key Optimization Opportunities

When analyzing Storage Lens data, look for these key optimization opportunities:

1. **Storage class transitions** - Identify objects in STANDARD storage class that could be moved to lower-cost tiers
2. **Lifecycle management** - Identify buckets with high percentages of noncurrent versions or delete markers
3. **Incomplete multipart uploads** - Find buckets with significant storage consumed by incomplete multipart uploads
4. **Unencrypted objects** - Identify buckets with unencrypted objects that should be encrypted
5. **Replication opportunities** - Find buckets that might benefit from replication for data protection

## Sample Queries

Here are sample SQL queries you can use with the `storage_lens_run_query` tool to analyze your Storage Lens data. Replace `{table}` with your actual table name (the tool will do this automatically).

### 1. Storage Distribution by Region and Storage Class

Identifies how your storage is distributed across regions and storage classes, helping you find opportunities to transition to lower-cost storage classes.

```sql
SELECT
    aws_region,
    storage_class,
    SUM(CAST(metric_value AS BIGINT)) as total_bytes
FROM
    {table}
WHERE
    metric_name = 'StorageBytes'
GROUP BY
    aws_region, storage_class
ORDER BY
    total_bytes DESC
```

### 2. Object Lifecycle Management Opportunities

Identifies buckets with high percentages of noncurrent versions, which could benefit from lifecycle rules.

```sql
SELECT
    aws_region,
    storage_class,
    SUM(CASE WHEN metric_name = 'NonCurrentVersionStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as noncurrent_bytes,
    SUM(CASE WHEN metric_name = 'StorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as total_bytes
FROM
    {table}
WHERE
    metric_name IN ('NonCurrentVersionStorageBytes', 'StorageBytes')
GROUP BY
    aws_region, storage_class
HAVING
    SUM(CASE WHEN metric_name = 'NonCurrentVersionStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) > 0
ORDER BY
    noncurrent_bytes DESC
```

### 3. Incomplete Multipart Uploads Analysis

Identifies buckets with storage consumed by incomplete multipart uploads, especially those older than 7 days.

```sql
SELECT
    aws_region,
    storage_class,
    SUM(CASE WHEN metric_name = 'IncompleteMultipartUploadStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as incomplete_mpu_bytes,
    SUM(CASE WHEN metric_name = 'IncompleteMPUStorageBytesOlderThan7Days' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as incomplete_mpu_bytes_older_than_7days
FROM
    {table}
WHERE
    metric_name IN ('IncompleteMultipartUploadStorageBytes', 'IncompleteMPUStorageBytesOlderThan7Days')
GROUP BY
    aws_region, storage_class
HAVING
    SUM(CASE WHEN metric_name = 'IncompleteMultipartUploadStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) > 0
ORDER BY
    incomplete_mpu_bytes DESC
```

### 4. Encryption Analysis

Identifies buckets with unencrypted objects that should be encrypted.

```sql
SELECT
    aws_region,
    storage_class,
    SUM(CASE WHEN metric_name = 'UnencryptedStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as unencrypted_bytes,
    SUM(CASE WHEN metric_name = 'StorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as total_bytes
FROM
    {table}
WHERE
    metric_name IN ('UnencryptedStorageBytes', 'StorageBytes')
GROUP BY
    aws_region, storage_class
HAVING
    SUM(CASE WHEN metric_name = 'UnencryptedStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) > 0
ORDER BY
    unencrypted_bytes DESC
```

### 5. Top Buckets by Storage

Identifies your largest buckets to focus optimization efforts.

```sql
SELECT
    bucket_name,
    SUM(CAST(metric_value AS BIGINT)) as total_bytes
FROM
    {table}
WHERE
    metric_name = 'StorageBytes'
GROUP BY
    bucket_name
ORDER BY
    total_bytes DESC
LIMIT 10
```

### 6. Lifecycle Rule Analysis

Identifies buckets that might benefit from additional lifecycle rules.

```sql
SELECT
    bucket_name,
    SUM(CASE WHEN metric_name = 'TotalLifecycleRuleCount' THEN CAST(metric_value AS INTEGER) ELSE 0 END) as lifecycle_rule_count,
    SUM(CASE WHEN metric_name = 'StorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as total_bytes
FROM
    {table}
WHERE
    metric_name IN ('TotalLifecycleRuleCount', 'StorageBytes')
GROUP BY
    bucket_name
ORDER BY
    lifecycle_rule_count ASC, total_bytes DESC
```

## S3 Storage Lens Metrics Reference

| Metric Name | Name in Exported Data | Description | Derived | Derived Metric Formula |
|-------------|----------------------|-------------|---------|------------------------|
| Total storage | StorageBytes | The total storage, inclusive of incomplete multipart uploads, object metadata, and delete markers | N | - |
| Object count | ObjectCount | The total object count | N | - |
| Average object size | - | The average object size | Y | sum(StorageBytes)/sum(ObjectCount) |
| Active buckets | - | The total number of buckets with storage > 0 bytes | Y | - |
| Buckets | - | The total number of buckets | Y | - |
| Accounts | - | The number of accounts whose storage is in scope | Y | - |
| Current version bytes | CurrentVersionStorageBytes | The number of bytes that are a current version of an object | N | - |
| % current version bytes | - | The percentage of bytes in scope that are current versions of objects | Y | sum(CurrentVersionStorageBytes)/sum(StorageBytes) |
| Current version object count | CurrentVersionObjectCount | The count of current version objects | N | - |
| % current version objects | - | The percentage of objects in scope that are a current version | Y | sum(CurrentVersionObjectCount)/sum(ObjectCount) |
| Noncurrent version bytes | NonCurrentVersionStorageBytes | The number of noncurrent version bytes | N | - |
| % noncurrent version bytes | - | The percentage of bytes in scope that are noncurrent versions | Y | sum(NonCurrentVersionStorageBytes)/sum(StorageBytes) |
| Noncurrent version object count | NonCurrentVersionObjectCount | The count of the noncurrent object versions | N | - |
| % noncurrent version objects | - | The percentage of objects in scope that are a noncurrent version | Y | sum(NonCurrentVersionObjectCount)/sum(ObjectCount) |
| Delete marker bytes | DeleteMarkerStorageBytes | The number of bytes in scope that are delete markers | N | - |
| % delete marker bytes | - | The percentage of bytes in scope that are delete markers | Y | sum(DeleteMarkerStorageBytes)/sum(StorageBytes) |
| Delete marker object count | DeleteMarkerObjectCount | The total number of objects with a delete marker | N | - |
| % delete marker objects | - | The percentage of objects in scope with a delete marker | Y | sum(DeleteMarkerObjectCount)/sum(ObjectCount) |
| Incomplete multipart upload bytes | IncompleteMultipartUploadStorageBytes | The total bytes in scope for incomplete multipart uploads | N | - |
| % incomplete multipart upload bytes | - | The percentage of bytes in scope that are the result of incomplete multipart uploads | Y | sum(IncompleteMultipartUploadStorageBytes)/sum(StorageBytes) |
| Incomplete multipart upload object count | IncompleteMultipartUploadObjectCount | The number of objects in scope that are incomplete multipart uploads | N | - |
| % incomplete multipart upload objects | - | The percentage of objects in scope that are incomplete multipart uploads | Y | sum(IncompleteMultipartUploadObjectCount)/sum(ObjectCount) |
| Incomplete multipart upload storage bytes greater than 7 days old | IncompleteMPUStorageBytesOlderThan7Days | The total bytes in scope for incomplete multipart uploads that are more than 7 days old | N | - |
| % incomplete multipart upload storage bytes greater than 7 days old | - | The percentage of bytes for incomplete multipart uploads that are more than 7 days old | Y | sum(IncompleteMPUStorageBytesOlderThan7Days)/sum(StorageBytes) |
| Incomplete multipart upload object count greater than 7 days old | IncompleteMPUObjectCountOlderThan7Days | The number of objects that are incomplete multipart uploads more than 7 days old | N | - |
| % incomplete multipart upload object count greater than 7 days old | - | The percentage of objects that are incomplete multipart uploads more than 7 days old | Y | sum(IncompleteMPUObjectCountOlderThan7Days)/sum(ObjectCount) |
| Transition lifecycle rule count | TransitionLifecycleRuleCount | The count of lifecycle rules to transition objects to another storage class | N | - |
| Average transition lifecycle rules per bucket | - | The average number of lifecycle rules to transition objects to another storage class | Y | sum(TransitionLifecycleRuleCount)/sum(DistinctNumberOfBuckets) |
| Expiration lifecycle rule count | ExpirationLifecycleRuleCount | The count of lifecycle rules to expire objects | N | - |
| Average expiration lifecycle rules per bucket | - | The average number of lifecycle rules to expire objects | Y | sum(ExpirationLifecycleRuleCount)/sum(DistinctNumberOfBuckets) |
| Noncurrent version transition lifecycle rule count | NoncurrentVersionTransitionLifecycleRuleCount | The count of lifecycle rules to transition noncurrent object versions to another storage class | N | - |
| Average noncurrent version transition lifecycle rules per bucket | - | The average number of lifecycle rules to transition noncurrent object versions to another storage class | Y | sum(NoncurrentVersionTransitionLifecycleRuleCount)/sum(DistinctNumberOfBuckets) |
| Noncurrent version expiration lifecycle rule count | NoncurrentVersionExpirationLifecycleRuleCount | The count of lifecycle rules to expire noncurrent object versions | N | - |
| Average noncurrent version expiration lifecycle rules per bucket | - | The average number of lifecycle rules to expire noncurrent object versions | Y | sum(NoncurrentVersionExpirationLifecycleRuleCount)/sum(DistinctNumberOfBuckets) |
| Abort incomplete multipart upload lifecycle rule count | AbortIncompleteMPULifecycleRuleCount | The count of lifecycle rules to delete incomplete multipart uploads | N | - |
| Average abort incomplete multipart upload lifecycle rules per bucket | - | The average number of lifecycle rules to delete incomplete multipart uploads | Y | sum(AbortIncompleteMPULifecycleRuleCount)/sum(DistinctNumberOfBuckets) |
| Expired object delete marker lifecycle rule count | ExpiredObjectDeleteMarkerLifecycleRuleCount | The count of lifecycle rules to remove expired object delete markers | N | - |
| Average expired object delete marker lifecycle rules per bucket | - | The average number of lifecycle rules to remove expired object delete markers | Y | sum(ExpiredObjectDeleteMarkerLifecycleRuleCount)/sum(DistinctNumberOfBuckets) |
| Total lifecycle rule count | TotalLifecycleRuleCount | The total count of lifecycle rules | N | - |
| Average lifecycle rule count per bucket | - | The average number of lifecycle rules | Y | sum(TotalLifecycleRuleCount)/sum(DistinctNumberOfBuckets) |
| Encrypted bytes | EncryptedStorageBytes | The total number of encrypted bytes | N | - |
| % encrypted bytes | - | The percentage of total bytes that are encrypted | Y | sum(EncryptedObjectCount)/sum(StorageBytes) |
| Encrypted object count | EncryptedObjectCount | The total count of objects that are encrypted | N | - |
| % encrypted objects | - | The percentage of objects that are encrypted | Y | sum(EncryptedStorageBytes)/sum(ObjectCount) |
| Unencrypted bytes | UnencryptedStorageBytes | The number of bytes that are unencrypted | Y | sum(StorageBytes) - sum(EncryptedStorageBytes) |
| % unencrypted bytes | - | The percentage of bytes that are unencrypted | Y | sum(UnencryptedStorageBytes)/sum(StorageBytes) |
| Unencrypted object count | UnencryptedObjectCount | The total count of objects that are unencrypted | Y | sum(ObjectCount) - sum(EncryptedObjectCount) |
| % unencrypted objects | - | The percentage of unencrypted objects | Y | sum(UnencryptedStorageBytes)/sum(ObjectCount) |
| Replicated storage bytes source | ReplicatedStorageBytesSource | The total number of bytes that are replicated from the source bucket | N | - |
| % replicated bytes source | - | The percentage of total bytes that are replicated from the source bucket | Y | sum(ReplicatedStorageBytesSource)/sum(StorageBytes) |
| Replicated object count source | ReplicatedObjectCountSource | The count of replicated objects from the source bucket | N | - |
| % replicated objects source | - | The percentage of total objects that are replicated from the source bucket | Y | sum(ReplicatedStorageObjectCount)/sum(ObjectCount) |
| Replicated storage bytes destination | ReplicatedStorageBytes | The total number of bytes that are replicated to the destination bucket | N | - |
| % replicated bytes destination | - | The percentage of total bytes that are replicated to the destination bucket | Y | sum(ReplicatedStorageBytes)/sum(StorageBytes) |
| Replicated object count destination | ReplicatedObjectCount | The count of objects that are replicated to the destination bucket | N | - |
| % replicated objects destination | - | The percentage of total objects that are replicated to the destination bucket | Y | sum(ReplicatedObjectCount)/sum(ObjectCount) |
| Object Lock bytes | ObjectLockEnabledStorageBytes | The total count of Object Lock enabled storage bytes | N | sum(UnencryptedStorageBytes)/sum(ObjectLockEnabledStorageCount)-sum(ObjectLockEnabledStorageBytes) |
| % Object Lock bytes | - | The percentage of Object Lock enabled storage bytes | Y | sum(ObjectLockEnabledStorageBytes)/sum(StorageBytes) |
| Object Lock object count | ObjectLockEnabledObjectCount | The total count of Object Lock objects | N | - |
| % Object Lock objects | - | The percentage of total objects that have Object Lock enabled | Y | sum(ObjectLockEnabledObjectCount)/sum(ObjectCount) |
| Versioning-enabled bucket count | VersioningEnabledBucketCount | The count of buckets that have S3 Versioning enabled | N | - |
| % versioning-enabled buckets | - | The percentage of buckets that have S3 Versioning enabled | Y | sum(VersioningEnabledBucketCount)/sum(DistinctNumberOfBuckets) |
| MFA delete-enabled bucket count | MFADeleteEnabledBucketCount | The count of buckets that have MFA (multi-factor authentication) delete enabled | N | - |
| % MFA delete-enabled buckets | - | The percentage of buckets that have MFA (multi-factor authentication) delete enabled | Y | sum(MFADeleteEnabledBucketCount)/sum(DistinctNumberOfBuckets) |
| SSE-KMS enabled bucket count | SSEKMSEnabledBucketCount | The count of buckets that use server-side encryption with AWS Key Management Service keys (SSE-KMS) for default bucket encryption | N | - |
| % SSE-KMS enabled buckets | - | The percentage of buckets that SSE-KMS for default bucket encryption | Y | sum(SSEKMSEnabledBucketCount)/sum(DistinctNumberOfBuckets) |
| All unsupported signature requests | AllUnsupportedSignatureRequests | The total number of requests that use unsupported AWS signature versions | N | - |
| % all unsupported signature requests | - | The percentage of requests that use unsupported AWS signature versions | Y | sum(AllUnsupportedSignatureRequests)/sum(AllRequests) |
| All unsupported TLS requests | AllUnsupportedTLSRequests | The number of requests that use unsupported Transport Layer Security (TLS) versions | N | - |
| % all unsupported TLS requests | - | The percentage of requests that use unsupported TLS versions | Y | sum(AllUnsupportedTLSRequests)/sum(AllRequests) |
| All SSE-KMS requests | AllSSEKMSRequests | The total number of requests that specify SSE-KMS | N | - |
| % all SSE-KMS requests | - | The percentage of requests that specify SSE-KMS | Y | sum(AllSSEKMSRequests)/sum(AllRequests) |
| Same-Region Replication rule count | SameRegionReplicationRuleCount | The count of replication rules for Same-Region Replication (SRR) | N | - |
| Average Same-Region Replication rules per bucket | - | The average number of replication rules for SRR | Y | sum(SameRegionReplicationRuleCount)/sum(DistinctNumberOfBuckets) |
| Cross-Region Replication rule count | CrossRegionReplicationRuleCount | The count of replication rules for Cross-Region Replication (CRR) | N | - |
| Average Cross-Region Replication rules per bucket | - | The average number of replication rules for CRR | Y | sum(CrossRegionReplicationRuleCount)/sum(DistinctNumberOfBuckets) |
| Same-account replication rule count | SameAccountReplicationRuleCount | The count of replication rules for replication within the same account | N | - |
| Average same-account replication rules per bucket | - | The average number of replication rules for replication within the same account | Y | sum(SameAccountReplicationRuleCount)/sum(DistinctNumberOfBuckets) |
| Cross-account replication rule count | CrossAccountReplicationRuleCount | The count of replication rules for cross-account replication | N | - |
| Average cross-account replication rules per bucket | - | The average number of replication rules for cross-account replication | Y | sum(CrossAccountReplicationRuleCount)/sum(DistinctNumberOfBuckets) |
| Invalid destination replication rule count | InvalidDestinationReplicationRuleCount | The count of replication rules with a replication destination that's not valid | N | - |
| Average invalid destination replication rules per bucket | - | The average number of replication rules with a replication destination that's not valid | Y | sum(InvalidReplicationRuleCount)/sum(DistinctNumberOfBuckets) |
| Total replication rule count | - | The total replication rule count | Y | - |
| Average replication rule count per bucket | - | The average total replication rule count | Y | sum(all replication rule count metrics)/sum(DistinctNumberOfBuckets) |
| Object Ownership bucket owner enforced bucket count | ObjectOwnershipBucketOwnerEnforcedBucketCount | The total count of buckets that have access control lists (ACLs) disabled by using the bucket owner enforced setting for Object Ownership | N | - |
| % Object Ownership bucket owner enforced buckets | - | The percentage of buckets that have ACLs disabled by using the bucket owner enforced setting for Object Ownership | Y | sum(ObjectOwnershipBucketOwnerEnforcedBucketCount)/sum(DistinctNumberOfBuckets) |
| Object Ownership bucket owner preferred bucket count | ObjectOwnershipBucketOwnerPreferredBucketCount | The total count of buckets that use the bucket owner preferred setting for Object Ownership | N | - |
| % Object Ownership bucket owner preferred buckets | - | The percentage of buckets that use the bucket owner preferred setting for Object Ownership | Y | sum(ObjectOwnershipBucketOwnerPreferredBucketCount)/sum(DistinctNumberOfBuckets) |
| Object Ownership object writer bucket count | ObjectOwnershipObjectWriterBucketCount | The total count of buckets that use the object writer setting for Object Ownership | N | - |
| % Object Ownership object writer buckets | - | The percentage of buckets that use the object writer setting for Object Ownership | Y | sum(ObjectOwnershipObjectWriterBucketCount)/sum(DistinctNumberOfBuckets) |
| Transfer Acceleration enabled bucket count | TransferAccelerationEnabledBucketCount | The total count of buckets that have Transfer Acceleration enabled | N | - |
| % Transfer Acceleration enabled buckets | - | The percentage of buckets that have Transfer Acceleration enabled | Y | sum(TransferAccelerationEnabledBucketCount)/sum(DistinctNumberOfBuckets) |
| Event Notification enabled bucket count | EventNotificationEnabledBucketCount | The total count of buckets that have Event Notifications enabled | N | - |
| % Event Notification enabled buckets | - | The percentage of buckets that have Event Notifications enabled | Y | sum(EventNotificationEnabledBucketCount)/sum(DistinctNumberOfBuckets) |
| All requests | AllRequests | The total number of requests made | N | - |
| Get requests | GetRequests | The total number of GET requests made | N | - |
| Put requests | PutRequests | The total number of PUT requests made | N | - |
| Head requests | HeadRequests | The total number of HEAD requests made | N | - |
| Delete requests | DeleteRequests | The total number of DELETE requests made | N | - |
| List requests | ListRequests | The total number of LIST requests made | N | - |
| Post requests | PostRequests | The total number of POST requests made | N | - |
| Select requests | SelectRequests | The total number of S3 Select requests | N | - |
| Select scanned bytes | SelectScannedBytes | The number of S3 Select bytes scanned | N | - |
| Select returned bytes | SelectReturnedBytes | The number of S3 Select bytes returned | N | - |
| Bytes downloaded | BytesDownloaded | The number of bytes downloaded | N | - |
| % retrieval rate | - | The percentage of bytes downloaded | Y | sum(BytesDownloaded)/sum(StorageBytes) |
| Bytes uploaded | BytesUploaded | The number of bytes uploaded | N | - |
| % ingest ratio | - | The percentage of bytes uploaded | Y | sum(BytesUploaded)/sum(StorageBytes) |
| 4xx errors | 4xxErrors | The total number of HTTP 4xx status codes | N | - |
| 5xx errors | 5xxErrors | The total number of HTTP 5xx status codes | N | - |
| Total errors | - | The sum of all 4xx and 5xx errors | Y | sum(4xxErrors) + sum(5xxErrors) |
| % error rate | - | The total number of 4xx and 5xx errors as a percentage of total requests | Y | sum(TotalErrors)/sum(TotalRequests) |
| 200 OK status count | 200OKStatusCount | The total count of 200 OK status codes | N | - |
| % 200 OK status | - | The total number of 200 OK status codes as a percentage of total requests | Y | sum(200OKStatusCount)/sum(AllRequests) |
| 206 Partial Content status count | 206PartialContentStatusCount | The total count of 206 Partial Content status codes | N | - |
| % 206 Partial Content status | - | The total number of 206 Partial Content status codes as a percentage of total requests | Y | sum(206PartialContentStatusCount)/sum(AllRequests) |
| 400 Bad Request error count | 400BadRequestErrorCount | The total count of 400 Bad Request status codes | N | - |
| % 400 Bad Request errors | - | The total number of 400 Bad Request status codes as a percentage of total requests | Y | sum(400BadRequestErrorCount)/sum(AllRequests) |
| 403 Forbidden error count | 403ForbiddenErrorCount | The total count of 403 Forbidden status codes | N | - |
| % 403 Forbidden errors | - | The total number of 403 Forbidden status codes as a percentage of total requests | Y | sum(403ForbiddenErrorCount)/sum(AllRequests) |
| 404 Not Found error count | 404NotFoundErrorCount | The total count of 404 Not Found status codes | N | - |
| % 404 Not Found errors | - | The total number of 404 Not Found status codes as a percentage of total requests | Y | sum(404NotFoundErrorCount)/sum(AllRequests) |
| 500 Internal Server Error count | 500InternalServerErrorCount | The total count of 500 Internal Server Error status codes | N | - |
| % 500 Internal Server Errors | - | The total number of 500 Internal Server Error status codes as a percentage of total requests | Y | sum(500InternalServerErrorCount)/sum(AllRequests) |
| 503 Service Unavailable error count | 503ServiceUnavailableErrorCount | The total count of 503 Service Unavailable status codes | N | - |
| % 503 Service Unavailable errors | - | The total number of 503 Service Unavailable status codes as a percentage of total requests | Y | sum(503ServiceUnavailableErrorCount)/sum(AllRequests) |

### Legend

- **Derived**: Indicates whether the metric is calculated from other metrics (Y) or directly measured (N)
- **Name in Exported Data**: The field name used when exporting S3 Storage Lens data
- **Derived Metric Formula**: The calculation formula for derived metrics
