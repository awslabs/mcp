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

"""AWS DMS Troubleshooting MCP Server implementation."""

import boto3
import json
import os
import sys
from awslabs.aws_dms_troubleshoot_mcp_server import __version__
from botocore.config import Config
from datetime import datetime, timedelta, timezone
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Dict, Optional


# User agent configuration for AWS API calls
USER_AGENT_CONFIG = Config(
    user_agent_extra=f'awslabs/mcp/aws-dms-troubleshoot-mcp-server/{__version__}'
)

# Set up AWS region from environment variables
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_PROFILE = os.environ.get('AWS_PROFILE', 'default')

# Remove default logger and add custom configuration
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'INFO'))

# Server instructions
SERVER_INSTRUCTIONS = """AWS DMS Troubleshooting MCP Server

This server provides Root Cause Analysis (RCA) tools for AWS Database Migration Service (DMS)
post-migration troubleshooting. It helps customers diagnose and resolve replication job issues
through:

- Querying replication task status and details
- Retrieving CloudWatch logs for error analysis
- Analyzing source and target endpoints
- Network connectivity and security group diagnostics
- VPC routing and configuration analysis
- Providing recommendations based on AWS DMS best practices and documentation

**Primary Use Case: Post-Migration Troubleshooting**
- Help customers when replication jobs fail or encounter issues
- Identify root causes of CDC replication problems
- Diagnose network connectivity and security group issues
- Analyze error patterns and provide actionable recommendations

**Available Tools:**
1. `list_replication_tasks` - List all DMS replication tasks with status
2. `get_replication_task_details` - Get detailed information about a specific task
3. `get_task_cloudwatch_logs` - Retrieve CloudWatch logs for a replication task
4. `analyze_endpoint` - Analyze source or target endpoint configuration
5. `diagnose_replication_issue` - Comprehensive RCA for failed/stopped tasks
6. `get_troubleshooting_recommendations` - Get recommendations based on error patterns
7. `analyze_security_groups` - Analyze security group rules for DMS connectivity
8. `diagnose_network_connectivity` - Comprehensive network diagnostics for DMS tasks
9. `check_vpc_configuration` - Analyze VPC routing and network configuration

**AWS Permissions Required:**
- dms:DescribeReplicationTasks
- dms:DescribeReplicationInstances
- dms:DescribeEndpoints
- logs:DescribeLogStreams
- logs:GetLogEvents
- logs:FilterLogEvents
- ec2:DescribeSecurityGroups
- ec2:DescribeSecurityGroupRules
- ec2:DescribeSubnets
- ec2:DescribeRouteTables
- ec2:DescribeNetworkAcls
- ec2:DescribeVpcPeeringConnections
- ec2:DescribeTransitGatewayAttachments
- ec2:DescribeNatGateways
- ec2:DescribeInternetGateways
"""

# Initialize MCP Server
mcp = FastMCP(
    'aws-dms-troubleshoot-mcp-server',
    instructions=SERVER_INSTRUCTIONS,
    dependencies=['boto3', 'pydantic', 'loguru'],
)

# Field defaults
FIELD_AWS_REGION = Field(AWS_REGION, description='AWS region for DMS resources')
FIELD_AWS_PROFILE = Field(
    AWS_PROFILE, description='AWS profile to use (defaults to AWS_PROFILE environment variable)'
)


def get_dms_client(region: str, profile: str = 'default'):
    """Get DMS client with proper configuration."""
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('dms', config=USER_AGENT_CONFIG)


def get_logs_client(region: str, profile: str = 'default'):
    """Get CloudWatch Logs client with proper configuration."""
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('logs', config=USER_AGENT_CONFIG)


def get_ec2_client(region: str, profile: str = 'default'):
    """Get EC2 client with proper configuration."""
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client('ec2', config=USER_AGENT_CONFIG)


@mcp.tool()
async def list_replication_tasks(
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
    status_filter: Optional[str] = Field(
        None,
        description="Filter by status: 'running', 'stopped', 'failed', 'starting', 'stopping', 'creating', 'deleting', 'modifying'",
    ),
) -> Dict:
    """List all DMS replication tasks with their current status.

    This tool provides an overview of all replication tasks in the specified region,
    including their current status, progress, and basic configuration.

    Returns:
        Dictionary containing:
        - tasks: List of replication tasks with key details
        - summary: Statistics about task statuses
        - region: The region queried
    """
    try:
        logger.info(f'Listing replication tasks in region: {region}')
        dms = get_dms_client(region, aws_profile)

        # Build filters
        filters = []
        if status_filter:
            filters.append({'Name': 'replication-task-status', 'Values': [status_filter]})

        # Get replication tasks
        response = dms.describe_replication_tasks(
            Filters=filters if filters else [], MaxRecords=100
        )

        tasks = []
        status_counts = {}

        for task in response.get('ReplicationTasks', []):
            status = task.get('Status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

            task_info = {
                'task_arn': task.get('ReplicationTaskArn'),
                'task_identifier': task.get('ReplicationTaskIdentifier'),
                'status': status,
                'migration_type': task.get('MigrationType'),
                'source_endpoint_arn': task.get('SourceEndpointArn'),
                'target_endpoint_arn': task.get('TargetEndpointArn'),
                'replication_instance_arn': task.get('ReplicationInstanceArn'),
                'table_mappings_count': len(
                    json.loads(task.get('TableMappings', '{}')).get('rules', [])
                ),
            }

            # Add statistics if available
            if 'ReplicationTaskStats' in task:
                stats = task['ReplicationTaskStats']
                task_info['stats'] = {
                    'full_load_progress': stats.get('FullLoadProgressPercent', 0),
                    'tables_loaded': stats.get('TablesLoaded', 0),
                    'tables_loading': stats.get('TablesLoading', 0),
                    'tables_queued': stats.get('TablesQueued', 0),
                    'tables_errored': stats.get('TablesErrored', 0),
                }

            # Add error information if present
            if task.get('LastFailureMessage'):
                task_info['last_error'] = task.get('LastFailureMessage')

            if task.get('StopReason'):
                task_info['stop_reason'] = task.get('StopReason')

            tasks.append(task_info)

        return {
            'region': region,
            'total_tasks': len(tasks),
            'status_summary': status_counts,
            'tasks': tasks,
        }

    except Exception as e:
        logger.error(f'Error listing replication tasks: {str(e)}')
        return {
            'region': region,
            'error': str(e),
            'message': 'Failed to list replication tasks',
        }


@mcp.tool()
async def get_replication_task_details(
    task_identifier: str = Field(description='Replication task identifier or ARN'),
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
) -> Dict:
    """Get detailed information about a specific replication task.

    This tool provides comprehensive details about a replication task, including
    its configuration, current status, statistics, and any error messages.

    Returns:
        Dictionary containing detailed task information including:
        - Task configuration and settings
        - Current status and progress
        - Error messages and stop reasons
        - Table-level statistics
        - Endpoint information
    """
    try:
        logger.info(f'Getting details for replication task: {task_identifier}')
        dms = get_dms_client(region, aws_profile)

        # Get task details
        response = dms.describe_replication_tasks(
            Filters=[
                {'Name': 'replication-task-id', 'Values': [task_identifier]},
            ]
        )

        tasks = response.get('ReplicationTasks', [])
        if not tasks:
            return {
                'error': f'Replication task not found: {task_identifier}',
                'message': 'Task does not exist in the specified region',
            }

        task = tasks[0]

        # Parse table mappings
        table_mappings = json.loads(task.get('TableMappings', '{}'))

        # Build detailed response
        details = {
            'task_identifier': task.get('ReplicationTaskIdentifier'),
            'task_arn': task.get('ReplicationTaskArn'),
            'status': task.get('Status'),
            'migration_type': task.get('MigrationType'),
            'created_date': task.get('ReplicationTaskCreationDate').isoformat()
            if task.get('ReplicationTaskCreationDate')
            else None,
            'started_date': task.get('ReplicationTaskStartDate').isoformat()
            if task.get('ReplicationTaskStartDate')
            else None,
            'source_endpoint_arn': task.get('SourceEndpointArn'),
            'target_endpoint_arn': task.get('TargetEndpointArn'),
            'replication_instance_arn': task.get('ReplicationInstanceArn'),
            'task_settings': json.loads(task.get('ReplicationTaskSettings', '{}')),
            'table_mappings': table_mappings,
        }

        # Add statistics
        if 'ReplicationTaskStats' in task:
            stats = task['ReplicationTaskStats']
            details['statistics'] = {
                'full_load_progress_percent': stats.get('FullLoadProgressPercent', 0),
                'elapsed_time_millis': stats.get('ElapsedTimeMillis', 0),
                'tables_loaded': stats.get('TablesLoaded', 0),
                'tables_loading': stats.get('TablesLoading', 0),
                'tables_queued': stats.get('TablesQueued', 0),
                'tables_errored': stats.get('TablesErrored', 0),
                'fresh_start_date': stats.get('FreshStartDate').isoformat()
                if stats.get('FreshStartDate')
                else None,
                'start_date': stats.get('StartDate').isoformat()
                if stats.get('StartDate')
                else None,
                'stop_date': stats.get('StopDate').isoformat() if stats.get('StopDate') else None,
                'full_load_start_date': stats.get('FullLoadStartDate').isoformat()
                if stats.get('FullLoadStartDate')
                else None,
                'full_load_finish_date': stats.get('FullLoadFinishDate').isoformat()
                if stats.get('FullLoadFinishDate')
                else None,
            }

        # Add error information
        if task.get('LastFailureMessage'):
            details['last_error'] = task.get('LastFailureMessage')

        if task.get('StopReason'):
            details['stop_reason'] = task.get('StopReason')

        if task.get('ReplicationTaskAssessmentResults'):
            details['assessment_results'] = task.get('ReplicationTaskAssessmentResults')

        return details

    except Exception as e:
        logger.error(f'Error getting replication task details: {str(e)}')
        return {
            'error': str(e),
            'message': f'Failed to get details for task: {task_identifier}',
        }


@mcp.tool()
async def get_task_cloudwatch_logs(
    task_identifier: str = Field(description='Replication task identifier'),
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
    hours_back: int = 24,
    filter_pattern: Optional[str] = Field(
        None, description='CloudWatch Logs filter pattern (e.g., "ERROR" or "FATAL")'
    ),
    max_events: int = 100,
) -> Dict:
    """Retrieve CloudWatch logs for a replication task.

    This tool fetches CloudWatch logs for a specific replication task, which is crucial
    for diagnosing errors and understanding task behavior. Logs can be filtered by
    time range and search patterns.

    Returns:
        Dictionary containing:
        - log_events: List of log entries with timestamps and messages
        - log_group: CloudWatch log group name
        - time_range: Time period covered by the logs
        - summary: Count of different log levels if filter_pattern is used
    """
    try:
        logger.info(f'Retrieving CloudWatch logs for task: {task_identifier}')
        logs_client = get_logs_client(region, aws_profile)

        # DMS log group name format
        log_group_name = f'dms-tasks-{task_identifier}'

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        try:
            # Get log streams
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=10,
            )

            log_streams = streams_response.get('logStreams', [])

            if not log_streams:
                return {
                    'log_group': log_group_name,
                    'message': 'No log streams found for this task',
                    'log_events': [],
                }

            # Get log events
            log_events = []

            for stream in log_streams[:5]:  # Check latest 5 streams
                stream_name = stream['logStreamName']

                try:
                    if filter_pattern:
                        # Use filter with pattern
                        events_response = logs_client.filter_log_events(
                            logGroupName=log_group_name,
                            logStreamNames=[stream_name],
                            startTime=int(start_time.timestamp() * 1000),
                            endTime=int(end_time.timestamp() * 1000),
                            filterPattern=filter_pattern,
                            limit=max_events,
                        )
                        events = events_response.get('events', [])
                    else:
                        # Get all events
                        events_response = logs_client.get_log_events(
                            logGroupName=log_group_name,
                            logStreamName=stream_name,
                            startTime=int(start_time.timestamp() * 1000),
                            endTime=int(end_time.timestamp() * 1000),
                            limit=max_events,
                        )
                        events = events_response.get('events', [])

                    for event in events:
                        log_events.append(
                            {
                                'timestamp': datetime.fromtimestamp(
                                    event['timestamp'] / 1000
                                ).isoformat(),
                                'message': event['message'],
                                'stream': stream_name,
                            }
                        )

                except Exception as stream_error:
                    logger.warning(f'Error reading stream {stream_name}: {str(stream_error)}')
                    continue

            # Sort by timestamp
            log_events.sort(key=lambda x: x['timestamp'], reverse=True)

            # Limit total events
            log_events = log_events[:max_events]

            # Analyze log patterns
            error_count = sum(1 for e in log_events if 'ERROR' in e['message'].upper())
            warning_count = sum(1 for e in log_events if 'WARNING' in e['message'].upper())
            fatal_count = sum(1 for e in log_events if 'FATAL' in e['message'].upper())

            return {
                'log_group': log_group_name,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'hours': hours_back,
                },
                'total_events': len(log_events),
                'log_summary': {
                    'errors': error_count,
                    'warnings': warning_count,
                    'fatal': fatal_count,
                },
                'log_events': log_events,
            }

        except logs_client.exceptions.ResourceNotFoundException:
            return {
                'log_group': log_group_name,
                'error': 'Log group not found',
                'message': f'CloudWatch Logs group {log_group_name} does not exist. The task may not have started yet or logging may not be enabled.',
            }

    except Exception as e:
        logger.error(f'Error retrieving CloudWatch logs: {str(e)}')
        return {
            'error': str(e),
            'message': f'Failed to retrieve logs for task: {task_identifier}',
        }


@mcp.tool()
async def analyze_endpoint(
    endpoint_arn: str = Field(description='Endpoint ARN to analyze'),
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
) -> Dict:
    """Analyze a DMS endpoint configuration for potential issues.

    This tool examines source or target endpoint configuration and checks for
    common misconfigurations that can cause replication issues.

    Returns:
        Dictionary containing:
        - endpoint_details: Configuration information
        - connection_status: Current connection status
        - potential_issues: List of identified configuration issues
        - recommendations: Suggested fixes and best practices
    """
    try:
        logger.info(f'Analyzing endpoint: {endpoint_arn}')
        dms = get_dms_client(region, aws_profile)

        # Get endpoint details
        response = dms.describe_endpoints(
            Filters=[
                {'Name': 'endpoint-arn', 'Values': [endpoint_arn]},
            ]
        )

        endpoints = response.get('Endpoints', [])
        if not endpoints:
            return {
                'error': f'Endpoint not found: {endpoint_arn}',
                'message': 'Endpoint does not exist in the specified region',
            }

        endpoint = endpoints[0]

        # Build endpoint details
        details = {
            'endpoint_identifier': endpoint.get('EndpointIdentifier'),
            'endpoint_type': endpoint.get('EndpointType'),
            'engine_name': endpoint.get('EngineName'),
            'server_name': endpoint.get('ServerName'),
            'port': endpoint.get('Port'),
            'database_name': endpoint.get('DatabaseName'),
            'username': endpoint.get('Username'),
            'ssl_mode': endpoint.get('SslMode'),
            'status': endpoint.get('Status'),
        }

        # Add engine-specific settings
        engine_name = endpoint.get('EngineName', '').lower()

        if 'mysql' in engine_name and endpoint.get('MySqlSettings'):
            details['mysql_settings'] = endpoint.get('MySqlSettings')
        elif 'postgres' in engine_name and endpoint.get('PostgreSqlSettings'):
            details['postgresql_settings'] = endpoint.get('PostgreSqlSettings')
        elif 'oracle' in engine_name and endpoint.get('OracleSettings'):
            details['oracle_settings'] = endpoint.get('OracleSettings')
        elif 's3' in engine_name and endpoint.get('S3Settings'):
            details['s3_settings'] = endpoint.get('S3Settings')

        # Analyze for potential issues
        potential_issues = []
        recommendations = []

        # Check SSL mode
        if endpoint.get('SslMode') == 'none':
            potential_issues.append('SSL/TLS is not enabled for this endpoint')
            recommendations.append(
                'Enable SSL/TLS encryption for secure data transfer (use ssl-mode verify-ca or verify-full)'
            )

        # Check connection status
        if endpoint.get('Status') != 'active':
            potential_issues.append(f"Endpoint status is '{endpoint.get('Status')}' (not active)")
            recommendations.append(
                'Test endpoint connection and verify credentials and network access'
            )

        # Engine-specific checks
        if 'mysql' in engine_name:
            mysql_settings = endpoint.get('MySqlSettings', {})
            if not mysql_settings.get('ServerTimezone'):
                recommendations.append(
                    'Consider setting ServerTimezone for MySQL endpoints to avoid timestamp issues'
                )

        if 'postgres' in engine_name:
            pg_settings = endpoint.get('PostgreSqlSettings', {})
            if not pg_settings.get('PluginName'):
                recommendations.append(
                    'Ensure PostgreSQL logical replication is properly configured (wal_level=logical)'
                )

        # Test connection if possible
        try:
            test_response = dms.test_connection(
                ReplicationInstanceArn=endpoint.get('ReplicationInstanceArn', ''),
                EndpointArn=endpoint_arn,
            )
            connection_test = {
                'status': test_response.get('Connection', {}).get('Status'),
                'message': test_response.get('Connection', {}).get('LastFailureMessage', 'N/A'),
            }
        except Exception as test_error:
            connection_test = {
                'status': 'unable_to_test',
                'error': str(test_error),
            }

        return {
            'endpoint_details': details,
            'connection_test': connection_test,
            'potential_issues': potential_issues,
            'recommendations': recommendations,
            'analysis_complete': True,
        }

    except Exception as e:
        logger.error(f'Error analyzing endpoint: {str(e)}')
        return {
            'error': str(e),
            'message': f'Failed to analyze endpoint: {endpoint_arn}',
        }


@mcp.tool()
async def diagnose_replication_issue(
    task_identifier: str = Field(description='Replication task identifier to diagnose'),
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
) -> Dict:
    """Perform comprehensive Root Cause Analysis (RCA) for a replication task.

    This tool combines information from multiple sources to diagnose issues with
    a failed or problematic replication task. It analyzes:
    - Task status and configuration
    - Recent error logs
    - Endpoint configurations
    - Common failure patterns

    Returns:
        Dictionary containing:
        - diagnosis_summary: High-level findings
        - root_causes: Identified root causes
        - recommendations: Actionable recommendations
        - supporting_evidence: Logs and configuration details
    """
    try:
        logger.info(f'Diagnosing replication task: {task_identifier}')

        # Get task details
        task_details = await get_replication_task_details(task_identifier, region, aws_profile)

        if 'error' in task_details:
            return task_details

        # Get recent logs with errors
        logs = await get_task_cloudwatch_logs(
            task_identifier,
            region,
            aws_profile,
            hours_back=24,
            filter_pattern='ERROR',
            max_events=50,
        )

        # Analyze endpoints
        source_analysis = await analyze_endpoint(
            task_details['source_endpoint_arn'], region, aws_profile
        )
        target_analysis = await analyze_endpoint(
            task_details['target_endpoint_arn'], region, aws_profile
        )

        # Build diagnosis
        root_causes = []
        recommendations = []
        severity = 'INFO'

        task_status = task_details.get('status', '').lower()

        # Analyze task status
        if 'failed' in task_status or 'stopped' in task_status:
            severity = 'CRITICAL'

            if task_details.get('last_error'):
                root_causes.append(f'Task error: {task_details["last_error"]}')

            if task_details.get('stop_reason'):
                root_causes.append(f'Stop reason: {task_details["stop_reason"]}')

        # Analyze statistics
        stats = task_details.get('statistics', {})
        if stats.get('tables_errored', 0) > 0:
            root_causes.append(
                f'{stats["tables_errored"]} table(s) encountered errors during replication'
            )
            recommendations.append(
                'Review table-level errors in CloudWatch Logs and check for schema differences'
            )

        # Analyze logs
        if logs.get('log_summary', {}).get('errors', 0) > 10:
            root_causes.append(
                f'High error rate detected: {logs["log_summary"]["errors"]} errors in last 24 hours'
            )
            recommendations.append(
                'Review error patterns in CloudWatch Logs to identify recurring issues'
            )

        # Analyze endpoints
        source_issues = source_analysis.get('potential_issues', [])
        target_issues = target_analysis.get('potential_issues', [])

        if source_issues:
            root_causes.extend([f'Source endpoint: {issue}' for issue in source_issues])
            recommendations.extend(source_analysis.get('recommendations', []))

        if target_issues:
            root_causes.extend([f'Target endpoint: {issue}' for issue in target_issues])
            recommendations.extend(target_analysis.get('recommendations', []))

        # Common CDC issues
        if task_details.get('migration_type') == 'cdc':
            recommendations.append(
                'For CDC replication, ensure source database has CDC enabled and proper permissions'
            )
            recommendations.append(
                'Verify network connectivity and security groups allow continuous connection'
            )

        # Build comprehensive diagnosis
        diagnosis = {
            'task_identifier': task_identifier,
            'status': task_status,
            'severity': severity,
            'diagnosis_summary': {
                'root_causes_found': len(root_causes),
                'recommendations_count': len(recommendations),
                'error_logs_analyzed': logs.get('total_events', 0),
            },
            'root_causes': root_causes if root_causes else ['No specific issues identified'],
            'recommendations': recommendations
            if recommendations
            else ['Task appears healthy. Monitor for continued stability.'],
            'supporting_evidence': {
                'task_status': task_status,
                'migration_type': task_details.get('migration_type'),
                'statistics': stats,
                'recent_errors_count': logs.get('log_summary', {}).get('errors', 0),
                'source_endpoint_status': source_analysis.get('endpoint_details', {}).get(
                    'status'
                ),
                'target_endpoint_status': target_analysis.get('endpoint_details', {}).get(
                    'status'
                ),
            },
        }

        return diagnosis

    except Exception as e:
        logger.error(f'Error diagnosing replication issue: {str(e)}')
        return {
            'error': str(e),
            'message': f'Failed to diagnose task: {task_identifier}',
        }


@mcp.tool()
async def get_troubleshooting_recommendations(
    error_pattern: str = Field(
        description='Error message or pattern from DMS task (e.g., "timeout", "connection refused", "access denied")'
    ),
) -> Dict:
    """Get troubleshooting recommendations based on common DMS error patterns.

    This tool provides recommendations and links to AWS documentation based on
    common DMS error patterns and issues.

    Returns:
        Dictionary containing:
        - matched_patterns: Error patterns that were matched
        - recommendations: Step-by-step troubleshooting guide
        - documentation_links: Relevant AWS documentation
    """
    try:
        logger.info(f'Finding recommendations for error pattern: {error_pattern}')

        error_lower = error_pattern.lower()
        recommendations = []
        doc_links = []
        matched_patterns = []

        # Database connection issues
        if any(
            keyword in error_lower
            for keyword in ['connection', 'timeout', 'refused', 'network', 'unreachable']
        ):
            matched_patterns.append('Connection/Network Issues')
            recommendations.extend(
                [
                    '1. Verify security group rules allow traffic between replication instance and endpoints',
                    '2. Check that endpoints are in accessible subnets (consider VPC peering or Transit Gateway)',
                    '3. Verify database server is running and accepting connections',
                    '4. Check DNS resolution for endpoint hostnames',
                    '5. Test connectivity using DMS "Test Connection" feature',
                ]
            )
            doc_links.append(
                'https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Troubleshooting.html#CHAP_Troubleshooting.General.Network'
            )

        # Authentication issues
        if any(
            keyword in error_lower
            for keyword in ['auth', 'denied', 'permission', 'credential', 'password']
        ):
            matched_patterns.append('Authentication/Authorization Issues')
            recommendations.extend(
                [
                    '1. Verify database user credentials are correct in endpoint configuration',
                    '2. Ensure database user has required permissions for DMS operations',
                    '3. For source: REPLICATION CLIENT, REPLICATION SLAVE, SELECT privileges',
                    '4. For target: INSERT, UPDATE, DELETE, CREATE, ALTER privileges',
                    '5. Check if password has expired or account is locked',
                ]
            )
            doc_links.append(
                'https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.html#CHAP_Security.Database'
            )

        # CDC-specific issues
        if any(keyword in error_lower for keyword in ['cdc', 'binlog', 'wal', 'redo', 'archive']):
            matched_patterns.append('CDC/Replication Issues')
            recommendations.extend(
                [
                    '1. Verify CDC is enabled on source database',
                    '2. For MySQL: Check binlog_format is set to ROW',
                    '3. For PostgreSQL: Verify wal_level is set to logical',
                    '4. For Oracle: Ensure supplemental logging is enabled',
                    '5. Check that retention period for CDC logs is sufficient',
                    '6. Verify DMS has permissions to read CDC logs',
                ]
            )
            doc_links.append('https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html')

        # Table-level issues
        if any(
            keyword in error_lower
            for keyword in ['table', 'column', 'schema', 'constraint', 'key']
        ):
            matched_patterns.append('Table/Schema Issues')
            recommendations.extend(
                [
                    '1. Verify table mappings are correct in task configuration',
                    '2. Check for schema differences between source and target',
                    '3. Ensure primary keys exist on all tables',
                    '4. Review column data type compatibility',
                    '5. Check for special characters in table/column names',
                    '6. Disable foreign key constraints during initial load if needed',
                ]
            )
            doc_links.append(
                'https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.html'
            )

        # Performance issues
        if any(keyword in error_lower for keyword in ['slow', 'lag', 'performance', 'memory']):
            matched_patterns.append('Performance Issues')
            recommendations.extend(
                [
                    '1. Consider upgrading replication instance size',
                    '2. Review CloudWatch metrics for bottlenecks',
                    '3. Enable Multi-AZ for high availability',
                    '4. Optimize table mappings to reduce data volume',
                    '5. Use LOB settings appropriate for your data',
                    '6. Consider BatchApply settings for bulk operations',
                ]
            )
            doc_links.append(
                'https://docs.aws.amazon.com/dms/latest/userguide/CHAP_BestPractices.html'
            )

        # SSL/TLS issues
        if any(keyword in error_lower for keyword in ['ssl', 'tls', 'certificate', 'encrypt']):
            matched_patterns.append('SSL/TLS Issues')
            recommendations.extend(
                [
                    '1. Verify SSL certificate is valid and not expired',
                    '2. Check that endpoint SSL mode is correctly configured',
                    '3. For verify-ca or verify-full modes, provide certificate bundle',
                    '4. Ensure CA certificates are up to date',
                    '5. Test with SSL mode "none" temporarily to isolate the issue',
                ]
            )
            doc_links.append(
                'https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Security.html#CHAP_Security.SSL'
            )

        # Default recommendations
        if not matched_patterns:
            matched_patterns.append('General Troubleshooting')
            recommendations.extend(
                [
                    '1. Review CloudWatch Logs for detailed error messages',
                    '2. Check AWS DMS service health dashboard',
                    '3. Verify IAM permissions for DMS service role',
                    '4. Review task settings and table mappings',
                    '5. Test endpoints independently using "Test Connection"',
                    '6. Consider opening AWS Support case for complex issues',
                ]
            )
            doc_links.append(
                'https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Troubleshooting.html'
            )

        # Always add general documentation
        doc_links.append('https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html')
        doc_links.append('https://repost.aws/knowledge-center/dms-common-errors')

        return {
            'query': error_pattern,
            'matched_patterns': matched_patterns,
            'recommendations': recommendations,
            'documentation_links': doc_links,
            'next_steps': [
                'Apply relevant recommendations from above',
                'Check CloudWatch Logs for detailed error context',
                'Test changes incrementally',
                'Document findings for future reference',
            ],
        }

    except Exception as e:
        logger.error(f'Error getting recommendations: {str(e)}')
        return {
            'error': str(e),
            'message': 'Failed to generate recommendations',
        }


@mcp.tool()
async def analyze_security_groups(
    replication_instance_arn: str = Field(
        description='DMS Replication Instance ARN to analyze security groups for'
    ),
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
) -> Dict:
    """Analyze security group rules for DMS replication instance connectivity.

    This tool examines security group configurations to identify potential
    network connectivity issues between the replication instance and endpoints.

    Returns:
        Dictionary containing:
        - security_groups: List of security groups with their rules
        - connectivity_issues: Identified connectivity problems
        - recommendations: Security group configuration recommendations
    """
    try:
        logger.info(f'Analyzing security groups for: {replication_instance_arn}')
        dms = get_dms_client(region, aws_profile)
        ec2 = get_ec2_client(region, aws_profile)

        # Get replication instance details
        response = dms.describe_replication_instances(
            Filters=[
                {'Name': 'replication-instance-arn', 'Values': [replication_instance_arn]},
            ]
        )

        instances = response.get('ReplicationInstances', [])
        if not instances:
            return {
                'error': f'Replication instance not found: {replication_instance_arn}',
                'message': 'Instance does not exist in the specified region',
            }

        instance = instances[0]
        vpc_security_groups = instance.get('VpcSecurityGroups', [])

        if not vpc_security_groups:
            return {
                'message': 'No VPC security groups found for this replication instance',
                'recommendations': [
                    'Ensure replication instance is in a VPC with proper security groups'
                ],
            }

        # Get security group details
        sg_ids = [sg.get('VpcSecurityGroupId') for sg in vpc_security_groups]
        sg_response = ec2.describe_security_groups(GroupIds=sg_ids)

        security_groups = []
        connectivity_issues = []
        recommendations = []

        for sg in sg_response.get('SecurityGroups', []):
            sg_info = {
                'group_id': sg.get('GroupId'),
                'group_name': sg.get('GroupName'),
                'description': sg.get('Description'),
                'vpc_id': sg.get('VpcId'),
                'ingress_rules': [],
                'egress_rules': [],
            }

            # Analyze ingress rules
            for rule in sg.get('IpPermissions', []):
                rule_info = {
                    'protocol': rule.get('IpProtocol', 'all'),
                    'from_port': rule.get('FromPort'),
                    'to_port': rule.get('ToPort'),
                    'sources': [],
                }

                # Get source information
                for ip_range in rule.get('IpRanges', []):
                    rule_info['sources'].append({'type': 'cidr', 'value': ip_range.get('CidrIp')})
                for sg_ref in rule.get('UserIdGroupPairs', []):
                    rule_info['sources'].append(
                        {'type': 'security_group', 'value': sg_ref.get('GroupId')}
                    )

                sg_info['ingress_rules'].append(rule_info)

            # Analyze egress rules
            for rule in sg.get('IpPermissionsEgress', []):
                rule_info = {
                    'protocol': rule.get('IpProtocol', 'all'),
                    'from_port': rule.get('FromPort'),
                    'to_port': rule.get('ToPort'),
                    'destinations': [],
                }

                # Get destination information
                for ip_range in rule.get('IpRanges', []):
                    rule_info['destinations'].append(
                        {'type': 'cidr', 'value': ip_range.get('CidrIp')}
                    )
                for sg_ref in rule.get('UserIdGroupPairs', []):
                    rule_info['destinations'].append(
                        {'type': 'security_group', 'value': sg_ref.get('GroupId')}
                    )

                sg_info['egress_rules'].append(rule_info)

            # Check for common issues
            if not sg_info['egress_rules']:
                connectivity_issues.append(
                    f'Security group {sg.get("GroupName")} has no egress rules'
                )
                recommendations.append(
                    f'Add egress rules to {sg.get("GroupName")} to allow outbound traffic'
                )

            # Check if egress allows database ports
            has_db_egress = False
            for rule in sg_info['egress_rules']:
                if rule['protocol'] in ['-1', 'all'] or (
                    rule['from_port']
                    and rule['to_port']
                    and any(
                        port in range(rule['from_port'], rule['to_port'] + 1)
                        for port in [3306, 5432, 1521, 1433]
                    )
                ):
                    has_db_egress = True
                    break

            if not has_db_egress:
                connectivity_issues.append(
                    f'Security group {sg.get("GroupName")} may not allow database port access'
                )
                recommendations.append(
                    'Ensure egress rules allow traffic to database ports (MySQL:3306, PostgreSQL:5432, Oracle:1521, SQL Server:1433)'
                )

            security_groups.append(sg_info)

        return {
            'replication_instance_arn': replication_instance_arn,
            'security_groups': security_groups,
            'connectivity_issues': connectivity_issues
            if connectivity_issues
            else ['No obvious security group issues detected'],
            'recommendations': recommendations
            if recommendations
            else ['Security group configuration appears correct'],
        }

    except Exception as e:
        logger.error(f'Error analyzing security groups: {str(e)}')
        return {
            'error': str(e),
            'message': f'Failed to analyze security groups for: {replication_instance_arn}',
        }


@mcp.tool()
async def diagnose_network_connectivity(
    task_identifier: str = Field(description='Replication task identifier to diagnose'),
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
) -> Dict:
    """Perform comprehensive network connectivity diagnostics for a DMS task.

    This tool analyzes network configuration including security groups, VPC settings,
    subnets, and routing to identify connectivity issues between replication instance
    and endpoints.

    Returns:
        Dictionary containing:
        - network_summary: Overview of network configuration
        - connectivity_analysis: Detailed connectivity checks
        - identified_issues: List of network problems
        - recommendations: Network troubleshooting steps
    """
    try:
        logger.info(f'Diagnosing network connectivity for task: {task_identifier}')
        dms = get_dms_client(region, aws_profile)
        ec2 = get_ec2_client(region, aws_profile)

        # Get task details
        task_response = dms.describe_replication_tasks(
            Filters=[{'Name': 'replication-task-id', 'Values': [task_identifier]}]
        )

        tasks = task_response.get('ReplicationTasks', [])
        if not tasks:
            return {
                'error': f'Task not found: {task_identifier}',
                'message': 'Task does not exist in the specified region',
            }

        task = tasks[0]
        instance_arn = task.get('ReplicationInstanceArn')

        # Get replication instance details
        instance_response = dms.describe_replication_instances(
            Filters=[{'Name': 'replication-instance-arn', 'Values': [instance_arn]}]
        )

        instances = instance_response.get('ReplicationInstances', [])
        if not instances:
            return {
                'error': 'Replication instance not found',
                'message': 'Could not retrieve replication instance details',
            }

        instance = instances[0]

        # Get endpoint details
        source_endpoint_arn = task.get('SourceEndpointArn')
        target_endpoint_arn = task.get('TargetEndpointArn')

        source_response = dms.describe_endpoints(
            Filters=[{'Name': 'endpoint-arn', 'Values': [source_endpoint_arn]}]
        )
        target_response = dms.describe_endpoints(
            Filters=[{'Name': 'endpoint-arn', 'Values': [target_endpoint_arn]}]
        )

        source_endpoint = source_response.get('Endpoints', [{}])[0]
        target_endpoint = target_response.get('Endpoints', [{}])[0]

        # Build network summary
        network_summary = {
            'replication_instance': {
                'arn': instance_arn,
                'public_ip': instance.get('ReplicationInstancePublicIpAddress'),
                'private_ip': instance.get('ReplicationInstancePrivateIpAddress'),
                'publicly_accessible': instance.get('PubliclyAccessible', False),
                'multi_az': instance.get('MultiAZ', False),
            },
            'source_endpoint': {
                'server': source_endpoint.get('ServerName'),
                'port': source_endpoint.get('Port'),
                'engine': source_endpoint.get('EngineName'),
            },
            'target_endpoint': {
                'server': target_endpoint.get('ServerName'),
                'port': target_endpoint.get('Port'),
                'engine': target_endpoint.get('EngineName'),
            },
        }

        # Analyze connectivity
        connectivity_checks = []
        identified_issues = []
        recommendations = []

        # Check 1: VPC Configuration
        subnet_group = instance.get('ReplicationSubnetGroup', {})
        subnets = subnet_group.get('Subnets', [])

        if not subnets:
            identified_issues.append('Replication instance has no subnet configuration')
            recommendations.append('Configure replication subnet group with appropriate subnets')
        else:
            subnet_ids = [s.get('SubnetIdentifier') for s in subnets]
            connectivity_checks.append(
                {
                    'check': 'VPC Subnet Configuration',
                    'status': 'OK',
                    'details': f'Replication instance in {len(subnets)} subnet(s)',
                }
            )

            # Get subnet details
            try:
                subnet_response = ec2.describe_subnets(SubnetIds=subnet_ids)
                vpc_id = subnet_response['Subnets'][0]['VpcId']
                network_summary['vpc_id'] = vpc_id

                # Check route tables
                rt_response = ec2.describe_route_tables(
                    Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
                )

                has_internet_route = False
                has_nat_route = False

                for rt in rt_response.get('RouteTables', []):
                    for route in rt.get('Routes', []):
                        if route.get('GatewayId', '').startswith('igw-'):
                            has_internet_route = True
                        if route.get('NatGatewayId'):
                            has_nat_route = True

                if instance.get('PubliclyAccessible') and not has_internet_route:
                    identified_issues.append(
                        'Instance is public but VPC has no internet gateway route'
                    )
                    recommendations.append(
                        'Add internet gateway and configure route table for public access'
                    )

                if not instance.get('PubliclyAccessible') and not has_nat_route:
                    connectivity_checks.append(
                        {
                            'check': 'NAT Gateway',
                            'status': 'WARNING',
                            'details': 'No NAT gateway found - outbound connectivity may be limited',
                        }
                    )
                    recommendations.append(
                        'Consider adding NAT gateway for private instance outbound connectivity'
                    )

            except Exception as subnet_error:
                logger.warning(f'Error checking subnets: {str(subnet_error)}')

        # Check 2: Security Groups
        vpc_security_groups = instance.get('VpcSecurityGroups', [])
        if vpc_security_groups:
            sg_analysis = await analyze_security_groups(instance_arn, region, aws_profile)
            connectivity_checks.append(
                {
                    'check': 'Security Groups',
                    'status': 'ANALYZED',
                    'details': f'Found {len(sg_analysis.get("security_groups", []))} security group(s)',
                }
            )
            if 'connectivity_issues' in sg_analysis and sg_analysis['connectivity_issues']:
                identified_issues.extend(sg_analysis['connectivity_issues'])
            if 'recommendations' in sg_analysis and sg_analysis['recommendations']:
                recommendations.extend(sg_analysis['recommendations'])

        # Check 3: DNS Resolution
        source_server = source_endpoint.get('ServerName')
        target_server = target_endpoint.get('ServerName')

        if source_server and not source_server.replace('.', '').isdigit():
            connectivity_checks.append(
                {
                    'check': 'Source Endpoint DNS',
                    'status': 'INFO',
                    'details': f'Hostname: {source_server} - Ensure DNS resolution is working',
                }
            )
            recommendations.append(
                f'Verify DNS can resolve {source_server} from replication instance VPC'
            )

        if target_server and not target_server.replace('.', '').isdigit():
            connectivity_checks.append(
                {
                    'check': 'Target Endpoint DNS',
                    'status': 'INFO',
                    'details': f'Hostname: {target_server} - Ensure DNS resolution is working',
                }
            )
            recommendations.append(
                f'Verify DNS can resolve {target_server} from replication instance VPC'
            )

        # Check 4: Cross-VPC/Cross-Account connectivity
        if instance.get('PubliclyAccessible'):
            connectivity_checks.append(
                {
                    'check': 'Public Access',
                    'status': 'INFO',
                    'details': 'Replication instance is publicly accessible',
                }
            )
        else:
            connectivity_checks.append(
                {
                    'check': 'Private Network',
                    'status': 'INFO',
                    'details': 'Replication instance is private - ensure VPC connectivity to endpoints',
                }
            )
            recommendations.append(
                'For private instances, verify VPC peering, Transit Gateway, or VPN connectivity to endpoints'
            )

        return {
            'task_identifier': task_identifier,
            'network_summary': network_summary,
            'connectivity_checks': connectivity_checks,
            'identified_issues': identified_issues
            if identified_issues
            else ['No critical issues identified'],
            'recommendations': recommendations
            if recommendations
            else ['Network configuration appears healthy'],
        }

    except Exception as e:
        logger.error(f'Error diagnosing network connectivity: {str(e)}')
        return {
            'error': str(e),
            'message': f'Failed to diagnose network for task: {task_identifier}',
        }


@mcp.tool()
async def check_vpc_configuration(
    vpc_id: str = Field(description='VPC ID to analyze for DMS connectivity'),
    region: str = FIELD_AWS_REGION,
    aws_profile: str = FIELD_AWS_PROFILE,
) -> Dict:
    """Analyze VPC routing, network ACLs, and connectivity configuration.

    This tool examines VPC-level network configuration that may affect DMS
    replication, including route tables, network ACLs, VPC peering, and
    Transit Gateway attachments.

    Returns:
        Dictionary containing:
        - vpc_details: VPC configuration information
        - routing_analysis: Route table analysis
        - network_acl_analysis: Network ACL configuration
        - connectivity_options: Available connectivity methods
        - recommendations: VPC configuration recommendations
    """
    try:
        logger.info(f'Analyzing VPC configuration: {vpc_id}')
        ec2 = get_ec2_client(region, aws_profile)

        # Get VPC details
        vpc_response = ec2.describe_vpcs(VpcIds=[vpc_id])
        vpcs = vpc_response.get('Vpcs', [])

        if not vpcs:
            return {
                'error': f'VPC not found: {vpc_id}',
                'message': 'VPC does not exist in the specified region',
            }

        vpc = vpcs[0]

        vpc_details = {
            'vpc_id': vpc_id,
            'cidr_block': vpc.get('CidrBlock'),
            'is_default': vpc.get('IsDefault', False),
            'state': vpc.get('State'),
            'dns_support': vpc.get('EnableDnsSupport', False),
            'dns_hostnames': vpc.get('EnableDnsHostnames', False),
        }

        recommendations = []

        # Check DNS settings
        if not vpc.get('EnableDnsSupport'):
            recommendations.append('Enable DNS support for the VPC')
        if not vpc.get('EnableDnsHostnames'):
            recommendations.append('Enable DNS hostnames for the VPC')

        # Analyze route tables
        rt_response = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])

        routing_analysis = {'route_tables': [], 'internet_gateway': None, 'nat_gateways': []}

        igw_response = ec2.describe_internet_gateways(
            Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
        )
        if igw_response.get('InternetGateways'):
            routing_analysis['internet_gateway'] = igw_response['InternetGateways'][0].get(
                'InternetGatewayId'
            )

        nat_response = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        routing_analysis['nat_gateways'] = [
            {
                'nat_gateway_id': nat.get('NatGatewayId'),
                'state': nat.get('State'),
                'subnet_id': nat.get('SubnetId'),
            }
            for nat in nat_response.get('NatGateways', [])
        ]

        for rt in rt_response.get('RouteTables', []):
            rt_info = {
                'route_table_id': rt.get('RouteTableId'),
                'is_main': any(assoc.get('Main', False) for assoc in rt.get('Associations', [])),
                'routes': [],
            }

            for route in rt.get('Routes', []):
                route_info = {
                    'destination': route.get('DestinationCidrBlock')
                    or route.get('DestinationPrefixListId'),
                    'target': route.get('GatewayId')
                    or route.get('NatGatewayId')
                    or route.get('TransitGatewayId')
                    or route.get('VpcPeeringConnectionId')
                    or 'local',
                    'state': route.get('State', 'active'),
                }
                rt_info['routes'].append(route_info)

            routing_analysis['route_tables'].append(rt_info)

        # Check for VPC Peering
        peering_response = ec2.describe_vpc_peering_connections(
            Filters=[
                {'Name': 'requester-vpc-info.vpc-id', 'Values': [vpc_id]},
                {'Name': 'status-code', 'Values': ['active']},
            ]
        )

        connectivity_options = {
            'vpc_peering': [
                {
                    'peering_id': peer.get('VpcPeeringConnectionId'),
                    'peer_vpc_id': peer.get('AccepterVpcInfo', {}).get('VpcId'),
                    'peer_cidr': peer.get('AccepterVpcInfo', {}).get('CidrBlock'),
                }
                for peer in peering_response.get('VpcPeeringConnections', [])
            ]
        }

        # Check for Transit Gateway attachments
        try:
            tgw_response = ec2.describe_transit_gateway_attachments(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'state', 'Values': ['available']},
                ]
            )
            connectivity_options['transit_gateway'] = [
                {
                    'attachment_id': tgw.get('TransitGatewayAttachmentId'),
                    'transit_gateway_id': tgw.get('TransitGatewayId'),
                    'state': tgw.get('State'),
                }
                for tgw in tgw_response.get('TransitGatewayAttachments', [])
            ]
        except Exception as tgw_error:
            logger.warning(f'Error checking Transit Gateway: {str(tgw_error)}')
            connectivity_options['transit_gateway'] = []

        # Analyze Network ACLs
        nacl_response = ec2.describe_network_acls(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])

        network_acl_analysis = []
        for nacl in nacl_response.get('NetworkAcls', []):
            nacl_info = {
                'nacl_id': nacl.get('NetworkAclId'),
                'is_default': nacl.get('IsDefault', False),
                'ingress_rules': [],
                'egress_rules': [],
            }

            for entry in nacl.get('Entries', []):
                rule = {
                    'rule_number': entry.get('RuleNumber'),
                    'protocol': entry.get('Protocol'),
                    'action': entry.get('RuleAction'),
                    'cidr': entry.get('CidrBlock'),
                }

                if entry.get('Egress'):
                    nacl_info['egress_rules'].append(rule)
                else:
                    nacl_info['ingress_rules'].append(rule)

            # Check for restrictive NACLs
            if not nacl_info['is_default']:
                has_deny_all = any(
                    rule['rule_number'] < 32767 and rule['action'] == 'deny'
                    for rule in nacl_info['ingress_rules'] + nacl_info['egress_rules']
                )
                if has_deny_all:
                    recommendations.append(
                        f"Network ACL {nacl.get('NetworkAclId')} has explicit deny rules - verify they don't block DMS traffic"
                    )

            network_acl_analysis.append(nacl_info)

        # Generate recommendations
        if not routing_analysis['internet_gateway'] and not routing_analysis['nat_gateways']:
            recommendations.append(
                'VPC has no internet gateway or NAT gateway - ensure connectivity to endpoints'
            )

        if not connectivity_options['vpc_peering'] and not connectivity_options['transit_gateway']:
            recommendations.append(
                'No VPC peering or Transit Gateway connections found - required for cross-VPC connectivity'
            )

        return {
            'vpc_details': vpc_details,
            'routing_analysis': routing_analysis,
            'network_acl_analysis': network_acl_analysis,
            'connectivity_options': connectivity_options,
            'recommendations': recommendations
            if recommendations
            else ['VPC configuration appears appropriate for DMS'],
        }

    except Exception as e:
        logger.error(f'Error analyzing VPC configuration: {str(e)}')
        return {
            'error': str(e),
            'message': f'Failed to analyze VPC: {vpc_id}',
        }


def main():
    """Run the MCP server."""
    logger.info('Starting AWS DMS Troubleshooting MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
