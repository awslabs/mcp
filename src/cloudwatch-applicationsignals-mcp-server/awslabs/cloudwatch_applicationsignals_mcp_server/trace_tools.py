# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""CloudWatch Application Signals MCP Server - Trace and logging tools."""

import asyncio
import json
from .aws_clients import applicationsignals_client, logs_client, xray_client
from .sli_report_client import AWSConfig, SLIReportClient
from .utils import remove_null_values
from datetime import datetime, timedelta, timezone
from loguru import logger
from pydantic import Field
from time import perf_counter as timer
from typing import Dict, Optional


def get_trace_summaries_paginated(
    xray_client, start_time, end_time, filter_expression, max_traces: int = 100
) -> list:
    """Get trace summaries with pagination to avoid exceeding response size limits.

    Args:
        xray_client: Boto3 X-Ray client
        start_time: Start time for trace query
        end_time: End time for trace query
        filter_expression: X-Ray filter expression
        max_traces: Maximum number of traces to retrieve (default 100)

    Returns:
        List of trace summaries
    """
    all_traces = []
    next_token = None
    logger.debug(
        f'Starting paginated trace retrieval - filter: {filter_expression}, max_traces: {max_traces}'
    )

    try:
        while len(all_traces) < max_traces:
            # Build request parameters
            kwargs = {
                'StartTime': start_time,
                'EndTime': end_time,
                'FilterExpression': filter_expression,
                'Sampling': True,
                'TimeRangeType': 'Service',
            }

            if next_token:
                kwargs['NextToken'] = next_token

            # Make request
            response = xray_client.get_trace_summaries(**kwargs)

            # Add traces from this page
            traces = response.get('TraceSummaries', [])
            all_traces.extend(traces)
            logger.debug(
                f'Retrieved {len(traces)} traces in this page, total so far: {len(all_traces)}'
            )

            # Check if we have more pages
            next_token = response.get('NextToken')
            if not next_token:
                break

            # If we've collected enough traces, stop
            if len(all_traces) >= max_traces:
                all_traces = all_traces[:max_traces]
                break

        logger.info(f'Successfully retrieved {len(all_traces)} traces')
        return all_traces

    except Exception as e:
        # Return what we have so far if there's an error
        logger.error(f'Error during paginated trace retrieval: {str(e)}', exc_info=True)
        logger.info(f'Returning {len(all_traces)} traces retrieved before error')
        return all_traces


def check_transaction_search_enabled(region: str = 'us-east-1') -> tuple[bool, str, str]:
    """Internal function to check if AWS X-Ray Transaction Search is enabled.

    Returns:
        tuple: (is_enabled: bool, destination: str, status: str)
    """
    try:
        response = xray_client.get_trace_segment_destination()

        destination = response.get('Destination', 'Unknown')
        status = response.get('Status', 'Unknown')

        is_enabled = destination == 'CloudWatchLogs' and status == 'ACTIVE'
        logger.debug(
            f'Transaction Search check - Enabled: {is_enabled}, Destination: {destination}, Status: {status}'
        )

        return is_enabled, destination, status

    except Exception as e:
        logger.error(f'Error checking transaction search status: {str(e)}')
        return False, 'Unknown', 'Error'


async def search_transaction_spans(
    log_group_name: str = Field(
        default='',
        description='CloudWatch log group name (defaults to "aws/spans" if not provided)',
    ),
    start_time: str = Field(
        default='', description='Start time in ISO 8601 format (e.g., "2025-04-19T20:00:00+00:00")'
    ),
    end_time: str = Field(
        default='', description='End time in ISO 8601 format (e.g., "2025-04-19T21:00:00+00:00")'
    ),
    query_string: str = Field(default='', description='CloudWatch Logs Insights query string'),
    limit: Optional[int] = Field(default=None, description='Maximum number of results to return'),
    max_timeout: int = Field(
        default=30, description='Maximum time in seconds to wait for query completion'
    ),
) -> Dict:
    """Executes a CloudWatch Logs Insights query for transaction search (100% sampled trace data).

    IMPORTANT: If log_group_name is not provided use 'aws/spans' as default cloudwatch log group name.
    The volume of returned logs can easily overwhelm the agent context window. Always include a limit in the query
    (| limit 50) or using the limit parameter.

    Usage:
    "aws/spans" log group stores OpenTelemetry Spans data with many attributes for all monitored services.
    This provides 100% sampled data vs X-Ray's 5% sampling, giving more accurate results.
    User can write CloudWatch Logs Insights queries to group, list attribute with sum, avg.

    ```
    FILTER attributes.aws.local.service = "customers-service-java" and attributes.aws.local.environment = "eks:demo/default" and attributes.aws.remote.operation="InvokeModel"
    | STATS sum(`attributes.gen_ai.usage.output_tokens`) as `avg_output_tokens` by `attributes.gen_ai.request.model`, `attributes.aws.local.service`,bin(1h)
    | DISPLAY avg_output_tokens, `attributes.gen_ai.request.model`, `attributes.aws.local.service`
    ```

    Returns:
    --------
        A dictionary containing the final query results, including:
            - status: The current status of the query (e.g., Scheduled, Running, Complete, Failed, etc.)
            - results: A list of the actual query results if the status is Complete.
            - statistics: Query performance statistics
            - messages: Any informational messages about the query
            - transaction_search_status: Information about transaction search availability
    """
    start_time_perf = timer()
    logger.info(
        f'Starting search_transactions - log_group: {log_group_name}, start: {start_time}, end: {end_time}'
    )
    logger.debug(f'Query string: {query_string}')

    # Check if transaction search is enabled
    is_enabled, destination, status = check_transaction_search_enabled()

    if not is_enabled:
        logger.warning(
            f'Transaction Search not enabled - Destination: {destination}, Status: {status}'
        )
        return {
            'status': 'Transaction Search Not Available',
            'transaction_search_status': {
                'enabled': False,
                'destination': destination,
                'status': status,
            },
            'message': (
                '⚠️ Transaction Search is not enabled for this account. '
                f'Current configuration: Destination={destination}, Status={status}. '
                "Transaction Search requires sending traces to CloudWatch Logs (destination='CloudWatchLogs' and status='ACTIVE'). "
                'Without Transaction Search, you only have access to 5% sampled trace data through X-Ray. '
                'To get 100% trace visibility, please enable Transaction Search in your X-Ray settings. '
                'As a fallback, you can use query_sampled_traces() but results may be incomplete due to sampling.'
            ),
            'fallback_recommendation': 'Use query_sampled_traces() with X-Ray filter expressions for 5% sampled data.',
        }

    try:
        # Use default log group if none provided
        if not log_group_name:
            log_group_name = 'aws/spans'
            logger.debug('Using default log group: aws/spans')

        # Start query
        kwargs = {
            'startTime': int(datetime.fromisoformat(start_time).timestamp()),
            'endTime': int(datetime.fromisoformat(end_time).timestamp()),
            'queryString': query_string,
            'logGroupNames': [log_group_name],
            'limit': limit,
        }

        logger.debug(f'Starting CloudWatch Logs query with limit: {limit}')
        start_response = logs_client.start_query(**remove_null_values(kwargs))
        query_id = start_response['queryId']
        logger.info(f'Started CloudWatch Logs query with ID: {query_id}')

        # Seconds
        poll_start = timer()
        while poll_start + max_timeout > timer():
            response = logs_client.get_query_results(queryId=query_id)
            status = response['status']

            if status in {'Complete', 'Failed', 'Cancelled'}:
                elapsed_time = timer() - start_time_perf
                logger.info(
                    f'Query {query_id} finished with status {status} in {elapsed_time:.3f}s'
                )

                if status == 'Failed':
                    logger.error(f'Query failed: {response.get("statistics", {})}')
                elif status == 'Complete':
                    logger.debug(f'Query returned {len(response.get("results", []))} results')

                return {
                    'queryId': query_id,
                    'status': status,
                    'statistics': response.get('statistics', {}),
                    'results': [
                        {field.get('field', ''): field.get('value', '') for field in line}  # type: ignore
                        for line in response.get('results', [])
                    ],
                    'transaction_search_status': {
                        'enabled': True,
                        'destination': 'CloudWatchLogs',
                        'status': 'ACTIVE',
                        'message': '✅ Using 100% sampled trace data from Transaction Search',
                    },
                }

            await asyncio.sleep(1)

        elapsed_time = timer() - start_time_perf
        msg = f'Query {query_id} did not complete within {max_timeout} seconds. Use get_query_results with the returned queryId to try again to retrieve query results.'
        logger.warning(f'Query timeout after {elapsed_time:.3f}s: {msg}')
        return {
            'queryId': query_id,
            'status': 'Polling Timeout',
            'message': msg,
        }

    except Exception as e:
        logger.error(f'Error in search_transactions: {str(e)}', exc_info=True)
        raise


async def query_sampled_traces(
    start_time: Optional[str] = Field(
        default=None,
        description='Start time in ISO format (e.g., "2024-01-01T00:00:00Z"). Defaults to 3 hours ago',
    ),
    end_time: Optional[str] = Field(
        default=None,
        description='End time in ISO format (e.g., "2024-01-01T01:00:00Z"). Defaults to current time',
    ),
    filter_expression: Optional[str] = Field(
        default=None,
        description='X-Ray filter expression to narrow results (e.g., service("service-name"){fault = true})',
    ),
    region: Optional[str] = Field(
        default=None, description='AWS region (defaults to AWS_REGION environment variable)'
    ),
) -> str:
    """SECONDARY TRACE TOOL - Query AWS X-Ray traces (5% sampled data) for trace investigation.

    ⚠️ **IMPORTANT: Consider using audit_slos() with auditors="all" instead for comprehensive root cause analysis**

    **RECOMMENDED WORKFLOW FOR OPERATION DISCOVERY:**
    1. **Use `get_service_detail(service_name)` FIRST** to discover operations from metric dimensions
    2. **Use audit_slos() with auditors="all"** for comprehensive root cause analysis (PREFERRED)
    3. Only use this tool if you need specific trace filtering that other tools don't provide

    **RECOMMENDED WORKFLOW FOR SLO BREACH INVESTIGATION:**
    1. Use get_slo() to understand SLO configuration
    2. **Use audit_slos() with auditors="all"** for comprehensive root cause analysis (PREFERRED)
    3. Only use this tool if you need specific trace filtering that audit_slos() doesn't provide

    **WHY audit_slos() IS PREFERRED:**
    - **Comprehensive analysis**: Combines traces, logs, metrics, and dependencies
    - **Actionable recommendations**: Provides specific steps to resolve issues
    - **Integrated findings**: Correlates multiple data sources for better insights
    - **Much more effective** than individual trace analysis

    **WHY get_service_detail() IS PREFERRED FOR OPERATION DISCOVERY:**
    - **Direct operation discovery**: Operations are available in metric dimensions
    - **More reliable**: Uses Application Signals service metadata instead of sampling
    - **Comprehensive**: Shows all operations, not just those in sampled traces

    ⚠️ **LIMITATIONS OF THIS TOOL:**
    - Uses X-Ray's **5% sampled trace data** - may miss critical errors
    - **Limited context** compared to comprehensive audit tools
    - **No integrated analysis** with logs, metrics, or dependencies
    - **May miss operations** due to sampling - use get_service_detail() for complete operation discovery
    - For 100% trace visibility, enable Transaction Search and use search_transaction_spans()

    **Use this tool only when:**
    - You need specific X-Ray filter expressions not available in audit tools
    - You're doing exploratory trace analysis outside of SLO breach investigation
    - You need raw trace data for custom analysis
    - **After using get_service_detail() for operation discovery**

    **For operation discovery, use get_service_detail() instead:**
    ```
    get_service_detail(service_name='your-service-name')
    ```

    **For SLO breach root cause analysis, use audit_slos() instead:**
    ```
    audit_slos(
        slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"your-slo-name"}}}]', auditors='all'
    )
    ```

    Common filter expressions (if you must use this tool):
    - 'service("service-name"){fault = true}': Find all traces with faults (5xx errors) for a service
    - 'service("service-name")': Filter by specific service
    - 'duration > 5': Find slow requests (over 5 seconds)
    - 'http.status = 500': Find specific HTTP status codes
    - 'annotation[aws.local.operation]="GET /owners/*/lastname"': Filter by specific operation (from metric dimensions)
    - 'annotation[aws.remote.operation]="ListOwners"': Filter by remote operation name
    - Combine filters: 'service("api"){fault = true} AND annotation[aws.local.operation]="POST /visits"'

    Returns JSON with trace summaries including:
    - Trace ID for detailed investigation
    - Duration and response time
    - Error/fault/throttle status
    - HTTP information (method, status, URL)
    - Service interactions
    - User information if available
    - Exception root causes (ErrorRootCauses, FaultRootCauses, ResponseTimeRootCauses)

    **RECOMMENDATION: Use get_service_detail() for operation discovery and audit_slos() with auditors="all" for comprehensive root cause analysis instead of this tool.**

    Returns:
        JSON string containing trace summaries with error status, duration, and service details
    """
    start_time_perf = timer()

    # Use AWS_REGION environment variable if region not provided
    if not region:
        from .aws_clients import AWS_REGION

        region = AWS_REGION

    logger.info(f'Starting query_sampled_traces - region: {region}, filter: {filter_expression}')

    try:
        logger.debug('Using X-Ray client')

        # Default to past 3 hours if times not provided
        if not end_time:
            end_datetime = datetime.now(timezone.utc)
        else:
            end_datetime = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

        if not start_time:
            start_datetime = end_datetime - timedelta(hours=3)
        else:
            start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

        # Validate time window to ensure it's not too large (max 6 hours)
        time_diff = end_datetime - start_datetime
        logger.debug(
            f'Query time window: {start_datetime} to {end_datetime} ({time_diff.total_seconds() / 3600:.1f} hours)'
        )
        if time_diff > timedelta(hours=6):
            logger.warning(f'Time window too large: {time_diff.total_seconds() / 3600:.1f} hours')
            return json.dumps(
                {
                    'error': 'Time window too large. Maximum allowed is 6 hours.',
                    'requested_hours': time_diff.total_seconds() / 3600,
                },
                indent=2,
            )

        # Use pagination helper with a reasonable limit
        traces = get_trace_summaries_paginated(
            xray_client,
            start_datetime,
            end_datetime,
            filter_expression or '',
            max_traces=100,  # Limit to prevent response size issues
        )

        # Convert response to JSON-serializable format
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        # Helper function to extract fault message from root causes for deduplication
        def get_fault_message(trace_data):
            """Extract fault message from a trace for deduplication.

            Only checks FaultRootCauses (5xx server errors) since this is the primary
            use case for root cause investigation. Traces without fault messages are
            not deduplicated.
            """
            # Only check FaultRootCauses for deduplication
            root_causes = trace_data.get('FaultRootCauses', [])
            if root_causes:
                for cause in root_causes:
                    services = cause.get('Services', [])
                    for service in services:
                        exceptions = service.get('Exceptions', [])
                        if exceptions and exceptions[0].get('Message'):
                            return exceptions[0].get('Message')
            return None

        # Build trace summaries (original format)
        trace_summaries = []
        for trace in traces:
            # Create a simplified trace data structure to reduce size
            trace_data = {
                'Id': trace.get('Id'),
                'Duration': trace.get('Duration'),
                'ResponseTime': trace.get('ResponseTime'),
                'HasError': trace.get('HasError'),
                'HasFault': trace.get('HasFault'),
                'HasThrottle': trace.get('HasThrottle'),
                'Http': trace.get('Http', {}),
            }

            # Only include root causes if they exist (to save space)
            if trace.get('ErrorRootCauses'):
                trace_data['ErrorRootCauses'] = trace.get('ErrorRootCauses', [])[:3]
            if trace.get('FaultRootCauses'):
                trace_data['FaultRootCauses'] = trace.get('FaultRootCauses', [])[:3]
            if trace.get('ResponseTimeRootCauses'):
                trace_data['ResponseTimeRootCauses'] = trace.get('ResponseTimeRootCauses', [])[:3]

            # Include limited annotations for key operations
            annotations = trace.get('Annotations', {})
            if annotations:
                # Only include operation-related annotations
                filtered_annotations = {}
                for key in ['aws.local.operation', 'aws.remote.operation']:
                    if key in annotations:
                        filtered_annotations[key] = annotations[key]
                if filtered_annotations:
                    trace_data['Annotations'] = filtered_annotations

            # Include user info if available
            if trace.get('Users'):
                trace_data['Users'] = trace.get('Users', [])[:2]  # Limit to first 2 users

            # Convert any datetime objects to ISO format strings
            for key, value in trace_data.items():
                trace_data[key] = convert_datetime(value)

            trace_summaries.append(trace_data)

        # Deduplicate trace summaries by fault message
        seen_faults = {}
        deduped_trace_summaries = []

        for trace_summary in trace_summaries:
            # Check if this trace has an error
            has_issues = (
                trace_summary.get('HasError')
                or trace_summary.get('HasFault')
                or trace_summary.get('HasThrottle')
            )

            if not has_issues:
                # Always include healthy traces
                deduped_trace_summaries.append(trace_summary)
                continue

            # Extract fault message for deduplication (only checks FaultRootCauses)
            fault_msg = get_fault_message(trace_summary)

            if fault_msg and fault_msg in seen_faults:
                # Skip this trace - we already have one with the same fault message
                seen_faults[fault_msg]['count'] += 1
                logger.debug(
                    f'Skipping duplicate trace {trace_summary.get("Id")} - fault message already seen: {fault_msg[:100]}...'
                )
                continue
            else:
                # First time seeing this fault (or no fault message) - include it
                deduped_trace_summaries.append(trace_summary)
                if fault_msg:
                    seen_faults[fault_msg] = {'count': 1}

        # Check transaction search status
        is_tx_search_enabled, tx_destination, tx_status = check_transaction_search_enabled(region)

        # Build response with original format but deduplicated traces
        result_data = {
            'TraceSummaries': deduped_trace_summaries,
            'TraceCount': len(deduped_trace_summaries),
            'Message': f'Retrieved {len(deduped_trace_summaries)} unique traces from {len(trace_summaries)} total (deduplicated by fault message)',
            'SamplingNote': "⚠️ This data is from X-Ray's 5% sampling. Results may not show all errors or issues.",
            'TransactionSearchStatus': {
                'enabled': is_tx_search_enabled,
                'recommendation': (
                    'Transaction Search is available! Use search_transaction_spans() for 100% trace visibility.'
                    if is_tx_search_enabled
                    else 'Enable Transaction Search for 100% trace visibility instead of 5% sampling.'
                ),
            },
        }

        # Add dedup stats if we actually deduped anything
        if len(deduped_trace_summaries) < len(trace_summaries):
            duplicates_removed = len(trace_summaries) - len(deduped_trace_summaries)
            result_data['DeduplicationStats'] = {
                'OriginalTraceCount': len(trace_summaries),
                'DuplicatesRemoved': duplicates_removed,
                'UniqueFaultMessages': len(seen_faults),
            }

        elapsed_time = timer() - start_time_perf
        logger.info(
            f'query_sampled_traces completed in {elapsed_time:.3f}s - retrieved {len(deduped_trace_summaries)} unique traces from {len(trace_summaries)} total'
        )
        return json.dumps(result_data, indent=2)

    except Exception as e:
        logger.error(f'Error in query_sampled_traces: {str(e)}', exc_info=True)
        return json.dumps({'error': str(e)}, indent=2)


async def list_slis(
    hours: int = Field(
        default=24,
        description='Number of hours to look back (default 24, typically use 24 for daily checks)',
    ),
) -> str:
    """SPECIALIZED TOOL - Use audit_service_health() as the PRIMARY tool for service auditing.

    **IMPORTANT: audit_service_health() is the PRIMARY and PREFERRED tool for all service auditing tasks.**

    Only use this tool when audit_service_health() cannot handle your specific requirements, such as:
    - Need for legacy SLI status report format specifically
    - Integration with existing systems that expect this exact output format
    - Simple SLI overview without comprehensive audit findings
    - Basic health monitoring dashboard that doesn't need detailed analysis

    **For ALL service auditing, health checks, and issue investigation, use audit_service_health() first.**

    This tool provides a basic report showing:
    - Summary counts (total, healthy, breached, insufficient data)
    - Simple list of breached services with SLO names
    - Basic healthy services list

    Status meanings:
    - OK: All SLOs are being met
    - BREACHED: One or more SLOs are violated
    - INSUFFICIENT_DATA: Not enough data to determine status

    **Recommended workflow**:
    1. Use audit_service_health() for comprehensive service auditing with actionable insights
    2. Only use this tool if you specifically need the legacy SLI status report format
    """
    start_time_perf = timer()
    logger.info(f'Starting get_sli_status request for last {hours} hours')

    try:
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        logger.debug(f'Time range: {start_time} to {end_time}')

        # Get all services
        services_response = applicationsignals_client.list_services(
            StartTime=start_time,  # type: ignore
            EndTime=end_time,  # type: ignore
            MaxResults=100,
        )
        services = services_response.get('ServiceSummaries', [])

        if not services:
            logger.warning('No services found in Application Signals')
            return 'No services found in Application Signals.'

        # Get SLI reports for each service
        reports = []
        logger.debug(f'Generating SLI reports for {len(services)} services')
        for service in services:
            service_name = service['KeyAttributes'].get('Name', 'Unknown')
            try:
                # Create custom config with the service's key attributes
                config = AWSConfig(
                    region='us-east-1',
                    period_in_hours=hours,
                    service_name=service_name,
                    key_attributes=service['KeyAttributes'],
                )

                # Generate SLI report
                client = SLIReportClient(config)
                sli_report = client.generate_sli_report()

                # Convert to expected format
                report = {
                    'BreachedSloCount': sli_report.breached_slo_count,
                    'BreachedSloNames': sli_report.breached_slo_names,
                    'EndTime': sli_report.end_time.timestamp(),
                    'OkSloCount': sli_report.ok_slo_count,
                    'ReferenceId': {'KeyAttributes': service['KeyAttributes']},
                    'SliStatus': 'BREACHED'
                    if sli_report.sli_status == 'CRITICAL'
                    else sli_report.sli_status,
                    'StartTime': sli_report.start_time.timestamp(),
                    'TotalSloCount': sli_report.total_slo_count,
                }
                reports.append(report)

            except Exception as e:
                # Log error but continue with other services
                logger.error(
                    f'Failed to get SLI report for service {service_name}: {str(e)}', exc_info=True
                )
                # Add a report with insufficient data status
                report = {
                    'BreachedSloCount': 0,
                    'BreachedSloNames': [],
                    'EndTime': end_time.timestamp(),
                    'OkSloCount': 0,
                    'ReferenceId': {'KeyAttributes': service['KeyAttributes']},
                    'SliStatus': 'INSUFFICIENT_DATA',
                    'StartTime': start_time.timestamp(),
                    'TotalSloCount': 0,
                }
                reports.append(report)

        # Check transaction search status
        is_tx_search_enabled, tx_destination, tx_status = check_transaction_search_enabled()

        # Build response
        result = f'SLI Status Report - Last {hours} hours\n'
        result += f'Time Range: {start_time.strftime("%Y-%m-%d %H:%M")} - {end_time.strftime("%Y-%m-%d %H:%M")}\n\n'

        # Add transaction search status
        if is_tx_search_enabled:
            result += '✅ Transaction Search: ENABLED (100% trace visibility available)\n\n'
        else:
            result += '⚠️ Transaction Search: NOT ENABLED (only 5% sampled traces available)\n'
            result += f'   Current config: Destination={tx_destination}, Status={tx_status}\n'
            result += '   Enable Transaction Search for accurate root cause analysis\n\n'

        # Count by status
        status_counts = {
            'OK': sum(1 for r in reports if r['SliStatus'] == 'OK'),
            'BREACHED': sum(1 for r in reports if r['SliStatus'] == 'BREACHED'),
            'INSUFFICIENT_DATA': sum(1 for r in reports if r['SliStatus'] == 'INSUFFICIENT_DATA'),
        }

        result += 'Summary:\n'
        result += f'• Total Services: {len(reports)}\n'
        result += f'• Healthy (OK): {status_counts["OK"]}\n'
        result += f'• Breached: {status_counts["BREACHED"]}\n'
        result += f'• Insufficient Data: {status_counts["INSUFFICIENT_DATA"]}\n\n'

        # Group by status
        if status_counts['BREACHED'] > 0:
            result += '⚠️  BREACHED SERVICES:\n'
            for report in reports:
                if report['SliStatus'] == 'BREACHED':
                    name = report['ReferenceId']['KeyAttributes']['Name']
                    env = report['ReferenceId']['KeyAttributes']['Environment']
                    breached_count = report['BreachedSloCount']
                    total_count = report['TotalSloCount']
                    breached_names = report['BreachedSloNames']

                    result += f'\n• {name} ({env})\n'
                    result += f'  SLOs: {breached_count}/{total_count} breached\n'
                    if breached_names:
                        result += '  Breached SLOs:\n'
                        for slo_name in breached_names:
                            result += f'    - {slo_name}\n'

        if status_counts['OK'] > 0:
            result += '\n✅ HEALTHY SERVICES:\n'
            for report in reports:
                if report['SliStatus'] == 'OK':
                    name = report['ReferenceId']['KeyAttributes']['Name']
                    env = report['ReferenceId']['KeyAttributes']['Environment']
                    ok_count = report['OkSloCount']

                    result += f'• {name} ({env}) - {ok_count} SLO(s) healthy\n'

        if status_counts['INSUFFICIENT_DATA'] > 0:
            result += '\n❓ INSUFFICIENT DATA:\n'
            for report in reports:
                if report['SliStatus'] == 'INSUFFICIENT_DATA':
                    name = report['ReferenceId']['KeyAttributes']['Name']
                    env = report['ReferenceId']['KeyAttributes']['Environment']

                    result += f'• {name} ({env})\n'

        elapsed_time = timer() - start_time_perf
        logger.info(
            f'get_sli_status completed in {elapsed_time:.3f}s - Total: {len(reports)}, Breached: {status_counts["BREACHED"]}, OK: {status_counts["OK"]}'
        )
        return result

    except Exception as e:
        logger.error(f'Error in get_sli_status: {str(e)}', exc_info=True)
        return f'Error getting SLI status: {str(e)}'
