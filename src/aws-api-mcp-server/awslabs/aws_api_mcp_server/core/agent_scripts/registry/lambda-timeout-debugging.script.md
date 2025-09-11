---
description: Helps debug Lambda function timeout failures by analyzing function configuration, CloudWatch logs, metrics, and dependencies to identify root causes and provide actionable solutions.
---
# Lambda Timeout Debugging

## Overview

This script systematically investigates Lambda function timeout failures by analyzing function configuration, CloudWatch logs, metrics, dependencies, and code patterns. It identifies common causes of timeouts such as insufficient timeout settings, external service delays, database connection issues, memory constraints, and inefficient code patterns, then provides specific recommendations for resolution.

## Parameters

Prompt the user in a single message to provide all required parameters at once. Clearly list the required parameters and their descriptions, and include any optional parameters with their default values. Do not proceed until you have received and confirmed all required parameters. If any required parameter is missing or unclear, you MUST explicitly request the missing information before moving forward.

- **function_name** (required): The name of the Lambda function experiencing timeout issues
- **region** (required): The AWS region where the Lambda function is deployed
- **time_window_hours** (optional, default: 1): Number of hours to look back for analysis (e.g., 1, 2, 8, 12, 24, etc)
- **lambda_code** (optional): The Lambda function code to analyze for potential timeout issues. If provided, the agent will review the code, otherwise the analysis will focus on configuration and metrics only.

Only proceed to the steps below if you have all required information.

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

### 2. Get Function Configuration

Retrieve the Lambda function configuration to understand current timeout and memory settings.

**Constraints:**
- You MUST only use the `call_aws` tool with the command: `aws lambda get-function-configuration --function-name ${function_name} --region ${region}`
- You MUST extract and save the following key information:
  - Timeout setting (in seconds)
  - Memory allocation (in MB)
  - Runtime version
  - Last modified date
  - Environment variables
  - VPC configuration (if applicable)
- You MUST identify if the timeout setting is at the maximum limit (900 seconds for most functions)

### 3. Analyze CloudWatch Metrics

Examine Lambda metrics to understand timeout patterns and performance trends.

**Constraints:**
- You MUST calculate the start time for metrics analysis using the time_window_hours parameter
- You MUST only use the `call_aws` tool with the command: `aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration --dimensions Name=FunctionName,Value=${function_name} --start-time ${start_time} --end-time ${end_time} --period 3600 --statistics Average Maximum --region ${region}`
- You MUST retrieve timeout error metrics using: `aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=${function_name} --start-time ${start_time} --end-time ${end_time} --period 3600 --statistics Sum --region ${region}`
- You MUST retrieve memory utilization metrics using: `aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name MemoryUtilization --dimensions Name=FunctionName,Value=${function_name} --start-time ${start_time} --end-time ${end_time} --period 3600 --statistics Average Maximum --region ${region}`
- You MUST analyze the relationship between duration trends and timeout occurrences
- You MUST remember all metric data for correlation analysis

### 4. Check Log Group Availability

Verify the log group exists and determine the available time range for analysis.

**Constraints:**
- You MUST use the `call_aws` tool with the command: `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/${function_name} --region ${region}`
- You MUST check if the log group exists and extract its creation time and retention settings
- You MUST list available log streams using: `aws logs describe-log-streams --log-group-name /aws/lambda/${function_name} --order-by LastEventTime --descending --max-items 10 --region ${region}`
- You MUST verify that log streams exist before attempting any log queries
- You MUST calculate the effective time range based on log group retention and creation time
- You MUST adjust the analysis time window to fit within the available log data range
- You MUST inform the user if the requested time window exceeds available log data
- You MUST inform the user if no log streams are found (function may not have been invoked)
- You SHOULD use a default 7-day window if the requested window is too large

### 5. Analyze CloudWatch Logs

Search CloudWatch logs for timeout-related errors and performance patterns.

**Constraints:**
- You MUST only proceed with log analysis if log streams were found in the previous step
- You MUST derive timestamps from existing AWS response data rather than calculating independently
- You MUST use the `lastEventTimestamp` from the log streams as the reference point for time calculations
- You MUST convert the validated time window to Unix timestamps (milliseconds since epoch)
- **Timestamp Derivation Process:**
  1. Extract `lastEventTimestamp` from the log streams response (step 4)
  2. Use this as your end time for the analysis window
  3. Calculate start time by subtracting the desired time window in milliseconds:
     - For 1 hour: subtract 3600000 milliseconds
     - For 24 hours: subtract 86400000 milliseconds
     - For 7 days: subtract 604800000 milliseconds
  4. Use these derived timestamps for all CloudWatch Logs Insights queries
- You MUST use the `call_aws` tool with the command: `aws logs start-query --log-group-name /aws/lambda/${function_name} --start-time ${start_timestamp} --end-time ${end_timestamp} --query-string 'fields @timestamp, @message | filter @message like /(?i)(timeout|task timed out|duration)/ | sort @timestamp desc | limit 50' --region ${region}`
- You MUST start a separate query for error patterns: `aws logs start-query --log-group-name /aws/lambda/${function_name} --start-time ${start_timestamp} --end-time ${end_timestamp} --query-string 'fields @timestamp, @message | filter @message like /(?i)(error|exception|fail)/ | sort @timestamp desc | limit 50' --region ${region}`
- You MUST start a query for performance indicators: `aws logs start-query --log-group-name /aws/lambda/${function_name} --start-time ${start_timestamp} --end-time ${end_timestamp} --query-string 'fields @timestamp, @message | filter @message like /(?i)(start|end|duration|memory)/ | sort @timestamp desc | limit 50' --region ${region}`
- You MUST remember all query IDs for result retrieval
- You MUST handle cases where log groups don't exist or are empty
- You MUST handle MalformedQueryException errors by adjusting the time range and retrying
- You MUST handle ResourceNotFoundException errors gracefully and inform the user that no logs are available
- You MUST NOT attempt to access individual log streams directly using get-log-events commands

### 6. Wait for Log Query Results

Poll for completion and retrieve results from all CloudWatch Logs queries.

**Constraints:**
- You MUST poll each query status using: `aws logs get-query-results --query-id ${query_id} --region ${region}`
- You MUST wait for all queries to reach "Complete" status before proceeding
- You MUST handle query failures and timeouts appropriately
- You MUST save all log results for pattern analysis
- You MUST extract key patterns from timeout and error messages

### 7. Analyze Function Code (Optional)

If lambda_code parameter is provided, analyze the code for potential timeout issues.

**Constraints:**
- You MUST only perform this step if the lambda_code parameter was provided
- You MUST analyze the provided code for common timeout patterns including:
  - Synchronous external API calls without timeouts
  - Database operations without connection timeouts
  - File I/O operations that could block
  - Long-running loops or recursive operations
  - Memory-intensive operations that could cause garbage collection delays
  - Network calls without proper timeout configuration
- You MUST identify specific code patterns that could contribute to timeouts
- You MUST provide specific recommendations for code improvements
- You MUST skip this step entirely if no lambda_code is provided

### 8. Analyze Function Dependencies

Identify external dependencies that could cause timeouts.

**Constraints:**
- You MUST use the `call_aws` tool with the command: `aws lambda get-function-configuration --function-name ${function_name} --region ${region}`
- You MUST check for VPC configuration that might affect network latency
- You MUST identify any environment variables that point to external services
- You MUST examine the function's role and permissions to understand what external services it can access
- You SHOULD save dependency information for the recommendations section

### 9. Check Related AWS Services

Investigate related AWS services that might be causing delays.

**Constraints:**
- If the function uses VPC, You MUST check VPC configuration and subnet routing
- If the function connects to databases, You MUST check for RDS or DynamoDB performance issues
- If the function makes API calls, You MUST look for patterns suggesting external service delays
- You MUST use appropriate AWS CLI commands to check service health and configuration
- You MUST correlate any service issues with the timeout patterns observed in logs

### 10. Analyze Cold Start Patterns

Examine cold start behavior and its impact on timeouts.

**Constraints:**
- You MUST use the `call_aws` tool with the command: `aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name InitDuration --dimensions Name=FunctionName,Value=${function_name} --start-time ${start_time} --end-time ${end_time} --period 3600 --statistics Average Maximum --region ${region}`
- You MUST correlate cold start patterns with timeout occurrences
- You MUST check if the function has provisioned concurrency configured
- You MUST analyze the relationship between function invocations and cold starts

### 11. Generate Recommendations

Create specific, actionable recommendations based on the analysis.

**Constraints:**
- You MUST create recommendations based on the specific issues identified in the analysis
- You MUST prioritize recommendations by impact and ease of implementation
- You MUST include specific configuration changes and architectural suggestions
- You MUST provide AWS CLI commands or code examples where applicable
- If lambda_code was analyzed, You MUST include specific code improvement recommendations
- You MUST address the most common timeout causes:
  - Insufficient timeout settings
  - External service delays
  - Database connection issues
  - Memory constraints
  - Inefficient code patterns (if code was analyzed)
  - Cold start issues
  - VPC configuration problems

### 12. Compile Analysis Report

Combine all findings into a comprehensive debugging report.

**Constraints:**
- You MUST create a structured report containing:
  - Executive summary of timeout issues found
  - Function configuration analysis
  - Metrics analysis with trends and patterns
  - Log analysis with key findings
  - Dependency analysis results
  - Root cause identification
  - Prioritized recommendations with implementation steps
  - Monitoring and prevention strategies
- You MUST format the results in a clear, actionable manner
- You MUST present the results to the user in a well-organized format

## Examples

### Example Input
```
function_name: my-api-handler
region: us-east-1
time_window_hours: 48
lambda_code: |
  import requests
  import json

  def lambda_handler(event, context):
      # This could cause timeouts - no timeout set
      response = requests.get('https://api.example.com/data')
      return {
          'statusCode': 200,
          'body': json.dumps(response.json())
      }
```

### Example Output
```
# Lambda Timeout Debugging Report

**Function:** my-api-handler
**Region:** us-east-1
**Analysis Period:** Last 48 hours

## Executive Summary
- 23 timeout errors detected in the last 48 hours
- Average function duration: 8.2 seconds (approaching 10-second timeout)
- Root cause: External API calls with no timeout configuration

## Function Configuration
- Current timeout: 10 seconds
- Memory allocation: 512 MB
- Runtime: Python 3.9
- VPC configuration: Yes (may add latency)

## Key Findings
1. **External API Delays**: Function makes unoptimized calls to external APIs
2. **No Timeout Configuration**: External calls have no timeout settings
3. **Memory Pressure**: Average memory usage at 89% of allocation
4. **Cold Start Impact**: 15% of timeouts occur during cold starts
5. **Code Issues**: HTTP requests without timeout configuration in the function code

## Recommendations
1. **Immediate (High Impact)**:
   - Increase timeout to 30 seconds
   - Add timeout configuration to external API calls: `requests.get(url, timeout=10)`
   - Increase memory to 1024 MB

2. **Short-term (Medium Impact)**:
   - Implement connection pooling for external APIs
   - Add retry logic with exponential backoff
   - Configure provisioned concurrency for critical functions

3. **Long-term (Architectural)**:
   - Consider async processing for long-running operations
   - Implement circuit breaker pattern for external dependencies
   - Add comprehensive monitoring and alerting

4. **Code Improvements**:
   - Add timeout parameter to all HTTP requests
   - Implement proper error handling for network timeouts
   - Consider using async/await for I/O operations
```

## Troubleshooting

### Function Not Found
If the Lambda function doesn't exist, verify the function name and region. Use `aws lambda list-functions --region ${region}` to see available functions.

### No Logs Available
If CloudWatch logs are empty or don't exist, the function may not have been invoked recently or logging may be disabled. Check the function's log group configuration.

### Access Denied Errors
If you encounter access denied errors, verify that your AWS credentials have the necessary permissions for Lambda, CloudWatch, and related services.

### Query Timeouts
If CloudWatch Logs Insights queries timeout, reduce the time window or check if the log group contains a large volume of data. Consider running analysis during off-peak hours.

### VPC Configuration Issues
If the function is in a VPC and experiencing timeouts, check NAT gateway configuration, security group rules, and subnet routing to ensure proper internet access for external API calls.

### Log Group Time Range Issues
If you encounter MalformedQueryException errors indicating the time range exceeds log retention or is before log group creation:
- Check the log group's retention settings using `aws logs describe-log-groups`
- Adjust the time window to fit within the available log data range
- Use a shorter time window (e.g., 7 days instead of 30 days) if retention is limited
- Consider that some log groups may have very short retention periods (0-111 days as shown in the error)

### Log Stream Not Found Errors
If you encounter ResourceNotFoundException errors for log streams:
- Verify that the Lambda function has been invoked recently using `aws logs describe-log-streams`
- Check if the function is actually being called by looking at CloudWatch metrics
- Some log streams may have been deleted due to retention policies
- Do not attempt to access individual log streams directly - use CloudWatch Logs Insights queries instead
- If no log streams exist, the function may not have been invoked in the specified time range

### Timestamp Derivation Best Practices
When calculating timestamps for log analysis:
- **ALWAYS** use timestamps from existing AWS response data as your reference point
- Extract `lastEventTimestamp` from log streams to determine the most recent activity
- Calculate relative time windows by subtracting milliseconds from this reference timestamp
- **NEVER** use system calls
- Common time window calculations:
  - 1 hour = 3,600,000 milliseconds
  - 24 hours = 86,400,000 milliseconds
  - 7 days = 604,800,000 milliseconds
