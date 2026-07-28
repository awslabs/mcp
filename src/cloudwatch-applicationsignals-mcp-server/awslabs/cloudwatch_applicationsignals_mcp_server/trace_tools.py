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
import re
from .aws_clients import AWS_REGION, applicationsignals_client, logs_client, xray_client
from .sli_report_client import AWSConfig, SLIReportClient
from .utils import remove_null_values
from datetime import datetime, timedelta, timezone
from loguru import logger
from pydantic import Field
from time import perf_counter as timer
from typing import Dict, Optional


OTEL_TRACE_DATA_FORMAT = 'AWS-OTEL-TRACE-V1'

# Match @data_format only as a whole token, not as a prefix of e.g. @data_format_version.
_DATA_FORMAT_PATTERN = re.compile(r'@data_format\b', re.IGNORECASE)

_LOG_GROUP_IGNORED_REASON = (
    'The query_string contained a SOURCE clause, so CloudWatch Logs Insights does '
    "not accept a separate logGroupNames parameter. The user's SOURCE scope was used "
    'instead. Remove log_group_name or the SOURCE clause to eliminate this ambiguity.'
)


def _user_query_has_source_clause(user_query: str) -> bool:
    """Return True if the user's query begins with a SOURCE command token."""
    first_token = user_query.lstrip().split(None, 1)[:1]
    return bool(first_token) and first_token[0].lower() == 'source'


def _compose_spans_query(user_query: str, log_group_name: str) -> str:
    """Prepend SOURCE logGroups() and filterIndex @data_format clauses to a user query.

    - If the user already started the query with a SOURCE command, the query is
      returned untouched (the user has taken control of log-group scoping).
    - If the user already references @data_format anywhere, the filterIndex clause
      is not prepended (the user has taken control of the format filter). Note the
      `@data_format` check is a substring/regex match, so a stray occurrence inside
      a quoted string literal would also suppress injection — low-probability but
      worth knowing.
    - Otherwise, the SOURCE clause is prepended only when no explicit log group
      was supplied — when one is supplied, StartQuery's logGroupNames parameter
      scopes the query, so SOURCE is omitted.

    Callers must ensure `user_query` is non-empty; empty queries produce invalid
    CWL syntax and are rejected upstream at the tool entry point.
    """
    if _user_query_has_source_clause(user_query):
        return user_query

    parts = []
    if not log_group_name:
        parts.append('SOURCE logGroups()')
    if not _DATA_FORMAT_PATTERN.search(user_query):
        parts.append(f'filterIndex @data_format = "{OTEL_TRACE_DATA_FORMAT}"')
    if user_query.strip():
        parts.append(user_query)

    return ' | '.join(parts)


def check_transaction_search_enabled(region: str = AWS_REGION) -> tuple[bool, str, str]:
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
        description=(
            'Optional CloudWatch Logs log group name. If omitted, the query runs across '
            'all log groups in the account (up to the CloudWatch Logs Insights cap, '
            'currently 10,000) and is pruned via the default @data_format field index '
            'to log groups carrying AWS-OTEL-TRACE-V1 spans. Supply a log group name '
            'to avoid the account-wide scan when you already know where the spans live.'
        ),
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
    """Executes a CloudWatch Logs Insights query against trace span records stored in CloudWatch Logs with the OpenTelemetry semantic-convention schema (@data_format = "AWS-OTEL-TRACE-V1").

    Scope: only log records tagged `@data_format = "AWS-OTEL-TRACE-V1"` will match,
    so span records must follow the OpenTelemetry semantic-convention schema (e.g.
    `attributes.aws.local.service`, `attributes.aws.remote.operation`). If your spans
    are stored in some other shape or log group, pass an explicit `log_group_name`
    and include your own filter in `query_string`.

    The tool adds the `@data_format = "AWS-OTEL-TRACE-V1"` filter automatically, so
    you do not need to include it in `query_string`. You can override by providing
    your own `@data_format` reference, or take control of log-group scoping by
    starting `query_string` with a `SOURCE logGroups(...)` clause. Don't combine
    `log_group_name` with a user-supplied `SOURCE` — `log_group_name` is dropped
    and `log_group_name_ignored: True` appears in the response.

    The volume of returned logs can easily overwhelm the agent context window. Always
    include a limit in the query (| limit 50) or via the limit parameter.

    Usage:
    Write CloudWatch Logs Insights queries over OpenTelemetry span attributes
    (filter, stats, sort, limit, etc.). If source code is not accessible, consider
    querying with code-level attributes.
    ⚠️ Use CORRECT attribute names: attributes.code.file.path, attributes.code.function.name, attributes.code.line.number

    ```
    FILTER attributes.aws.local.service = "customers-service-java" and attributes.aws.local.environment = "eks:demo/default" and attributes.aws.remote.operation="InvokeModel"
    | STATS sum(`attributes.gen_ai.usage.output_tokens`) as `avg_output_tokens` by `attributes.gen_ai.request.model`, `attributes.aws.local.service`,bin(1h)
    | DISPLAY avg_output_tokens, `attributes.gen_ai.request.model`, `attributes.aws.local.service`
    ```

    Returns:
    --------
        A dictionary containing the final query results, including:
            - status: one of 'Scheduled', 'Running', 'Complete', 'Failed', 'Cancelled',
              'Polling Timeout', 'Transaction Search Not Available', 'Invalid Input'.
              'Invalid Input' is returned synchronously when query_string is empty or
              whitespace-only.
            - results: A list of the actual query results if the status is Complete.
            - statistics: Query performance statistics
            - messages: Any informational messages about the query
            - transaction_search_status: Information about transaction search availability
            - log_group_name_ignored (only when true): set when log_group_name was
              supplied but dropped because query_string already contained a SOURCE
              clause. Accompanied by log_group_name_ignored_reason.
    """
    start_time_perf = timer()
    logger.info(
        f'Starting search_transactions - log_group: {log_group_name}, start: {start_time}, end: {end_time}'
    )
    logger.debug(f'Query string: {query_string}')

    if not query_string or not query_string.strip():
        logger.warning('search_transaction_spans called with empty query_string')
        return {
            'status': 'Invalid Input',
            'message': (
                'query_string is required and must not be empty. Provide a CloudWatch '
                'Logs Insights query (e.g., "fields @timestamp, attributes.aws.local.service '
                '| limit 20").'
            ),
        }

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
                'As a fallback, you can use get_xray_trace() to look up specific traces by ID, but results may be incomplete due to sampling.'
            ),
            'fallback_recommendation': 'Use get_xray_trace() to look up specific X-Ray trace IDs (5% sampled data).',
        }

    try:
        final_query = _compose_spans_query(query_string, log_group_name)
        logger.debug(f'Composed Logs Insights query: {final_query}')

        kwargs: Dict = {
            'startTime': int(datetime.fromisoformat(start_time).timestamp()),
            'endTime': int(datetime.fromisoformat(end_time).timestamp()),
            'queryString': final_query,
            'limit': limit,
        }
        # StartQuery rejects logGroupNames when queryString already contains a
        # SOURCE clause, so let the user's SOURCE win in that case.
        log_group_name_ignored = False
        if log_group_name and not _user_query_has_source_clause(query_string):
            kwargs['logGroupNames'] = [log_group_name]
        elif log_group_name:
            log_group_name_ignored = True
            logger.warning(
                'log_group_name is ignored because query_string already specifies a SOURCE clause'
            )

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

                # Convert results to list of dictionaries
                results = [
                    {field.get('field', ''): field.get('value', '') for field in line}  # type: ignore
                    for line in response.get('results', [])
                ]

                # Check for code-level attributes following OpenTelemetry semantic conventions
                # Only supported attributes: code.file.path, code.function.name, code.line.number
                code_level_attribute_names = [
                    'code.file.path',
                    'code.function.name',
                    'code.line.number',
                ]

                # Check with both prefixed and unprefixed versions
                code_level_attributes_set = set()
                for attr in code_level_attribute_names:
                    code_level_attributes_set.add(attr)
                    code_level_attributes_set.add(f'attributes.{attr}')

                # Check if code-level attributes are requested in the query
                query_lower = query_string.lower()
                requested_in_query = any(
                    attr.lower() in query_lower or f'`{attr}`'.lower() in query_lower
                    for attr in code_level_attributes_set
                )

                # Check if any code-level attributes are present in results
                detected_attributes = set()
                for result in results:
                    for field_name in result.keys():
                        if field_name in code_level_attributes_set:
                            # Normalize attribute name (remove 'attributes.' prefix if present)
                            normalized_name = field_name.replace('attributes.', '')
                            detected_attributes.add(normalized_name)

                code_level_detected = len(detected_attributes) > 0

                # Build code-level attributes status
                code_level_status = {
                    'detected': code_level_detected,
                    'attributes_found': sorted(detected_attributes),
                    'requested_in_query': requested_in_query,
                }

                if not code_level_detected:
                    if requested_in_query:
                        # Attributes were requested but not found - instrumentation not enabled
                        code_level_status['message'] = (
                            'Code-level attributes not available in span data. '
                            'If source code is not accessible and code-level context is needed, '
                            'enable code-level attributes by setting OTEL_AWS_EXPERIMENTAL_CODE_ATTRIBUTES=true. '
                            'It is only supported in Python and requires the latest ADOT Python SDK.'
                        )
                        code_level_status['suggestion'] = (
                            'Enable code-level attributes if source code is not accessible.'
                        )
                        logger.debug(
                            'Code-level attributes requested in query but not found in data'
                        )
                else:
                    code_level_status['message'] = (
                        f'✅ Code-Level Attributes Available: {", ".join(sorted(detected_attributes))}'
                    )
                    logger.debug(
                        f'Code-level attributes detected - attributes: {", ".join(sorted(detected_attributes))}'
                    )

                result: Dict = {
                    'queryId': query_id,
                    'status': status,
                    'statistics': response.get('statistics', {}),
                    'results': results,
                    'transaction_search_status': {
                        'enabled': True,
                        'destination': 'CloudWatchLogs',
                        'status': 'ACTIVE',
                    },
                    'code_level_attributes_status': code_level_status,
                }
                if log_group_name_ignored:
                    result['log_group_name_ignored'] = True
                    result['log_group_name_ignored_reason'] = _LOG_GROUP_IGNORED_REASON
                return result

            await asyncio.sleep(1)

        elapsed_time = timer() - start_time_perf
        msg = f'Query {query_id} did not complete within {max_timeout} seconds. Use get_query_results with the returned queryId to try again to retrieve query results.'
        logger.warning(f'Query timeout after {elapsed_time:.3f}s: {msg}')
        timeout_result: Dict = {
            'queryId': query_id,
            'status': 'Polling Timeout',
            'message': msg,
        }
        if log_group_name_ignored:
            timeout_result['log_group_name_ignored'] = True
            timeout_result['log_group_name_ignored_reason'] = _LOG_GROUP_IGNORED_REASON
        return timeout_result

    except Exception as e:
        logger.error(f'Error in search_transactions: {str(e)}', exc_info=True)
        raise


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
                    region=AWS_REGION,
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


# =============================================================================
# X-Ray Trace Lookup
# =============================================================================


def _convert_otel_to_xray_trace_id(trace_id: str) -> str:
    """Convert OTel trace ID to X-Ray format.

    OTel format: "0xdeadbeefdeadbeefdeadbeefdeadbeef" (0x + 32 hex)
    X-Ray format: "1-deadbeef-deadbeefdeadbeefdeadbeef" (1-epoch8hex-random24hex)

    Also accepts X-Ray format (passthrough) and raw 32-hex-char strings.
    """
    trace_id = trace_id.strip()

    # Already X-Ray format: "1-xxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx"
    if re.match(r'^1-[0-9a-fA-F]{8}-[0-9a-fA-F]{24}$', trace_id):
        return trace_id

    # Strip "0x" prefix if present
    if trace_id.startswith('0x') or trace_id.startswith('0X'):
        trace_id = trace_id[2:]

    # Validate: must be exactly 32 hex chars
    if not re.match(r'^[0-9a-fA-F]{32}$', trace_id):
        raise ValueError(
            f'Invalid trace ID format: expected 32 hex chars (with optional 0x prefix) '
            f"or X-Ray format '1-xxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx', got: '{trace_id}'"
        )

    trace_id = trace_id.lower()
    epoch = trace_id[:8]
    random_part = trace_id[8:]
    return f'1-{epoch}-{random_part}'


def _extract_segment_summary(doc: dict, depth: int = 0) -> dict:
    """Extract a focused summary from an X-Ray segment/subsegment document.

    Recursively processes subsegments up to depth 5 to avoid excessive nesting.
    """
    start_time = doc.get('start_time', 0)
    end_time = doc.get('end_time', 0)
    duration_ms = round((end_time - start_time) * 1000, 2) if (start_time and end_time) else 0

    segment: dict = {
        'name': doc.get('name', 'unknown'),
        'duration_ms': duration_ms,
    }

    # Include type/namespace if available (identifies AWS services, HTTP calls, etc.)
    if namespace := doc.get('namespace'):
        segment['namespace'] = namespace  # "aws", "remote", etc.
    if origin := doc.get('origin'):
        segment['origin'] = origin  # "AWS::ECS::Container", etc.

    # Error/fault/throttle flags — only include when true
    if doc.get('error'):
        segment['error'] = True
    if doc.get('fault'):
        segment['fault'] = True
    if doc.get('throttle'):
        segment['throttle'] = True

    # HTTP details (method, URL, status code)
    if http := doc.get('http'):
        http_summary: dict = {}
        if req := http.get('request'):
            if method := req.get('method'):
                http_summary['method'] = method
            if url := req.get('url'):
                http_summary['url'] = url
        if resp := http.get('response'):
            if status := resp.get('status'):
                http_summary['status'] = status
        if http_summary:
            segment['http'] = http_summary

    # AWS service details (operation, table name, queue URL, etc.)
    if aws := doc.get('aws'):
        aws_summary: dict = {}
        for key in (
            'operation',
            'table_name',
            'queue_url',
            'bucket_name',
            'function_name',
            'topic_arn',
            'stream_name',
        ):
            if val := aws.get(key):
                aws_summary[key] = val
        if aws_summary:
            segment['aws'] = aws_summary

    # Cause/error details
    if cause := doc.get('cause'):
        if isinstance(cause, dict):
            exceptions = cause.get('exceptions', [])
            if exceptions:
                segment['cause'] = [
                    {
                        'type': exc.get('type', 'Unknown'),
                        'message': exc.get('message', ''),
                    }
                    for exc in exceptions[:3]  # Limit to 3 exceptions
                ]

    # SQL details
    if sql := doc.get('sql'):
        sql_summary: dict = {}
        if sanitized := sql.get('sanitized_query'):
            sql_summary['query'] = sanitized
        if db_type := sql.get('database_type'):
            sql_summary['database_type'] = db_type
        if sql_summary:
            segment['sql'] = sql_summary

    # Recurse into subsegments (cap depth at 5)
    if depth < 5:
        subsegments = doc.get('subsegments', [])
        if subsegments:
            segment['subsegments'] = [
                _extract_segment_summary(sub, depth + 1) for sub in subsegments
            ]

    return segment


def _scan_for_issues(segments: list) -> tuple:
    """Recursively scan segments for errors and faults."""
    has_errors = False
    has_faults = False
    for seg in segments:
        if seg.get('error'):
            has_errors = True
        if seg.get('fault'):
            has_faults = True
        sub_errors, sub_faults = _scan_for_issues(seg.get('subsegments', []))
        has_errors = has_errors or sub_errors
        has_faults = has_faults or sub_faults
    return has_errors, has_faults


def _parse_xray_trace(trace: dict) -> dict:
    """Parse raw X-Ray trace into agent-friendly summary.

    Focuses on extracting downstream dependency information:
    service names, durations, errors, faults, and nested subsegments.
    """
    trace_id = trace.get('Id', '')
    duration_s = trace.get('Duration', 0)

    segments = []
    for raw_segment in trace.get('Segments', []):
        doc_str = raw_segment.get('Document', '{}')
        try:
            doc = json.loads(doc_str)
        except json.JSONDecodeError:
            logger.warning(f'Failed to parse segment document for trace {trace_id}')
            continue

        segment = _extract_segment_summary(doc)
        segments.append(segment)

    has_errors, has_faults = _scan_for_issues(segments)

    return {
        'trace_id': trace_id,
        'duration_s': duration_s,
        'segments': segments,
        'has_errors': has_errors,
        'has_faults': has_faults,
    }


async def get_xray_trace(
    trace_ids: str = Field(
        ...,
        description=(
            'One or more trace IDs, comma-separated. Accepts OTel format '
            '(from telemetry_correlation.trace_id), X-Ray format, or raw hex. '
            'Maximum 5 trace IDs per call.'
        ),
    ),
) -> Dict:
    """Look up X-Ray traces to analyze downstream dependency calls and their health.

    Use this tool when investigating incidents where the root cause may be in a
    downstream dependency (external API, database, AWS service). The tool retrieves
    full X-Ray trace data showing all downstream calls with their latencies, errors,
    and fault status.

    **When to use this tool:**
    - After `get_incident_root_cause()` when the call_tree shows time spent in an external
      call (HTTP client, AWS SDK, database driver)
    - When investigating SLO breaches that may correlate with downstream service degradation
    - When `telemetry_correlation.trace_id` is available in incident data

    **Trace ID format:**
    Accepts trace IDs in any of these formats:
    - OTel format from incident data: "0xdeadbeefdeadbeefdeadbeefdeadbeef"
    - X-Ray format: "1-deadbeef-deadbeefdeadbeefdeadbeef"
    - Raw 32-char hex: "deadbeefdeadbeefdeadbeefdeadbeef"

    **Workflow:**
    1. Get incident details: `get_incident_root_cause(snapshot_id)` -> note `telemetry_correlation.trace_id`
    2. Look up the trace: `get_xray_trace(trace_ids="<trace_id from step 1>")`
    3. Analyze the dependency tree for errors, faults, and latency bottlenecks
    4. If a downstream service segment shows errors/faults/high latency and is an instrumented
       service (not a managed AWS service like DynamoDB/S3), drill down into that service:
       - Use `get_recent_incidents(service_name="<downstream_service_name>", endpoint="<operation>")` to
         find incidents on the downstream service
       - Use `get_incident_root_cause(snapshot_id)` on the downstream incident for code-level root cause
       - Repeat steps 1-4 to follow the dependency chain until you reach the true root cause

    **Interpreting segments:**
    - Segments with `namespace: "aws"` are AWS managed services (DynamoDB, S3, SQS, etc.) —
      check `aws.operation`, `cause`, and `http.status` for errors. No further drill-down available.
    - Segments with `namespace: "remote"` are calls to other services — if the service is
      instrumented, you can drill down using `get_recent_incidents(service_name=<segment name>)`.
    - Look for segments with `fault: true` (5xx), `error: true` (4xx), or `throttle: true`
      to identify the problematic dependency.

    **Important:** X-Ray uses sampling (typically 5%), so the trace may not be available
    if it was not sampled. If `unprocessed_trace_ids` is non-empty, those traces were
    not found in X-Ray. Use `search_transaction_spans()` for 100% sampled data if
    Transaction Search is enabled.

    Args:
        trace_ids: One or more trace IDs, comma-separated. Accepts OTel format
            (from telemetry_correlation.trace_id), X-Ray format, or raw hex.
            Maximum 5 trace IDs per call.

    Returns:
        Dictionary with:
        - traces: List of trace summaries, each containing:
            - trace_id: X-Ray trace ID
            - duration_s: Total trace duration in seconds
            - segments: List of service segments with name, duration_ms,
              error/fault/throttle flags, http details, aws service details,
              cause (exceptions), sql details, and nested subsegments
            - has_errors: True if any segment has errors
            - has_faults: True if any segment has faults (5xx)
        - unprocessed_trace_ids: Trace IDs not found (not sampled by X-Ray)
        - trace_id_conversions: Mapping of original input -> X-Ray format (when conversion occurred)
    """
    start_time_perf = timer()

    # Parse comma-separated trace IDs
    raw_ids = [tid.strip() for tid in trace_ids.split(',') if tid.strip()]

    if not raw_ids:
        return {'error': 'No trace IDs provided. Pass one or more trace IDs (comma-separated).'}

    if len(raw_ids) > 5:
        return {
            'error': f'Too many trace IDs ({len(raw_ids)}). Maximum 5 per call. '
            'Split into multiple calls if needed.',
        }

    # Convert all trace IDs to X-Ray format
    xray_ids = []
    conversions = {}
    for raw_id in raw_ids:
        try:
            xray_id = _convert_otel_to_xray_trace_id(raw_id)
            xray_ids.append(xray_id)
            conversions[raw_id] = xray_id
        except ValueError as e:
            return {'error': str(e)}

    logger.info(f'Looking up {len(xray_ids)} X-Ray trace(s): {xray_ids}')

    try:
        response = xray_client.batch_get_traces(TraceIds=xray_ids)

        traces = []
        for trace in response.get('Traces', []):
            trace_summary = _parse_xray_trace(trace)  # type: ignore[arg-type]
            traces.append(trace_summary)

        unprocessed = response.get('UnprocessedTraceIds', [])

        elapsed = timer() - start_time_perf
        logger.info(
            f'X-Ray trace lookup completed in {elapsed:.3f}s: '
            f'{len(traces)} found, {len(unprocessed)} unprocessed'
        )

        result: dict = {
            'traces': traces,
            'unprocessed_trace_ids': unprocessed,
        }

        # Only include conversions if any input was not already X-Ray format
        if any(k != v for k, v in conversions.items()):
            result['trace_id_conversions'] = conversions

        if unprocessed:
            result['note'] = (
                f'{len(unprocessed)} trace(s) not found in X-Ray. '
                'This is normal — X-Ray samples approximately 5% of traces. '
                'Use search_transaction_spans() for 100% sampled data if Transaction Search is enabled.'
            )

        return result

    except Exception as e:
        logger.error(f'Error looking up X-Ray traces: {str(e)}', exc_info=True)
        raise
