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
- **enable_data_events** (optional, default: false): Enable data events for S3 and Lambda (increases costs)
- **enable_insights** (optional, default: true): Enable CloudTrail Insights for anomaly detection

## Steps

### 1. Verify Dependencies

Check for required tools and warn the user if any are missing.

**Constraints:**
- You MUST verify the following tools are available in your context:
  - call_aws
- You MUST ONLY check for tool existence and MUST NOT attempt to run the tools because running tools during verification could cause unintended side effects, consume resources unnecessarily, or trigger actions before the user is ready
- You MUST inform the user about any missing tools with a clear message
- You MUST ask if the user wants to proceed anyway despite missing tools
- You MUST respect the user's decision to proceed or abort

### 2. Create S3 Bucket for CloudTrail Logs

Create a dedicated S3 bucket with proper permissions for CloudTrail log storage.

**Constraints:**
- You MUST create the S3 bucket using: `aws s3api create-bucket --bucket ${s3_bucket_name} --region ${region}`
- You MUST enable versioning: `aws s3api put-bucket-versioning --bucket ${s3_bucket_name} --versioning-configuration Status=Enabled --region ${region}`
- You MUST create and apply the CloudTrail bucket policy to allow CloudTrail service access
- You MUST handle bucket creation errors gracefully (bucket may already exist)
- You MUST verify bucket creation was successful before proceeding

### 3. Create CloudWatch Log Group

Set up CloudWatch log group for real-time log analysis.

**Constraints:**
- You MUST create the log group using: `aws logs create-log-group --log-group-name ${cloudwatch_log_group} --region ${region}`
- You MUST set retention policy: `aws logs put-retention-policy --log-group-name ${cloudwatch_log_group} --retention-in-days 90 --region ${region}`
- You MUST handle log group creation errors (may already exist)
- You MUST create IAM role for CloudTrail to write to CloudWatch Logs

### 4. Create IAM Role for CloudTrail

Create IAM role with necessary permissions for CloudTrail operations.

**Constraints:**
- You MUST create IAM role for CloudTrail service
- You MUST attach policies for S3 bucket access and CloudWatch Logs access
- You MUST use least privilege principle for permissions
- You MUST save the role ARN for trail configuration

### 5. Enable Multi-Region CloudTrail

Create and configure CloudTrail to capture events across all regions.

**Constraints:**
- You MUST create the trail using: `aws cloudtrail create-trail --name ${trail_name} --s3-bucket-name ${s3_bucket_name} --include-global-service-events --is-multi-region-trail --enable-log-file-validation --cloud-watch-logs-log-group-arn ${log_group_arn} --cloud-watch-logs-role-arn ${role_arn}`
- You MUST enable the trail: `aws cloudtrail start-logging --name ${trail_name}`
- You MUST configure event selectors if enable_data_events is true
- You MUST enable CloudTrail Insights if enable_insights is true
- You MUST verify trail status after creation

### 6. Configure Event Selectors (Optional)

Configure data events for S3 and Lambda if requested.

**Constraints:**
- You MUST only execute this step if enable_data_events parameter is true
- You MUST configure S3 and Lambda data events: `aws cloudtrail put-event-selectors --trail-name ${trail_name} --event-selectors '[{"ReadWriteType": "All","IncludeManagementEvents": true,"DataResources": [{"Type":"AWS::S3::Object", "Values": ["arn:aws:s3"]},{"Type": "AWS::Lambda::Function","Values": ["arn:aws:lambda"]}]}]'`
- You MUST inform user about additional costs for data events

### 7. Enable CloudTrail Insights (Optional)

Enable CloudTrail Insights for anomaly detection if requested.

**Constraints:**
- You MUST only execute this step if enable_insights parameter is true
- You MUST enable insights: `aws cloudtrail put-insight-selectors --trail-name ${trail_name} --insight-selectors InsightType=ApiCallRateInsight`
- You MUST inform user about additional costs for Insights

### 8. Create CloudWatch Alarms

Set up monitoring and alerting for critical CloudTrail events.

**Constraints:**
- You MUST create alarms for security-critical events:
  - Root account usage
  - Failed console logins
  - IAM policy changes
  - Security group modifications
  - CloudTrail configuration changes
- You MUST use CloudWatch metric filters to parse CloudTrail logs
- You MUST configure SNS notifications for alarms

### 9. Configure Log Analysis Queries

Create pre-built CloudWatch Logs Insights queries for common analysis tasks.

**Constraints:**
- You MUST provide queries for:
  - Failed API calls by user
  - Root account activity
  - Resource creation/deletion events
  - Cross-region API activity
  - Unusual API call patterns
- You MUST save queries for easy reuse
- You MUST provide examples of running each query

### 10. Verify Configuration

Test the CloudTrail setup and log analysis capabilities.

**Constraints:**
- You MUST verify trail is logging: `aws cloudtrail get-trail-status --name ${trail_name}`
- You MUST check CloudWatch log group is receiving events
- You MUST test sample log analysis queries
- You MUST verify S3 bucket is receiving log files
- You MUST provide status report of all components

### 11. Generate Setup Report

Create comprehensive documentation of the CloudTrail configuration.

**Constraints:**
- You MUST create a report containing:
  - Trail configuration summary
  - S3 bucket and CloudWatch setup details
  - IAM roles and permissions created
  - Monitoring and alerting configuration
  - Sample analysis queries and usage instructions
  - Cost implications and optimization recommendations
- You MUST provide maintenance and troubleshooting guidance
- You MUST include security best practices for ongoing management

## Examples

### Example Input
```
trail_name: security-audit-trail
s3_bucket_name: my-org-cloudtrail-logs-2024
region: us-east-1
cloudwatch_log_group: CloudTrail/SecurityLogs
enable_data_events: true
enable_insights: true
```

### Example Output
```
# CloudTrail Multi-Region Setup Report

**Trail Name:** security-audit-trail
**S3 Bucket:** my-org-cloudtrail-logs-2024
**CloudWatch Log Group:** CloudTrail/SecurityLogs
**Multi-Region:** Enabled
**Data Events:** Enabled
**Insights:** Enabled

## Configuration Summary
- S3 bucket created with versioning enabled
- CloudWatch log group configured with 90-day retention
- IAM role created with appropriate permissions
- Multi-region trail enabled and logging
- Data events configured for S3 and Lambda
- CloudTrail Insights enabled for anomaly detection
- CloudWatch alarms configured for security events

## Sample Analysis Queries

### Failed API Calls by User
```
fields @timestamp, sourceIPAddress, userIdentity.userName, eventName, errorCode
| filter errorCode exists
| stats count() by userIdentity.userName, errorCode
| sort count desc
```

### Root Account Activity
```
fields @timestamp, sourceIPAddress, eventName, userAgent
| filter userIdentity.type = "Root"
| sort @timestamp desc
```

### Resource Deletions
```
fields @timestamp, userIdentity.userName, eventName, sourceIPAddress
| filter eventName like /Delete/
| sort @timestamp desc
```

## Cost Implications
- **Management Events:** ~$2.00 per 100,000 events
- **Data Events:** ~$0.10 per 100,000 events (S3/Lambda)
- **Insights:** ~$0.35 per 100,000 events analyzed
- **CloudWatch Logs:** ~$0.50 per GB ingested
- **S3 Storage:** ~$0.023 per GB per month

## Next Steps
1. Monitor initial log volume and costs
2. Customize CloudWatch alarms based on your security requirements
3. Set up automated log analysis and reporting
4. Configure log forwarding to SIEM if needed
5. Review and optimize retention policies
```

## Troubleshooting

### S3 Bucket Already Exists
If the S3 bucket name is already taken, choose a different globally unique name. Consider adding timestamp or organization identifier.

### Permission Denied Errors
Ensure your AWS credentials have sufficient permissions for CloudTrail, S3, CloudWatch, and IAM operations. You may need `CloudTrailFullAccess` and `IAMFullAccess` policies.

### CloudWatch Log Group Creation Fails
If log group creation fails, check if it already exists in the region. CloudWatch log groups are region-specific.

### High Log Volume Costs
If costs are higher than expected, consider:
- Disabling data events for high-volume S3 buckets
- Reducing CloudWatch log retention period
- Using S3 lifecycle policies for log archival

### Trail Not Logging
If the trail shows as not logging:
- Verify IAM role permissions
- Check S3 bucket policy allows CloudTrail access
- Ensure trail is started with `start-logging` command

### Missing Events in CloudWatch
If events aren't appearing in CloudWatch Logs:
- Verify CloudWatch Logs role ARN is correct
- Check log group exists in the same region as trail
- Allow 5-15 minutes for initial log delivery
