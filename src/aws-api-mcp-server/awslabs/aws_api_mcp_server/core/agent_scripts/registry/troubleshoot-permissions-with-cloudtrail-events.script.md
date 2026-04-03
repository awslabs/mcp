---
description: A comprehensive guide to analyze AWS CloudTrail logs using AWS CLI to identify the causes of permission errors, determine which actions were denied, and recommend policy changes to resolve access issues.
---

# AWS CloudTrail Permission Error Analysis Runbook

## Overview

This Agent Script provides a systematic approach to analyze AWS CloudTrail logs using `call_aws` tool to diagnose permission errors. It helps identify denied actions, affected resources, and the policy changes needed to resolve access issues.

## Parameters

- **aws_username_or_role** (required): The IAM user or role name that encountered the permission error
- **error_timeframe** (required): The time range when the permission error occurred (e.g., "2023-06-15T14:00:00Z,2023-06-15T16:00:00Z", "a day ago", "1 hour ago")
- **aws_region** (required): The AWS region where the action was attempted
- **resource_name** (optional): The name or ARN of the resource being accessed
- **aws_account_id** (optional): The AWS account ID where the error occurred
- **error_message** (optional): The actual error message received if available

**Constraints for parameter acquisition:**
- You MUST ask for all required parameters upfront in a single prompt rather than one at a time
- You MUST support multiple input methods including:
  - Direct input: Text provided directly in the conversation
  - Error message text: Text copied from the AWS Management Console or CLI error output
  - CloudTrail event details: JSON format of CloudTrail events
- You MUST confirm successful acquisition of all parameters before proceeding
- You SHOULD parse any provided error messages to extract relevant information

## Steps

### 1. Verify Dependencies

Check for required tools and warn the user if any are missing.

**Constraints:**
- You MUST verify the following tools are available in your context:
  - call_aws
- You MUST ONLY check for tool existence and MUST NOT attempt to run the tools because running tools during verification could cause unintended side effects
- You MUST inform the user about any missing tools with a clear message
- You MUST ask if the user wants to proceed anyway despite missing tools
- You MUST respect the user's decision to proceed or abort
- You MUST verify AWS CLI is properly configured with this command:
  ```
  aws sts get-caller-identity
  ```

### 2. Check CloudTrail Configuration

Verify that CloudTrail is enabled and properly configured to capture the events we need to analyze.

**Constraints:**
- You MUST check if CloudTrail is enabled in the account and region
- You MUST identify which trail captures the relevant events
- You MUST determine where CloudTrail logs are stored (S3 bucket or CloudWatch Logs)
- You SHOULD verify if the trail captures management events (which include permission errors)
- You MUST use these AWS CLI commands:
  ```
  # List all trails
  aws cloudtrail describe-trails --region <aws_region>

  # Get trail status
  aws cloudtrail get-trail-status --name <trail_name> --region <aws_region>

  # Check trail event selectors to confirm management events are logged
  aws cloudtrail get-event-selectors --trail-name <trail_name> --region <aws_region>
  ```

### 3. Query CloudTrail for Access Denied Events

Search CloudTrail logs for events with access denied errors related to the specified user or role.

**Constraints:**
- You MUST provide commands to look up CloudTrail events from both CloudTrail service and CloudWatch Logs
- You MUST filter for access denied errors using appropriate error codes
- You MUST narrow the search to the specified user/role and time range
- You MUST format the output for readability
- You MUST use these AWS CLI commands:
```
# Lookup events directly from CloudTrail (last 90 days)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=<aws_username_or_role> \
  --start-time <start_time> \
  --end-time <end_time> \
  --region <aws_region> \
  --query "Events[?contains(CloudTrailEvent, 'errorCode') || contains(CloudTrailEvent, 'AccessDenied') || contains(CloudTrailEvent, 'UnauthorizedOperation')]" \
  --output json
```

### 4. Parse and Analyze Access Denied Events

Extract key information from the CloudTrail events to understand the permission issues.

**Constraints:**
- You MUST extract the denied AWS service and action
- You MUST identify the specific resource that could not be accessed
- You MUST extract the error message and error code
- You MUST organize the findings in a structured format
```
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=<aws_username_or_role> \
  --start-time <start_time> \
  --end-time <end_time> \
  --region <aws_region> \
  --query "Events[?contains(CloudTrailEvent, 'errorCode')].{
    EventTime: EventTime,
    EventData: CloudTrailEvent
  }" \
  --output text
```

### 5. Check Current IAM Permissions

Examine the current IAM permissions for the user/role to understand what's missing.

**Constraints:**
- You MUST retrieve the IAM policies attached to the user or role
- You MUST check inline policies and managed policies
- You SHOULD examine permissions boundaries if applicable
- You MUST provide commands to check resource-based policies when relevant
- You MUST use these AWS CLI commands:
```
# Get user information and attached policies
aws iam get-user --user-name <aws_username> --region <aws_region>
aws iam list-attached-user-policies --user-name <aws_username> --region <aws_region>
aws iam list-user-policies --user-name <aws_username> --region <aws_region>

# For roles
aws iam get-role --role-name <role_name> --region <aws_region>
aws iam list-attached-role-policies --role-name <role_name> --region <aws_region>
aws iam list-role-policies --role-name <role_name> --region <aws_region>

# Get specific policy contents
aws iam get-policy --policy-arn <policy_arn> --region <aws_region>
aws iam get-policy-version --policy-arn <policy_arn> --version-id <version_id> --region <aws_region>

# Get inline policy
aws iam get-user-policy --user-name <aws_username> --policy-name <policy_name> --region <aws_region>
aws iam get-role-policy --role-name <role_name> --policy-name <policy_name> --region <aws_region>

# Check resource policies (example for S3)
aws s3api get-bucket-policy --bucket <bucket_name> --region <aws_region>
```

### 6. Check Service-Specific Resource Policies

Examine resource-based policies that might be affecting access.

**Constraints:**
- You MUST check resource policies for the specific service identified in the denied action
- You MUST provide service-specific commands for common AWS services
- You MUST translate service names from CloudTrail format (e.g., s3.amazonaws.com) to CLI service names (e.g., s3api)
- You MUST use these AWS CLI commands:
```
# S3 bucket policy
aws s3api get-bucket-policy --bucket <bucket_name> --region <aws_region>

# KMS key policy
aws kms get-key-policy --key-id <key_id> --policy-name default --region <aws_region>

# SQS queue policy
aws sqs get-queue-attributes --queue-url <queue_url> --attribute-names Policy --region <aws_region>

# SNS topic policy
aws sns get-topic-attributes --topic-arn <topic_arn> --region <aws_region>

# Lambda function policy
aws lambda get-policy --function-name <function_name> --region <aws_region>

# Secrets Manager resource policy
aws secretsmanager get-resource-policy --secret-id <secret_id> --region <aws_region>

# OpenSearch Serverless resource policy
aws opensearchserverless get-resource-policy --resource-type collection --resource-identifier <resource-name-or-id> --region <aws-region>
```

### 7. Generate Policy Recommendations

Create policy recommendations to address the permission errors.

**Constraints:**
- You MUST generate an IAM policy statement that would allow the denied action
- You MUST use the principle of least privilege (specific resources and actions)
- You MUST NOT use wildcards ("*") in resource ARNs unless absolutely necessary because they create security risks
- You MUST explain each component of the recommended policy
- You MUST provide a complete policy document that can be applied
- You MUST include policy examples like:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::example-bucket/path/to/object"
    }
  ]
}
```

### 8. Implement Policy Changes

Guide the user through implementing the policy changes to resolve the permission error.

**Constraints:**
- You MUST provide clear commands to implement the policy changes
- You MUST explain the difference between updating existing policies and creating new ones
- You MUST advise on managing policy versions for managed policies
- You MUST include commands for testing the changes
- You MUST warn about potential policy size limits
- You MUST use these AWS CLI commands:
```
# Creating a new policy
aws iam create-policy --policy-name <policy_name> --policy-document file://policy.json --region <aws_region>

# Attaching a policy to a user
aws iam attach-user-policy --user-name <aws_username> --policy-arn <policy_arn> --region <aws_region>

# Attaching a policy to a role
aws iam attach-role-policy --role-name <role_name> --policy-arn <policy_arn> --region <aws_region>

# Creating/updating an inline policy
aws iam put-user-policy --user-name <aws_username> --policy-name <policy_name> --policy-document file://policy.json --region <aws_region>
aws iam put-role-policy --role-name <role_name> --policy-name <policy_name> --policy-document file://policy.json --region <aws_region>

# Creating a new version of a managed policy
aws iam create-policy-version --policy-arn <policy_arn> --policy-document file://policy.json --set-as-default --region <aws_region>

# Updating resource policies (example for S3)
aws s3api put-bucket-policy --bucket <bucket_name> --policy file://bucket-policy.json --region <aws_region>
```

## Examples

### Example Input

```
aws_username_or_role: DataAnalystRole
error_timeframe: 2023-06-15T14:00:00Z,2023-06-15T16:00:00Z
aws_region: us-east-1
resource_name: analytics-data-bucket
error_message: User: arn:aws:iam::123456789012:role/DataAnalystRole is not authorized to perform: s3:GetObject on resource: arn:aws:s3:::analytics-data-bucket/reports/june-2023.csv
```

### Example Output

**CloudTrail Event Analysis:**

Event found:
- Event Time: 2023-06-15T14:23:17Z
- Event Source: s3.amazonaws.com
- Event Name: GetObject
- Error Code: AccessDenied
- Error Message: Access Denied
- Resource: arn:aws:s3:::analytics-data-bucket/reports/june-2023.csv

**Current IAM Configuration:**
- Role: DataAnalystRole
- Managed Policies: AmazonS3ReadOnlyAccess
- Inline Policies: None

**Issue Analysis:**
The AmazonS3ReadOnlyAccess policy allows s3:GetObject, but the bucket analytics-data-bucket might have a bucket policy restricting access.

**Bucket Policy Check:**
The bucket policy contains a condition limiting access to specific IP ranges, which is causing the access denial.

**Policy Recommendation:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::analytics-data-bucket/reports/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "<your-ip-address>/32"
        }
      }
    }
  ]
}
```

## Troubleshooting

### CloudTrail Events Not Found
If no CloudTrail events are found for the error, you should first verify that CloudTrail management events are enabled and check if you're searching in the correct region. CloudTrail only retains events for 90 days by default, so for older events, check S3 bucket archives. Also, ensure you're using the correct principal name - if actions were taken using assumed roles, search for the role session name or ARN instead.

### Multiple Access Denials for Same Action
If you see repeated access denials for the same action despite policy changes, you should check for multiple policy layers - identity policies, resource policies, SCPs, and permission boundaries. Access evaluation combines all of these, and explicit denies in any policy will override allows. Use IAM Access Analyzer to help identify which policy element is causing the restriction.

### Policy Changes Not Taking Effect
If policy changes don't resolve the issue immediately, you should remember that IAM changes can take several minutes to propagate through AWS's infrastructure. Wait 5-15 minutes after making policy changes before testing again. For immediate testing, consider creating a new role with the correct permissions instead of modifying an existing one.

### Large Number of Events to Analyze
If your CloudTrail query returns too many events to analyze effectively, you should narrow your search criteria by using more specific time ranges or additional attribute filters. Breaking the analysis into smaller time segments can make large-scale troubleshooting more manageable.
