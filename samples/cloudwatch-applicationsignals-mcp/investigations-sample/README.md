# Document Manager API

REST API for document management with S3 storage and DynamoDB metadata. Automatically deploys to EC2 with CloudWatch Application Signals and runs traffic generator.

## Quick Start

### Setup

```bash
./scripts/manage.sh setup document-service
```

This will:
- Create S3 buckets (documents + deployment)
- Create DynamoDB table
- Launch EC2 instance (Amazon Linux 2023, t3.micro, EC2Admin role)
- Install CloudWatch Agent
- Deploy and start application

Wait ~2 minutes after setup completes.

### Traffic Generator

```bash
# Connect via SSM
aws ssm start-session --target <INSTANCE_ID>

# Run with custom action distribution (upload, get, list, download)
cd /home/ec2-user
python3.11 scripts/traffic_generator.py -c 5 -d 300 -a 10 30 30 30  # Example

# Options: -c customers, -d duration, -a percentages (must sum to 100)
```

### Create SLOs

After running traffic generator, create SLOs for the 4 known problems:

```bash
./scripts/manage.sh setup-slos
```

This creates:
- **download-availability**: Availability SLO for download endpoint
- **list-latency**: Latency SLO for list documents with tag filters
- **upload-latency**: Latency SLO for upload with scanner
- **get-latency**: Latency SLO for get document

### Cleanup

```bash
./scripts/manage.sh cleanup
```

Deletes: EC2 instance, S3 buckets, DynamoDB table, security group, .env

## Tech Stack

FastAPI, S3, DynamoDB, Python 3.11, OpenTelemetry, CloudWatch Application Signals


## Bugs

### 1. Download Faults (GET /documents/{id}/download - get_download_url)

1. Upload creates document: `s3_key=""` (empty)
2. File uploaded to S3: `documents/{id}/file.pdf`
3. `update_document()` called BUT __can't update s3_key__ (no parameter)
4. Database still has `s3_key=""`
5. Download reads document: `s3_key=""`
6. Calls `head_object(Key="")` → __ParamValidationError__ (empty Key invalid)
7. Should __store s3_key__ on update document.

### 2. Tag Filter Inefficiency (GET /documents - list_documents)

1. List documents: `GET /documents?tags=urgent&tags=legal&tags=review`
2. `list_documents()` receives `tags=['urgent', 'legal', 'review']`
3. __Performs N separate DynamoDB scans__ (one per tag)
4. Each scan reads entire table with filter
5. Results merged and deduplicated after all scans complete
6. __Latency scales linearly__: 3 tags = 3× slower than single tag
7. Should use __single scan with OR filter expression__ instead

### 3. Scanner Service Upload Latency (POST /documents - upload_document)

1. Upload reads entire file into memory: `file_content = await file.read()`
2. __Scans file BEFORE size check__: `scan_file(filename, file_content)`
3. Scanner runtime scales with size: large files take a long time to scan
4. __Size check happens AFTER scan__: `if len(file_content) > max_upload_size`
6. __Then rejected by size limit__ (50KB max_upload_size)
7. Should __check size BEFORE scanning__ to avoid wasting time on oversized files

### 4. Overly Broad Retry Logic (GET /documents/{id} - get_document)

1. `get_document()` has retry logic: 4 attempts with exponential backoff
2. __Retries ALL ClientError exceptions__ instead of just transient errors
3. Should ONLY retry: `ProvisionedThroughputExceededException`, `ThrottlingException`
4. Oversized document IDs (3000 bytes, exceeds 2KB limit) cause `ValidationException` which __shouldn't be retried__
5. But bug retries anyway: 0.1s, 0.2s, 0.4s, 0.8s = __~1.5s wasted per invalid ID__
6. Traffic generator: ~10% of get_document calls use oversized IDs
7. Should __check error code__ before retrying: only retry transient AWS errors
