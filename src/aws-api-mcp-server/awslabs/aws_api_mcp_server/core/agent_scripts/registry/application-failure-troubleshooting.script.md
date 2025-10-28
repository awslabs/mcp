---
description: Troubleshoots failing applications by discovering and analyzing relevant CloudWatch log groups to identify error patterns, root causes, and provide actionable solutions.
---
# Application Failure Troubleshooting

## Overview

This script provides comprehensive troubleshooting for failing applications through CloudWatch log analysis. It discovers log groups related to the application name, searches for error patterns, analyzes stack traces and exceptions, and provides specific recommendations based on the findings in the logs.

## Parameters

Prompt the user in a single message to provide all required parameters at once. Clearly list the required parameters and their descriptions, and include any optional parameters with their default values. Do not proceed until you have received and confirmed all required parameters. If any required parameter is missing or unclear, you MUST explicitly request the missing information before moving forward.

- **application_name** (required): The name of the failing application (e.g., "user-api", "payment-service", "web-app")
- **region** (required): The AWS region where the application is deployed
- **time_window_hours** (optional, default: 2): Number of hours to look back for analysis (e.g., 1, 2, 4, 8, 12, 24)

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

### 2. Discover Relevant Log Groups

Search for CloudWatch log groups that are related to the application name.

**Constraints:**
- You MUST search for log groups that contain the application name using: `aws logs describe-log-groups --region ${region}`
- You MUST filter the results to find log groups that contain the application_name in their log group name
- You MUST also search for common AWS service log group patterns that might be related:
  - `/aws/lambda/*${application_name}*`
  - `/aws/apigateway/*${application_name}*`
  - `/aws/ecs/*${application_name}*`
  - `/aws/applicationelb/*${application_name}*`
  - `*${application_name}*` (custom application log groups)
- You MUST present all discovered log groups to the user and ask them to confirm which ones are relevant to the application
- You MUST handle cases where no log groups are found and ask the user to provide specific log group names
- You MUST save the confirmed log groups for analysis
- If no relevant log groups are found, You MUST ask the user to provide specific log group names manually

### 3. Validate Log Groups and Check Availability

Verify the selected log groups exist and determine the available time range for analysis.

**Constraints:**
- You MUST validate each confirmed log group using: `aws logs describe-log-groups --log-group-name-prefix ${log_group_name} --region ${region}`
- You MUST list available log streams for each log group: `aws logs describe-log-streams --log-group-name ${log_group_name} --order-by LastEventTime --descending --max-items 10 --region ${region}`
- You MUST verify that log streams exist before attempting any log queries
- You MUST calculate the effective time range based on log retention and creation time
- You MUST extract the `lastEventTimestamp` from log streams to determine the most recent activity
- You MUST inform the user if any log groups are empty or have no recent activity
- You MUST inform the user if the requested time window exceeds available log data
- You MUST adjust the analysis time window to fit within the available log data range

### 4. Analyze Application Logs

Search CloudWatch logs for error patterns and failure indicators.

**Constraints:**
- You MUST only proceed with log analysis if log streams were found in the previous step
- You MUST derive timestamps from existing AWS response data rather than calculating independently
- You MUST use the `lastEventTimestamp` from the log streams as the reference point for time calculations
- You MUST convert the validated time window to Unix timestamps (milliseconds since epoch)
- **Timestamp Derivation Process:**
  1. Extract `lastEventTimestamp` from the log streams response (step 3)
  2. Use this as your end time for the analysis window
  3. Calculate start time by subtracting the desired time window in milliseconds
  4. Use these derived timestamps for all CloudWatch Logs Insights queries
- You MUST start queries to search for errors and failure patterns:
  - **Error Query**: `aws logs start-query --log-group-name ${log_group_name} --start-time ${start_timestamp} --end-time ${end_timestamp} --query-string 'fields @timestamp, @message | filter @message like /(?i)(error|fail|exception|timeout|unable|denied|invalid)/ | sort @timestamp desc | limit 100' --region ${region}`
  - **Exception Query**: `aws logs start-query --log-group-name ${log_group_name} --start-time ${start_timestamp} --end-time ${end_timestamp} --query-string 'fields @timestamp, @message | filter @message like /(?i)(exception|stack trace|caused by|at .+\\.java:|at .+\\.py:)/ | sort @timestamp desc | limit 100' --region ${region}`
- You MUST remember all query IDs for result retrieval
- You MUST handle cases where log groups don't exist or are empty
- You MUST handle query errors gracefully and adjust time ranges if needed

### 5. Wait for Log Query Results

Poll for completion and retrieve results from all CloudWatch Logs queries.

**Constraints:**
- You MUST poll each query status using: `aws logs get-query-results --query-id ${query_id} --region ${region}`
- You MUST wait for all queries to reach "Complete" status before proceeding
- You MUST handle query failures and timeouts appropriately
- You MUST save all log results for pattern analysis
- You MUST extract key error patterns, stack traces, and failure indicators from the results
- You MUST identify the most frequent error messages and their timestamps

### 6. Analyze Error Patterns and Frequency

Analyze the collected log data to identify error patterns, frequency, and trends.

**Constraints:**
- You MUST categorize the errors found in the logs by type:
  - **Application Exceptions**: Unhandled exceptions, stack traces, runtime errors
  - **Connection Errors**: Network timeouts, connection failures, service unavailable
  - **Authentication/Authorization Errors**: Access denied, invalid credentials, permission errors
  - **Resource Errors**: Memory exhaustion, disk space, file system errors
  - **External Service Errors**: API call failures, timeout errors, third-party service issues
  - **Configuration Errors**: Missing configuration, invalid settings, environment issues
- You MUST count the frequency of each error type and identify the most common issues
- You MUST analyze the timing patterns to identify if errors are:
  - Consistent throughout the time period
  - Occurring in bursts or spikes
  - Correlated with specific time periods
- You MUST extract specific error messages, stack traces, and context information
- You MUST identify any correlation between different types of errors

### 7. Generate Root Cause Analysis

Identify the most likely root causes based on all collected evidence.

**Constraints:**
- You MUST prioritize root causes based on:
  - Frequency and severity of errors
  - Correlation with infrastructure metrics
  - Timing alignment with recent changes
  - Impact on user experience
- You MUST categorize issues into:
  - **Application Code Issues**: Unhandled exceptions, logic errors, resource leaks
  - **Infrastructure Issues**: Service outages, capacity limits, network problems
  - **Configuration Issues**: Incorrect settings, security group rules, timeout values
  - **Dependency Issues**: Database problems, external service failures, API limits
- You MUST provide evidence for each identified root cause
- You MUST estimate the impact and urgency of each issue

### 8. Create Actionable Recommendations

Develop specific, prioritized recommendations to resolve the application failures.

**Constraints:**
- You MUST create recommendations organized by priority and implementation complexity:
  - **Immediate Actions**: Critical fixes to stop ongoing failures
  - **Short-term Actions**: Important fixes to prevent recurrence
  - **Long-term Actions**: Architectural improvements and monitoring enhancements
- You MUST provide specific AWS CLI commands or configuration changes where applicable
- You MUST include monitoring and alerting recommendations to prevent future issues
- You MUST address the most common application failure causes:
  - Application code bugs and unhandled exceptions
  - Connection issues and timeouts
  - Resource exhaustion and capacity limits
  - Configuration errors and security issues
  - External dependency failures
  - Authentication and authorization problems
- You MUST include rollback procedures if recent changes are identified as the cause

### 9. Compile Comprehensive Report

Create a detailed troubleshooting report with findings and recommendations.

**Constraints:**
- You MUST create a structured report containing:
  - Executive summary of application failure analysis
  - Log groups analyzed and their relevance
  - Error pattern analysis with frequency and trends
  - Specific error messages and stack traces found
  - Root cause analysis based on log evidence
  - Prioritized action plan with specific steps
  - Code fixes and configuration changes recommended
  - Monitoring and alerting recommendations
- You MUST format the results in a clear, actionable manner for both technical and non-technical stakeholders
- You MUST include specific commands, configurations, and code examples where relevant
- You MUST present the results to the user in a well-organized format

## Examples

### Example Input
```
application_name: payment-service
region: us-west-2
time_window_hours: 4
```

### Example Output
```
# Application Failure Troubleshooting Report

**Application:** payment-service
**Region:** us-west-2
**Analysis Period:** Last 4 hours

## Executive Summary
- 847 errors detected across 3 log groups in the last 4 hours
- Peak error period: 2:15 PM - 2:45 PM UTC
- Primary root cause: Connection pool exhaustion (67% of errors)
- Secondary cause: Unhandled NullPointerException in validation (23% of errors)
- Tertiary cause: External service timeout (10% of errors)

## Log Groups Analyzed
- **/aws/lambda/payment-service-processor**: 456 errors (Lambda function logs)
- **/aws/lambda/payment-service-validator**: 234 errors (Validation service logs)
- **/payment-service/application**: 157 errors (Custom application logs)

## Error Pattern Analysis
### Error Frequency and Trends
- **Total errors**: 847 across all log groups
- **Error spike**: 2:15 PM - 2:45 PM (423 errors in 30 minutes)
- **Baseline errors**: 15-20 errors per hour outside spike period
- **Most affected component**: payment-service-processor (54% of errors)

### Specific Error Messages Found
1. **Connection Pool Exhaustion** (567 occurrences - 67%):
   ```
   ERROR: could not obtain a database connection within 30 seconds
   java.sql.SQLException: Connection pool exhausted
   at com.payment.db.ConnectionManager.getConnection(ConnectionManager.java:45)
   ```

2. **Null Pointer Exception in Validation** (198 occurrences - 23%):
   ```
   ERROR: NullPointerException in payment validation
   java.lang.NullPointerException: Cannot invoke "PaymentRequest.getAmount()" because "request" is null
   at com.payment.validator.PaymentValidator.validate(PaymentValidator.java:23)
   ```

3. **External Service Timeout** (82 occurrences - 10%):
   ```
   ERROR: Payment gateway timeout after 30 seconds
   java.net.SocketTimeoutException: Read timed out
   at com.payment.gateway.StripeClient.processPayment(StripeClient.java:67)
   ```

## Root Cause Analysis
### Primary Cause: Connection Pool Exhaustion
- **Evidence**: 567 "Connection pool exhausted" errors in logs, concentrated during traffic spike
- **Impact**: High - affects 67% of all errors
- **Urgency**: Critical - immediate action required
- **Location**: ConnectionManager.java:45 in payment-service-processor

### Secondary Cause: Null Pointer Exception in Validation
- **Evidence**: 198 NullPointerException errors when PaymentRequest.getAmount() is called on null object
- **Impact**: Medium - affects 23% of errors
- **Urgency**: High - code fix needed
- **Location**: PaymentValidator.java:23 in payment-service-validator

### Tertiary Cause: External Service Timeouts
- **Evidence**: 82 SocketTimeoutException errors from external API calls
- **Impact**: Low - affects 10% of errors
- **Urgency**: Medium - configuration and retry logic needed
- **Location**: StripeClient.java:67 in payment-service-processor

## Action Plan

### Immediate Actions
1. **Increase Connection Pool Size**:
   - Update ConnectionManager configuration to increase max connections from 20 to 50
   - Add connection pool monitoring and alerting
   - Deploy configuration change immediately

2. **Add Null Check in Validator**:
   ```java
   // Fix in PaymentValidator.java:23
   public void validate(PaymentRequest request) {
       if (request == null) {
           throw new IllegalArgumentException("PaymentRequest cannot be null");
       }
       // existing validation logic...
   }
   ```

3. **Increase External Service Timeout**:
   - Update client timeout from 30 to 60 seconds
   - Add retry logic with exponential backoff

### Short-term Actions
1. **Implement Proper Error Handling**: Add comprehensive try-catch blocks around connection operations
2. **Add Input Validation**: Validate all incoming requests before processing
3. **Connection Pool Monitoring**: Add CloudWatch metrics for connection pool usage
4. **Circuit Breaker Pattern**: Implement circuit breaker for external service calls

### Long-term Actions
1. **Comprehensive Testing**: Add unit tests for null input scenarios and edge cases
2. **Load Testing**: Implement load testing to identify capacity limits
3. **Monitoring Enhancement**: Add detailed application metrics and alerting

## Monitoring & Prevention
### Immediate Monitoring Setup
1. **CloudWatch Log Alarms**:
   - Alert on "Connection pool exhausted" errors >10 per hour
   - Alert on "NullPointerException" errors >5 per hour
   - Alert on "SocketTimeoutException" errors >5 per hour

2. **Custom Metrics**: Create custom metrics from log patterns for real-time monitoring

### Prevention Strategies
1. **Input Validation**: Implement comprehensive input validation at API entry points
2. **Connection Pool Monitoring**: Add metrics and alerting for database connection usage
3. **Code Quality Gates**: Implement static code analysis to catch null pointer issues
4. **Load Testing**: Regular load testing to identify capacity limits before they cause issues

## Next Steps
1. Execute immediate actions within the next hour
2. Monitor error rates for improvement
3. Schedule short-term actions for implementation
4. Review and approve long-term architectural changes
5. Set up ongoing monitoring and alerting
```

## Troubleshooting

### No Log Groups Found
If no log groups are discovered for the application name, ask the user to provide specific log group names. Common patterns include `/aws/lambda/function-name`, `/aws/apigateway/api-name`, or custom application log groups.

### No Logs Available
If CloudWatch logs are empty, check if logging is enabled for the application. Verify that the application is actually running and generating logs during the specified time window.

### Access Denied Errors
Verify AWS credentials have permissions for CloudWatch Logs service, specifically `logs:DescribeLogGroups`, `logs:DescribeLogStreams`, `logs:StartQuery`, and `logs:GetQueryResults`.

### High Volume Log Analysis
For applications with high log volumes, consider using shorter time windows (1-2 hours) or more specific log queries to avoid timeouts and improve performance.

### Query Timeouts
If CloudWatch Logs Insights queries timeout, reduce the time window or limit the number of results. Large log groups may require multiple smaller queries.

### Multi-Region Applications
For applications spanning multiple regions, run the analysis in each region separately since CloudWatch Logs are region-specific.

### Log Retention Issues
If the requested time window exceeds log retention settings, adjust the analysis period to fit within the available log data range.
