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

"""CloudWatch Application Signals MCP Server - SLO-related tools."""

import json
from .aws_clients import applicationsignals_client
from botocore.exceptions import ClientError
from loguru import logger
from pydantic import Field
from time import perf_counter as timer


async def get_slo(
    slo_id: str = Field(..., description='The ARN or name of the SLO to retrieve'),
) -> str:
    """Get detailed information about a specific Service Level Objective (SLO).

    **RECOMMENDED WORKFLOW AFTER USING THIS TOOL:**
    After getting SLO configuration details, use `audit_slos()` with `auditors="all"` for comprehensive root cause analysis:
    - `audit_slos(slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"your-slo-name"}}}]', auditors="all")`
    - This provides deep root cause analysis with traces, logs, metrics, and dependencies
    - Much more comprehensive than using individual trace tools

    Use this tool to:
    - Get comprehensive SLO configuration details
    - Understand what metrics the SLO monitors
    - See threshold values and comparison operators
    - Extract operation names and key attributes for further investigation
    - Identify dependency configurations
    - Review attainment goals and burn rate settings

    Returns detailed information including:
    - SLO name, description, and metadata
    - Metric configuration (for period-based or request-based SLOs)
    - Key attributes and operation names
    - Metric type (LATENCY or AVAILABILITY)
    - Threshold values and comparison operators
    - Goal configuration (attainment percentage, time interval)
    - Burn rate configurations

    This tool is essential for:
    - Understanding SLO configuration before deep investigation
    - Getting the exact SLO name/ARN for use with audit_slos()
    - Identifying the metrics and thresholds being monitored
    - Planning comprehensive root cause analysis workflow

    **NEXT STEP: Use audit_slos() with auditors="all" for root cause analysis**
    """
    start_time_perf = timer()
    logger.info(f'Starting get_service_level_objective request for SLO: {slo_id}')

    try:
        response = applicationsignals_client.get_service_level_objective(Id=slo_id)
        slo = response.get('Slo', {})

        if not slo:
            logger.warning(f'No SLO found with ID: {slo_id}')
            return f'No SLO found with ID: {slo_id}'

        result = 'Service Level Objective Details\n'
        result += '=' * 50 + '\n\n'

        # Basic info
        result += f'Name: {slo.get("Name", "Unknown")}\n'
        result += f'ARN: {slo.get("Arn", "Unknown")}\n'
        if slo.get('Description'):
            result += f'Description: {slo.get("Description", "")}\n'
        result += f'Evaluation Type: {slo.get("EvaluationType", "Unknown")}\n'
        result += f'Created: {slo.get("CreatedTime", "Unknown")}\n'
        result += f'Last Updated: {slo.get("LastUpdatedTime", "Unknown")}\n\n'

        # Goal configuration
        goal = slo.get('Goal', {})
        if goal:
            result += 'Goal Configuration:\n'
            result += f'• Attainment Goal: {goal.get("AttainmentGoal", 99)}%\n'
            result += f'• Warning Threshold: {goal.get("WarningThreshold", 50)}%\n'

            interval = goal.get('Interval', {})
            if 'RollingInterval' in interval:
                rolling = interval['RollingInterval']
                result += f'• Interval: Rolling {rolling.get("Duration")} {rolling.get("DurationUnit")}\n'
            elif 'CalendarInterval' in interval:
                calendar = interval['CalendarInterval']
                result += f'• Interval: Calendar {calendar.get("Duration")} {calendar.get("DurationUnit")} starting {calendar.get("StartTime")}\n'
            result += '\n'

        # Period-based SLI
        if 'Sli' in slo:
            sli = slo['Sli']
            result += 'Period-Based SLI Configuration:\n'

            sli_metric = sli.get('SliMetric', {})
            if sli_metric:
                # Key attributes - crucial for trace queries
                key_attrs = sli_metric.get('KeyAttributes', {})
                if key_attrs:
                    result += '• Key Attributes:\n'
                    for k, v in key_attrs.items():
                        result += f'  - {k}: {v}\n'

                # Operation name - essential for trace filtering
                if sli_metric.get('OperationName'):
                    result += f'• Operation Name: {sli_metric.get("OperationName", "")}\n'
                    result += f'  (Use this in trace queries: annotation[aws.local.operation]="{sli_metric.get("OperationName", "")}")\n'

                result += f'• Metric Type: {sli_metric.get("MetricType", "Unknown")}\n'

                # MetricDataQueries - detailed metric configuration
                metric_queries = sli_metric.get('MetricDataQueries', [])
                if metric_queries:
                    result += '• Metric Data Queries:\n'
                    for query in metric_queries:
                        query_id = query.get('Id', 'Unknown')
                        result += f'  Query ID: {query_id}\n'

                        # MetricStat details
                        metric_stat = query.get('MetricStat', {})
                        if metric_stat:
                            metric = metric_stat.get('Metric', {})
                            if metric:
                                result += f'    Namespace: {metric.get("Namespace", "Unknown")}\n'
                                result += (
                                    f'    MetricName: {metric.get("MetricName", "Unknown")}\n'
                                )

                                # Dimensions - crucial for understanding what's being measured
                                dimensions = metric.get('Dimensions', [])
                                if dimensions:
                                    result += '    Dimensions:\n'
                                    for dim in dimensions:
                                        result += f'      - {dim.get("Name", "Unknown")}: {dim.get("Value", "Unknown")}\n'

                            result += (
                                f'    Period: {metric_stat.get("Period", "Unknown")} seconds\n'
                            )
                            result += f'    Stat: {metric_stat.get("Stat", "Unknown")}\n'
                            if metric_stat.get('Unit'):
                                result += f'    Unit: {metric_stat["Unit"]}\n'  # type: ignore

                        # Expression if present
                        if query.get('Expression'):
                            result += f'    Expression: {query.get("Expression", "")}\n'

                        result += f'    ReturnData: {query.get("ReturnData", True)}\n'

                # Dependency config
                dep_config = sli_metric.get('DependencyConfig', {})
                if dep_config:
                    result += '• Dependency Configuration:\n'
                    dep_attrs = dep_config.get('DependencyKeyAttributes', {})
                    if dep_attrs:
                        result += '  Key Attributes:\n'
                        for k, v in dep_attrs.items():
                            result += f'    - {k}: {v}\n'
                    if dep_config.get('DependencyOperationName'):
                        result += (
                            f'  - Dependency Operation: {dep_config["DependencyOperationName"]}\n'
                        )
                        result += f'    (Use in traces: annotation[aws.remote.operation]="{dep_config["DependencyOperationName"]}")\n'

            result += f'• Threshold: {sli.get("MetricThreshold", "Unknown")}\n'
            result += f'• Comparison: {sli.get("ComparisonOperator", "Unknown")}\n\n'

        # Request-based SLI
        if 'RequestBasedSli' in slo:
            rbs = slo['RequestBasedSli']
            result += 'Request-Based SLI Configuration:\n'

            rbs_metric = rbs.get('RequestBasedSliMetric', {})
            if rbs_metric:
                # Key attributes
                key_attrs = rbs_metric.get('KeyAttributes', {})
                if key_attrs:
                    result += '• Key Attributes:\n'
                    for k, v in key_attrs.items():
                        result += f'  - {k}: {v}\n'

                # Operation name
                if rbs_metric.get('OperationName'):
                    result += f'• Operation Name: {rbs_metric.get("OperationName", "")}\n'
                    result += f'  (Use this in trace queries: annotation[aws.local.operation]="{rbs_metric.get("OperationName", "")}")\n'

                result += f'• Metric Type: {rbs_metric.get("MetricType", "Unknown")}\n'

                # MetricDataQueries - detailed metric configuration
                metric_queries = rbs_metric.get('MetricDataQueries', [])
                if metric_queries:
                    result += '• Metric Data Queries:\n'
                    for query in metric_queries:
                        query_id = query.get('Id', 'Unknown')
                        result += f'  Query ID: {query_id}\n'

                        # MetricStat details
                        metric_stat = query.get('MetricStat', {})
                        if metric_stat:
                            metric = metric_stat.get('Metric', {})
                            if metric:
                                result += f'    Namespace: {metric.get("Namespace", "Unknown")}\n'
                                result += (
                                    f'    MetricName: {metric.get("MetricName", "Unknown")}\n'
                                )

                                # Dimensions - crucial for understanding what's being measured
                                dimensions = metric.get('Dimensions', [])
                                if dimensions:
                                    result += '    Dimensions:\n'
                                    for dim in dimensions:
                                        result += f'      - {dim.get("Name", "Unknown")}: {dim.get("Value", "Unknown")}\n'

                            result += (
                                f'    Period: {metric_stat.get("Period", "Unknown")} seconds\n'
                            )
                            result += f'    Stat: {metric_stat.get("Stat", "Unknown")}\n'
                            if metric_stat.get('Unit'):
                                result += f'    Unit: {metric_stat["Unit"]}\n'  # type: ignore

                        # Expression if present
                        if query.get('Expression'):
                            result += f'    Expression: {query.get("Expression", "")}\n'

                        result += f'    ReturnData: {query.get("ReturnData", True)}\n'

                # Dependency config
                dep_config = rbs_metric.get('DependencyConfig', {})
                if dep_config:
                    result += '• Dependency Configuration:\n'
                    dep_attrs = dep_config.get('DependencyKeyAttributes', {})
                    if dep_attrs:
                        result += '  Key Attributes:\n'
                        for k, v in dep_attrs.items():
                            result += f'    - {k}: {v}\n'
                    if dep_config.get('DependencyOperationName'):
                        result += (
                            f'  - Dependency Operation: {dep_config["DependencyOperationName"]}\n'
                        )
                        result += f'    (Use in traces: annotation[aws.remote.operation]="{dep_config["DependencyOperationName"]}")\n'

            result += f'• Threshold: {rbs.get("MetricThreshold", "Unknown")}\n'
            result += f'• Comparison: {rbs.get("ComparisonOperator", "Unknown")}\n\n'

        # Burn rate configurations
        burn_rates = slo.get('BurnRateConfigurations', [])
        if burn_rates:
            result += 'Burn Rate Configurations:\n'
            for br in burn_rates:
                result += f'• Look-back window: {br.get("LookBackWindowMinutes")} minutes\n'

        elapsed_time = timer() - start_time_perf
        logger.info(f"get_service_level_objective completed for '{slo_id}' in {elapsed_time:.3f}s")
        return result

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
        logger.error(f'AWS ClientError in get_slo: {error_code} - {error_message}')
        return f'AWS Error: {error_message}'
    except Exception as e:
        logger.error(
            f"Unexpected error in get_service_level_objective for '{slo_id}': {str(e)}",
            exc_info=True,
        )
        return f'Error: {str(e)}'


async def list_slos(
    key_attributes: str = Field(
        default='{}',
        description='JSON string of key attributes to filter SLOs (e.g., \'{"Name": "my-service", "Environment": "ecs:my-cluster"}\'. Defaults to empty object to list all SLOs.',
    ),
    include_linked_accounts: bool = Field(
        default=True, description='Whether to include SLOs from linked accounts (default: True)'
    ),
    max_results: int = Field(
        default=50, description='Maximum number of SLOs to return (default: 50, max: 50)'
    ),
) -> str:
    """List all Service Level Objectives (SLOs) in Application Signals.

    Use this tool to:
    - Get a complete list of all SLOs in your account
    - Discover SLO names and ARNs for use with other tools
    - Filter SLOs by service attributes
    - See basic SLO information including creation time and operation names

    Returns a formatted list showing:
    - SLO name and ARN
    - Associated service key attributes
    - Operation name being monitored
    - Creation timestamp
    - Total count of SLOs found

    This tool is useful for:
    - SLO discovery and inventory
    - Finding SLO names to use with get_slo() or audit_service_health()
    - Understanding what operations are being monitored
    """
    start_time_perf = timer()
    logger.debug('Starting list_slos request')

    try:
        # Parse key_attributes JSON string
        try:
            key_attrs_dict = json.loads(key_attributes) if key_attributes else {}
        except json.JSONDecodeError as e:
            return f'Error: Invalid JSON in key_attributes parameter: {str(e)}'

        # Validate max_results
        max_results = min(max(max_results, 1), 50)  # Ensure between 1 and 50

        # Build request parameters
        request_params = {
            'MaxResults': max_results,
            'IncludeLinkedAccounts': include_linked_accounts,
        }

        # Add key attributes if provided
        if key_attrs_dict:
            request_params['KeyAttributes'] = key_attrs_dict

        logger.debug(f'Listing SLOs with parameters: {request_params}')

        # Call the Application Signals API
        response = applicationsignals_client.list_service_level_objectives(**request_params)
        slo_summaries = response.get('SloSummaries', [])

        logger.debug(f'Retrieved {len(slo_summaries)} SLO summaries')

        if not slo_summaries:
            logger.info('No SLOs found matching the criteria')
            return 'No Service Level Objectives found matching the specified criteria.'

        # Build formatted response
        result = f'Service Level Objectives ({len(slo_summaries)} total):\n\n'

        for slo in slo_summaries:
            slo_name = slo.get('Name', 'Unknown')
            slo_arn = slo.get('Arn', 'Unknown')
            operation_name = slo.get('OperationName', 'N/A')
            created_time = slo.get('CreatedTime', 'Unknown')

            result += f'• SLO: {slo_name}\n'
            result += f'  ARN: {slo_arn}\n'
            result += f'  Operation: {operation_name}\n'
            result += f'  Created: {created_time}\n'

            # Add key attributes if available
            key_attrs = slo.get('KeyAttributes', {})
            if key_attrs:
                result += '  Service Attributes:\n'
                for key, value in key_attrs.items():
                    result += f'    {key}: {value}\n'

            result += '\n'

        # Add pagination info if there might be more results
        next_token = response.get('NextToken')
        if next_token:
            result += f'Note: More SLOs may be available. This response shows the first {len(slo_summaries)} results.\n'

        elapsed_time = timer() - start_time_perf
        logger.debug(
            f'list_slos completed in {elapsed_time:.3f}s - found {len(slo_summaries)} SLOs'
        )
        return result

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
        logger.error(f'AWS ClientError in list_slos: {error_code} - {error_message}')
        return f'AWS Error: {error_message}'
    except Exception as e:
        logger.error(f'Unexpected error in list_slos: {str(e)}', exc_info=True)
        return f'Error: {str(e)}'
