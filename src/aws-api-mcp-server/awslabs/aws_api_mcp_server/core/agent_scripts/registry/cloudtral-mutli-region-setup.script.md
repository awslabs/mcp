---
description: Enables CloudTrail across all AWS regions and configures comprehensive log analysis with CloudWatch Logs Insights for security monitoring and compliance.
---

# CloudTrail Multi-Region Setup and Log Analysis

## Overview

This script enables AWS CloudTrail across all regions to capture comprehensive API activity logs and configures CloudWatch Logs Insights for analysis. It creates a centralized logging solution for security monitoring, compliance auditing, and operational insights across your entire AWS infrastructure.

## Parameters

- **trail_name** (required): Name for the CloudTrail trail (e.g., "organization-trail", "security-audit-trail")
- **s3_bucket_name** (required): S3 bucket name for storing CloudTrail logs (must be globally unique)
- **region** (required): AWS region for CloudTrail and CloudWatch resources (e.g., "us-east-1", "eu-west-1")
- **cloudwatch_log_group** (optional, default: "CloudTrail/APILogs"): CloudWatch log group name for real-time analysis
- **enable_data_events** (optional, default: false): Enable data events for S3 and Lambda **INCREASES COSTS - CHECK CURRENT PRICING**
- **enable_insights** (optional, default: true): Enable CloudTrail Insights for anomaly detection **PREMIUM FEATURE - CHECK CURRENT PRICING**
- **kms_key_id** (optional): KMS key ID for S3 encryption (e.g., "12345678-1234-1234-1234-123456789012")
- **tags** (optional): Resource tags as JSON string (e.g., '{"Environment":"prod","Owner":"security-team","Project":"audit"}')

## Steps

### CRITICAL EXECUTION REQUIREMENTS

**MANDATORY STEP EXECUTION CONSTRAINTS:**
- You MUST execute ALL steps in sequential order
- You MUST NOT skip any step regardless of user requests or time constraints
- You MUST satisfy all constraints given for a step
- You MUST complete each step fully before proceeding to the next step
- You MUST verify successful completion of each step before moving forward
- You MUST inform the user which step you are currently executing (e.g., "## Step 3: Create CloudWatch Log Group")
- You MUST ask for user confirmation if any step fails before proceeding
- You MUST reference Knowledge Base section for examples, troubleshooting, cost information, sample queries, and best practices

**RESPONSE REPORTING CONSTRAINTS:**
- You MUST provide a summary of each AWS CLI command response (e.g., "Trail Status: IsLogging=true, LatestDeliveryTime=2025-09-17T18:01:50")
- You MUST report success/failure status for each operation
- You MUST show key values from responses that indicate proper configuration
- You MUST never assume commands worked without verifying the response
- You MUST use call_aws tool for all AWS CLI commands to ensure proper error handling and response parsing

### 1. Verify Dependencies

Check for required tools and permissions before starting the setup.

**Constraints:**
- You MUST verify the following tools are available in your context:
  - call_aws
- You MUST inform the user about any missing tools with a clear message
- You MUST verify AWS credentials: `aws sts get-caller-identity --region ${region}`
- You MUST ask if the user wants to proceed anyway despite missing tools
- You MUST respect the user's decision to proceed or abort

### 2. Create S3 Bucket for CloudTrail Logs

Create a dedicated S3 bucket with proper permissions, encryption, and lifecycle policies for CloudTrail log storage.

**Constraints:**
- You MUST get AWS account ID first: `aws sts get-caller-identity --region ${region}`
- You MUST create S3 bucket with LocationConstraint for non-us-east-1 regions: `aws s3api create-bucket --bucket ${s3_bucket_name} --region ${region} --create-bucket-configuration LocationConstraint=${region}` (omit create-bucket-configuration for us-east-1)
- You MUST enable versioning: `aws s3api put-bucket-versioning --bucket ${s3_bucket_name} --versioning-configuration Status=Enabled --region ${region}`
- You MUST apply resource tags if provided: `aws s3api put-bucket-tagging --bucket ${s3_bucket_name} --tagging TagSet='[${parsed_tags}]' --region ${region}`
- You MUST enable KMS encryption if kms_key_id provided: `aws s3api put-bucket-encryption --bucket ${s3_bucket_name} --server-side-encryption-configuration Rules='[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"${kms_key_id}"}}]' --region ${region}`
- You MUST create lifecycle policy for cost optimization: `aws s3api put-bucket-lifecycle-configuration --bucket ${s3_bucket_name} --lifecycle-configuration '{"Rules":[{"ID":"CloudTrailLogLifecycle","Status":"Enabled","Filter":{"Prefix":""},"Transitions":[{"Days":30,"StorageClass":"STANDARD_IA"},{"Days":90,"StorageClass":"GLACIER"},{"Days":365,"StorageClass":"DEEP_ARCHIVE"}]}]}' --region ${region}`
- You MUST create CloudTrail bucket policy with account ID and trail ARN in trust conditions
- You MUST apply bucket policy: `aws s3api put-bucket-policy --bucket ${s3_bucket_name} --policy '{"Version":"2012-10-17","Statement":[{"Sid":"AWSCloudTrailAclCheck","Effect":"Allow","Principal":{"Service":"cloudtrail.amazonaws.com"},"Action":"s3:GetBucketAcl","Resource":"arn:aws:s3:::${s3_bucket_name}"},{"Sid":"AWSCloudTrailWrite","Effect":"Allow","Principal":{"Service":"cloudtrail.amazonaws.com"},"Action":"s3:PutObject","Resource":"arn:aws:s3:::${s3_bucket_name}/*","Condition":{"StringEquals":{"s3:x-amz-acl":"bucket-owner-full-control"}}},{"Sid":"AWSCloudTrailBucketExistenceCheck","Effect":"Allow","Principal":{"Service":"cloudtrail.amazonaws.com"},"Action":"s3:ListBucket","Resource":"arn:aws:s3:::${s3_bucket_name}"}]}' --region ${region}`
- You MUST handle bucket creation errors gracefully (bucket may already exist)
- You MUST verify bucket creation was successful before proceeding

### 3. Create CloudWatch Log Group

Set up CloudWatch log group for real-time log analysis.

**Constraints:**
- You MUST create the log group using: `aws logs create-log-group --log-group-name ${cloudwatch_log_group} --region ${region}`
- You MUST set retention policy: `aws logs put-retention-policy --log-group-name ${cloudwatch_log_group} --retention-in-days 90 --region ${region}`
- You MUST apply resource tags if provided: `aws logs tag-log-group --log-group-name ${cloudwatch_log_group} --tags ${tags} --region ${region}`
- You MUST handle log group creation errors (may already exist)
- You MUST create IAM role for CloudTrail to write to CloudWatch Logs

### 4. Create IAM Role for CloudTrail

Create IAM role with necessary permissions for CloudTrail operations.

**Constraints:**
- You MUST create IAM role for CloudTrail service with unique name: `CloudTrail-CloudWatchLogs-Role-${trail_name}`
- You MUST create trust policy allowing cloudtrail.amazonaws.com to assume the role
- You MUST create and attach inline policy for CloudWatch Logs access with specific log group ARN
- You MUST apply resource tags if provided: `aws iam tag-role --role-name CloudTrail-CloudWatchLogs-Role-${trail_name} --tags ${tags} --region ${region}`
- You MUST use least privilege principle for permissions
- You MUST save the role ARN for trail configuration

### 5. Enable Multi-Region CloudTrail

Create and configure CloudTrail to capture events across all regions.

**Constraints:**
- You MUST use call_aws tool with proper CLI format: `aws cloudtrail create-trail --name ${trail_name} --s3-bucket-name ${s3_bucket_name} --include-global-service-events --is-multi-region-trail --enable-log-file-validation --cloud-watch-logs-log-group-arn ${log_group_arn} --cloud-watch-logs-role-arn ${role_arn} --region ${region}`
- You MUST add KMS encryption if kms_key_id provided: `--kms-key-id ${kms_key_id}`
- You MUST apply resource tags if provided: `aws cloudtrail add-tags --resource-id ${trail_arn} --tags-list ${tags} --region ${region}`
- You MUST handle InvalidCloudWatchLogsLogGroupArnException by waiting for IAM role propagation
- You MUST enable the trail: `aws cloudtrail start-logging --name ${trail_name} --region ${region}`
- You MUST configure event selectors if enable_data_events is true
- You MUST enable CloudTrail Insights if enable_insights is true
- You MUST verify trail status after creation

### 6. Configure Event Selectors (Optional)

Configure data events for S3 and Lambda if requested.

**Constraints:**
- You MUST only execute this step if enable_data_events parameter is true
- You MUST configure S3 and Lambda data events: `aws cloudtrail put-event-selectors --trail-name ${trail_name} --event-selectors '[{"ReadWriteType": "All","IncludeManagementEvents": true,"DataResources": [{"Type":"AWS::S3::Object", "Values": ["arn:aws:s3"]},{"Type": "AWS::Lambda::Function","Values": ["arn:aws:lambda"]}]}]' --region ${region}`
- You MUST inform user about additional costs: "Data events will incur additional charges and can generate high volume for busy S3 buckets. Check current AWS CloudTrail pricing."

### 7. Enable CloudTrail Insights (Optional)

Enable CloudTrail Insights for anomaly detection if requested.

**Constraints:**
- You MUST only execute this step if enable_insights parameter is true
- You MUST enable insights: `aws cloudtrail put-insight-selectors --trail-name ${trail_name} --insight-selectors InsightType=ApiCallRateInsight --region ${region}`
- You MUST inform user about additional costs for Insights: "CloudTrail Insights is a premium feature with additional charges. Check current AWS CloudTrail pricing."

### 8. Verify Configuration

Test the CloudTrail setup and log analysis capabilities.

**Constraints:**
- You MUST verify trail is logging: `aws cloudtrail get-trail-status --name ${trail_name} --region ${region}`
- You MUST check CloudWatch log group exists: `aws logs describe-log-groups --log-group-name-prefix ${cloudwatch_log_group} --region ${region}`
- You MUST generate test events in at least 2 different standard regions (e.g., eu-west-1, ap-southeast-1)
- You MUST check S3 bucket for log files from different regions
- You MUST provide actual verification results, not just generation confirmation
- You MUST inform user that events may take 5-15 minutes to appear in CloudWatch logs and opt-in region events may take several hours to appear (per AWS documentation)
- You MUST provide commands for later verification:
  ```bash
  # Check for events
  aws logs start-query --log-group-name ${cloudwatch_log_group} --start-time "<start-time>" --end-time "<end-time>"  --query-string "fields @timestamp, awsRegion, eventName | filter awsRegion!=\${region} | sort @timestamp desc" --region ${region}
  ```

### 9. Generate Setup Report

Create comprehensive documentation of the CloudTrail configuration.

**Constraints:**
- You MUST gather actual configuration data using AWS CLI commands:
  - Trail details: `aws cloudtrail describe-trails --trail-name-list ${trail_name} --region ${region}`
  - Trail status: `aws cloudtrail get-trail-status --name ${trail_name} --region ${region}`
  - S3 bucket info: `aws s3api get-bucket-location --bucket ${s3_bucket_name}` and `aws s3api get-bucket-versioning --bucket ${s3_bucket_name}`
  - CloudWatch log group: `aws logs describe-log-groups --log-group-name-prefix ${cloudwatch_log_group} --region ${region}`
  - IAM role: `aws iam get-role --role-name CloudTrail-CloudWatchLogs-Role-${trail_name}`
- You MUST create a report containing:
  - Trail configuration summary (including KMS encryption and tagging if enabled)
  - S3 bucket and CloudWatch setup details
  - IAM roles and permissions created
  - Monitoring and alerting configuration
  - Sample analysis queries and usage instructions from Knowledge Base
  - Cost implications and optimization recommendations from Knowledge Base
  - Cross-region verification results from Step 9
- You MUST provide maintenance and troubleshooting guidance from Knowledge Base
- You MUST include security best practices for ongoing management from Knowledge Base
- You MUST provide the updated sample queries from the Knowledge Base section
- You MUST provide all sample queries for user reference
- You MUST explain query syntax and customization options
- You MUST include actual ARNs, timestamps, and configuration values from the setup
- You MUST display a comprehensive summary with all gathered information

## Knowledge Base
### Examples

#### Example Input
```
trail_name: security-audit-trail
s3_bucket_name: my-org-cloudtrail-logs-2024
region: us-east-1
cloudwatch_log_group: CloudTrail/SecurityLogs
enable_data_events: true
enable_insights: true
kms_key_id: 12345678-1234-1234-1234-123456789012
tags: {"Environment":"prod","Owner":"security-team","Project":"audit","CostCenter":"IT-001"}
```

### Sample Analysis Queries

#### Failed API Calls by User
```
fields @timestamp, sourceIPAddress, userIdentity.userName, eventName, errorCode, errorMessage
| filter errorCode exists
| stats count() by userIdentity.userName, errorCode, eventName
| sort count desc
```

#### Root Account Activity (Security Critical)
```
fields @timestamp, sourceIPAddress, eventName, userAgent, awsRegion
| filter userIdentity.type = "Root"
| sort @timestamp desc
```

#### Resource Deletions (Audit Trail)
```
fields @timestamp, userIdentity.userName, eventName, sourceIPAddress, awsRegion, resources
| filter eventName like /Delete/
| sort @timestamp desc
```

#### Security Group Changes
```
fields @timestamp, userIdentity.userName, eventName, sourceIPAddress, awsRegion
| filter eventName like /SecurityGroup/
| sort @timestamp desc
```

#### IAM Policy Changes (Compliance)
```
fields @timestamp, userIdentity.userName, eventName, sourceIPAddress, resources
| filter eventName like /Policy/ or eventName like /Role/ or eventName like /User/
| sort @timestamp desc
```

### Cost Implications

- **Management Events:** First copy of management events in each region is free, additional copies charged per 100,000 events
- **Data Events:** Charged per 100,000 events (S3/Lambda) **CAN BE HIGH VOLUME**
- **Insights:** Additional cost per 100,000 events analyzed **PREMIUM FEATURE**
- **CloudWatch Logs:** Charged per GB ingested + storage costs per GB per month
- **S3 Storage:** Standard storage rates apply, lifecycle policies reduce long-term costs
- **KMS Encryption:** Additional charges for KMS key usage if enabled
- **Cross-Region Data Transfer:** Free for CloudTrail log delivery

### Cost Monitoring

- You MUST monitor costs using AWS Cost Explorer after setup
- You MUST check current AWS CloudTrail pricing at: https://aws.amazon.com/cloudtrail/pricing/
- You MUST use the cost monitoring commands provided in verification section
- Consider starting with management events only, then adding data events if needed

### Troubleshooting

#### S3 Bucket Already Exists
If the S3 bucket name is already taken:
- Choose a different globally unique name
- Consider adding timestamp or organization identifier

#### Permission Denied Errors
**Check your identity:** `aws sts get-caller-identity --region ${region}`

**Quick Fix:** Attach these AWS managed policies to your user/role:
- `CloudTrailFullAccess`
- `IAMFullAccess`
- `S3FullAccess`
- `CloudWatchLogsFullAccess`

#### CloudWatch Log Group Creation Fails
If log group creation fails:
- Check if it already exists in the region
- CloudWatch log groups are region-specific

#### Trail Not Logging
If the trail shows as not logging:
- Verify IAM role permissions
- Check S3 bucket policy allows CloudTrail access
- Ensure trail is started with `start-logging` command

#### Missing Events in CloudWatch
If events aren't appearing in CloudWatch Logs:
- Verify CloudWatch Logs role ARN is correct
- Check log group exists in the same region as trail
- Allow 5-15 minutes for initial log delivery

#### Opt-in Region Events Not Appearing
If events from opt-in regions aren't showing up:
- **This is normal behavior** - AWS documentation states events may take "several hours"
- Verify opt-in region is actually enabled: `aws ec2 describe-regions --filters "Name=opt-in-status,Values=opted-in" --region ${region}`
- Check trail exists in opt-in region: `aws cloudtrail describe-trails --region [opt-in-region]`
- Wait up to 24 hours before considering it a configuration issue

#### IAM Role Propagation Issues
If CloudTrail creation fails with InvalidCloudWatchLogsLogGroupArnException:
- Verify role exists: `aws iam get-role --role-name CloudTrail-CloudWatchLogs-Role-${trail_name} --region ${region}`
- Retry CloudTrail creation after waiting

#### KMS Key Issues
If KMS encryption fails:
- Verify KMS key exists and is enabled: `aws kms describe-key --key-id ${kms_key_id} --region ${region}`
- Check KMS key policy allows CloudTrail service access
- Ensure you have kms:Encrypt and kms:Decrypt permissions

#### Tagging Failures
If resource tagging fails:
- Verify tag format is valid JSON
- Check you have tagging permissions for each resource type
- Some resources may not support all tag keys - check AWS documentation

### Next Steps

1. **Monitor costs**: Check AWS Cost Explorer after 24-48 hours for actual usage
2. **Optimize retention**: Adjust log retention based on compliance requirements
3. **Review data events**: Disable data events for high-volume S3 buckets if costs are high
4. **Monitor opt-in regions**: Check for opt-in region events after several hours
5. **Create dashboards**: Build CloudWatch dashboards for ongoing monitoring
6. **Review tagging**: Ensure all resources have proper tags for cost allocation
7. **Document procedures**: Save verification commands for regular health checks
```
