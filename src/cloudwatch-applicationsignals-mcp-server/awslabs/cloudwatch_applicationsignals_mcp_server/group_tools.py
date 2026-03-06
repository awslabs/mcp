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

"""CloudWatch Application Signals MCP Server - Group-level tools.

This module provides tools for working with application groups, enabling SREs to
assess and analyze services at the group (application) level.

Tools:
- list_group_services: Discover services belonging to a group
- audit_group_health: Detect anomalies and health issues in a group
- get_group_dependencies: Map dependencies within and across groups
- get_group_changes: Track deployments across a group
- list_grouping_attribute_definitions: List all custom grouping attribute definitions
"""

from .aws_clients import AWS_REGION, applicationsignals_client, cloudwatch_client
from .sli_report_client import AWSConfig, SLIReportClient
from .utils import (
    ERROR_THRESHOLD_CRITICAL,
    ERROR_THRESHOLD_WARNING,
    FAULT_THRESHOLD_CRITICAL,
    FAULT_THRESHOLD_WARNING,
    LATENCY_P99_THRESHOLD_CRITICAL,
    LATENCY_P99_THRESHOLD_WARNING,
    fetch_metric_stats,
    list_services_paginated,
    parse_time_range,
)
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from pydantic import Field
from time import perf_counter as timer
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# SHARED HELPER FUNCTIONS
# =============================================================================


def _matches_group(service_groups: List[Dict], group_name: str) -> bool:
    """Check if any service group entry matches the target group name."""
    is_wildcard = '*' in group_name
    search_term = group_name.strip('*').lower() if is_wildcard else group_name.lower()

    for sg in service_groups:
        fields = [
            sg.get('GroupName', '').lower(),
            sg.get('GroupValue', '').lower(),
            sg.get('GroupIdentifier', '').lower(),
        ]
        if is_wildcard:
            if search_term == '' and (fields[0] or fields[1]):
                return True
            if any(search_term in f for f in fields):
                return True
        else:
            if any(search_term == f for f in fields):
                return True
    return False


async def _discover_services_by_group(
    group_name: str,
    start_time: datetime,
    end_time: datetime,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Discover all services belonging to a specific group.

    Uses the ServiceGroups field from ListServices API response which contains:
    - GroupName: Attribute name (e.g., "BusinessUnit", "Team")
    - GroupValue: Attribute value (e.g., "Payments", "Topology")
    - GroupSource: Source type (TAG, OTEL, DEFAULT)
    - GroupIdentifier: Unique identifier for filtering

    Args:
        group_name: The group value to filter by (e.g., "Topology", "Payments").
                   Can also match GroupName. Supports wildcards like '*payment*'.
        start_time: Start time for service discovery
        end_time: End time for service discovery

    Returns:
        Tuple of (list of services in the group, discovery stats)
    """
    logger.debug(f'Discovering services for group: {group_name}')

    group_services = []
    stats = {
        'total_services_scanned': 0,
        'services_in_group': 0,
        'groups_found': set(),  # Set of (GroupName, GroupValue) tuples
    }

    try:
        all_services = list_services_paginated(applicationsignals_client, start_time, end_time)

        for service in all_services:
            stats['total_services_scanned'] += 1
            key_attrs = service.get('KeyAttributes', {})

            # Get ServiceGroups from the API response
            service_groups = service.get('ServiceGroups', [])

            # Track all groups found for reporting
            for sg in service_groups:
                group_name_attr = sg.get('GroupName', '')
                group_value = sg.get('GroupValue', '')
                if group_name_attr or group_value:
                    stats['groups_found'].add(f'{group_name_attr}={group_value}')

            # Check if this service belongs to the target group
            if _matches_group(service_groups, group_name):
                group_services.append(service)
                stats['services_in_group'] += 1
                logger.debug(
                    f"Found service in group '{group_name}': {key_attrs.get('Name', 'Unknown')}"
                )

        stats['groups_found'] = sorted(stats['groups_found'])

        logger.info(
            f"Group discovery complete: {stats['services_in_group']} services found in group '{group_name}' "
            f'out of {stats["total_services_scanned"]} total services'
        )

        return group_services, stats

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
        logger.error(
            f'AWS ClientError in _discover_services_by_group: {error_code} - {error_message}'
        )
        raise


def _format_no_services_found(group_name: str, discovery_stats: Dict[str, Any]) -> str:
    """Format error message when no services found in group."""
    available_groups = discovery_stats.get('groups_found', [])
    result = f"⚠️ No services found in group '{group_name}'.\n\n"
    result += f'📊 Scanned {discovery_stats["total_services_scanned"]} total services.\n\n'

    if available_groups:
        result += '📋 **Available ServiceGroups Found (GroupName=GroupValue):**\n'
        for grp in available_groups[:20]:
            result += f'   • {grp}\n'
        if len(available_groups) > 20:
            result += f'   ... and {len(available_groups) - 20} more groups\n'
        result += "\n💡 Try using one of these GroupName or GroupValue values, or a wildcard pattern like '*team*'.\n"
    else:
        result += 'ℹ️ No ServiceGroups were found in the service responses.\n'
        result += 'Services may not have group metadata configured via tags or OpenTelemetry attributes.\n'

    return result


def _build_group_header(
    emoji: str,
    title: str,
    group_name: str,
    start_dt: datetime,
    end_dt: datetime,
    service_count: int,
) -> str:
    """Build the standard header used by group tools."""
    return (
        f'{emoji} **{title}: {group_name}**\n'
        f'⏰ Time Range: {start_dt.strftime("%Y-%m-%d %H:%M")} to {end_dt.strftime("%Y-%m-%d %H:%M")} UTC\n'
        f'🌎 Region: {AWS_REGION}\n'
        f'📊 Services in group: {service_count}\n\n'
    )


async def _setup_group_tool(
    group_name: str,
    start_time: Optional[str],
    end_time: Optional[str],
    emoji: str,
    title: str,
    default_hours: int = 3,
) -> Tuple[Optional[List[Dict]], Optional[datetime], Optional[datetime], str, Optional[Dict]]:
    """Common setup: parse time, discover services, build header or error message.

    Returns (group_services, start_dt, end_dt, result_or_error, discovery_stats).
    If group_services is None, result_or_error contains the error/empty message to return immediately.
    """
    start_dt, end_dt = parse_time_range(start_time, end_time, default_hours)
    if end_dt <= start_dt:
        return None, None, None, 'Error: end_time must be greater than start_time.', None

    group_services, discovery_stats = await _discover_services_by_group(
        group_name, start_dt, end_dt
    )
    if not group_services:
        return None, None, None, _format_no_services_found(group_name, discovery_stats), None

    header = _build_group_header(emoji, title, group_name, start_dt, end_dt, len(group_services))
    return group_services, start_dt, end_dt, header, discovery_stats


# =============================================================================
# TOOL 1: LIST GROUP SERVICES
# =============================================================================


async def list_group_services(
    group_name: str = Field(
        ...,
        description="REQUIRED. The group name or value to search for. Matches against ServiceGroups.GroupName (e.g., 'BusinessUnit'), ServiceGroups.GroupValue (e.g., 'Payments'), or ServiceGroups.GroupIdentifier. Supports wildcards like '*payment*'.",
    ),
    start_time: Optional[str] = Field(
        default=None,
        description="Start time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now-3h UTC.",
    ),
    end_time: Optional[str] = Field(
        default=None,
        description="End time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now UTC.",
    ),
) -> str:
    """SERVICE DISCOVERY TOOL - Find all services belonging to a group.

    Use this tool when users ask:
    - "What services belong to the Payment group?"
    - "List all services in Topology"
    - "Show me the services in the checkout application"
    - "Which services are part of the API group?"

    **WHAT THIS TOOL DOES:**
    Discovers all services that belong to a specific group by checking the
    ServiceGroups metadata (from tags, OpenTelemetry attributes, or defaults).

    **OUTPUT INCLUDES:**
    - List of services with their names and environments
    - Group membership details (GroupName, GroupValue, GroupSource)
    - Total count of services in the group

    **EXAMPLES:**
    ```
    list_group_services(group_name='Payments')
    list_group_services(group_name='Topology')
    list_group_services(group_name='*checkout*')  # Wildcard
    ```
    """
    start_time_perf = timer()
    logger.debug(f'Starting list_group_services for group: {group_name}')

    try:
        group_services, _, _, result, discovery_stats = await _setup_group_tool(
            group_name, start_time, end_time, '📋', 'SERVICES IN GROUP'
        )
        if group_services is None or discovery_stats is None:
            return result

        # Add discovery stats (unique to this tool)
        result += f'📊 (Scanned {discovery_stats["total_services_scanned"]} total services)\n\n'

        # Collect platform and environment statistics
        platforms = {}
        environments = {}
        for svc in group_services:
            key_attrs = svc.get('KeyAttributes', {})
            env = key_attrs.get('Environment', 'N/A')
            environments[env] = environments.get(env, 0) + 1

            # Extract platform from AttributeMaps
            attribute_maps = svc.get('AttributeMaps', [])
            for attr_map in attribute_maps:
                if 'PlatformType' in attr_map:
                    platform = attr_map['PlatformType']
                    platforms[platform] = platforms.get(platform, 0) + 1
                    break

        # Display platform and environment summary
        if platforms:
            result += '**Platform Distribution:**\n'
            for platform, count in sorted(platforms.items(), key=lambda x: -x[1]):
                result += f'   • {platform}: {count} service{"s" if count > 1 else ""}\n'
            result += '\n'

        if environments:
            result += '**Environment Distribution:**\n'
            for env, count in sorted(environments.items(), key=lambda x: -x[1]):
                result += f'   • {env}: {count} service{"s" if count > 1 else ""}\n'
            result += '\n'

        result += '**Services:**\n'
        for svc in group_services:
            key_attrs = svc.get('KeyAttributes', {})
            svc_name = key_attrs.get('Name', 'Unknown')
            svc_env = key_attrs.get('Environment', 'N/A')
            svc_type = key_attrs.get('Type', 'Service')
            svc_groups = svc.get('ServiceGroups', [])

            result += f'\n• **{svc_name}**\n'
            result += f'  Environment: {svc_env}\n'
            result += f'  Type: {svc_type}\n'

            if svc_groups:
                result += '  Groups:\n'
                for sg in svc_groups:
                    gn = sg.get('GroupName', '')
                    gv = sg.get('GroupValue', '')
                    gs = sg.get('GroupSource', '')
                    result += f'    - {gn}={gv} (source: {gs})\n'

        elapsed = timer() - start_time_perf
        logger.debug(f'list_group_services completed in {elapsed:.3f}s')

        return result

    except Exception as e:
        logger.error(f'Unexpected error in list_group_services: {e}', exc_info=True)
        return f'Error: {str(e)}'


# =============================================================================
# TOOL 2: AUDIT GROUP HEALTH
# =============================================================================


async def audit_group_health(
    group_name: str = Field(
        ...,
        description="REQUIRED. The group name or value to audit. Supports wildcards like '*payment*'.",
    ),
    start_time: Optional[str] = Field(
        default=None,
        description="Start time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now-3h UTC.",
    ),
    end_time: Optional[str] = Field(
        default=None,
        description="End time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now UTC.",
    ),
    fault_threshold_warning: float = Field(
        default=FAULT_THRESHOLD_WARNING,
        description='Fault rate percentage threshold for WARNING when using metrics fallback (default: 1.0)',
    ),
    fault_threshold_critical: float = Field(
        default=FAULT_THRESHOLD_CRITICAL,
        description='Fault rate percentage threshold for CRITICAL when using metrics fallback (default: 5.0)',
    ),
    error_threshold_warning: float = Field(
        default=ERROR_THRESHOLD_WARNING,
        description='Error rate percentage threshold for WARNING when using metrics fallback (default: 1.0)',
    ),
    error_threshold_critical: float = Field(
        default=ERROR_THRESHOLD_CRITICAL,
        description='Error rate percentage threshold for CRITICAL when using metrics fallback (default: 5.0)',
    ),
    latency_p99_threshold_warning: float = Field(
        default=LATENCY_P99_THRESHOLD_WARNING,
        description='Latency P99 threshold in milliseconds for WARNING when using metrics fallback (default: 1000.0)',
    ),
    latency_p99_threshold_critical: float = Field(
        default=LATENCY_P99_THRESHOLD_CRITICAL,
        description='Latency P99 threshold in milliseconds for CRITICAL when using metrics fallback (default: 5000.0)',
    ),
) -> str:
    """HEALTH AUDIT TOOL - Detect anomalies and unhealthy services in a group.

    Use this tool when users ask:
    - "Is the Payment application healthy?"
    - "Are there any unhealthy services in Topology?"
    - "Which services have high fault rates in the checkout group?"
    - "Check the health of the API group"
    - "Any anomalies in the Payment services?"

    **WHAT THIS TOOL DOES:**
    1. **SLI-First**: First checks Service Level Indicators (SLOs) for each service.
       If SLOs are configured, uses SLO breach status for health assessment.
    2. **Metrics Fallback**: For services without SLOs, falls back to raw metrics
       (fault rate, error rate, latency) with configurable thresholds.

    **HEALTH ASSESSMENT:**
    - SLI Mode: CRITICAL if any SLO is breached, OK otherwise
    - Metrics Mode: Based on fault/error rate thresholds

    **OUTPUT INCLUDES:**
    - Data source indicator (SLI vs Metrics) per service
    - Health summary (critical/warning/healthy counts)
    - Breached SLO names (if using SLI)
    - Detailed anomaly list with severity
    - Recommendations for investigation

    **EXAMPLES:**
    ```
    audit_group_health(group_name='Payments')
    audit_group_health(group_name='Checkout', fault_threshold_critical=15.0)
    ```
    """
    start_time_perf = timer()
    logger.debug(f'Starting audit_group_health for group: {group_name}')

    try:
        group_services, start_dt, end_dt, result, _ = await _setup_group_tool(
            group_name, start_time, end_time, '🔍', 'GROUP HEALTH AUDIT'
        )
        if group_services is None or start_dt is None or end_dt is None:
            return result

        # Collect health status for each service
        critical_services = []
        warning_services = []
        healthy_services = []
        error_services = []

        # Track data sources for reporting
        sli_based_count = 0
        metrics_based_count = 0

        # Calculate period hours for SLI client
        period_hours = int((end_dt - start_dt).total_seconds() / 3600)
        period_hours = min(max(period_hours, 1), 24)  # Clamp to 1-24 hours

        # Calculate appropriate period for metrics fallback
        time_diff = (end_dt - start_dt).total_seconds()
        if time_diff <= 3600:
            period = 60
        elif time_diff <= 86400:
            period = 300
        else:
            period = 3600

        for svc in group_services:
            key_attrs = svc.get('KeyAttributes', {})
            svc_name = key_attrs.get('Name', 'Unknown')
            svc_env = key_attrs.get('Environment', '')

            health_result = {
                'service_name': svc_name,
                'environment': svc_env,
                'data_source': 'UNKNOWN',
                'health_status': 'UNKNOWN',
                'anomalies': [],
                'slo_info': None,
                'fault_rate': None,
                'error_rate': None,
                'latency_p99': None,
            }

            # Step 1: Try SLI-based health check first
            sli_data_available = False
            try:
                config = AWSConfig(
                    region=AWS_REGION,
                    period_in_hours=period_hours,
                    service_name=svc_name,
                    key_attributes=key_attrs,
                )
                sli_client = SLIReportClient(config)
                sli_report = sli_client.generate_sli_report()

                # Check if we have any SLOs configured
                if sli_report.total_slo_count > 0:
                    sli_data_available = True
                    sli_based_count += 1
                    health_result['data_source'] = 'SLI'
                    health_result['slo_info'] = {
                        'total_slos': sli_report.total_slo_count,
                        'ok_slos': sli_report.ok_slo_count,
                        'breached_slos': sli_report.breached_slo_count,
                        'breached_slo_names': sli_report.breached_slo_names,
                    }

                    if sli_report.sli_status == 'CRITICAL':
                        health_result['health_status'] = 'CRITICAL'
                        health_result['anomalies'].append(
                            {
                                'type': 'SLO_BREACH',
                                'severity': 'CRITICAL',
                                'message': f'{sli_report.breached_slo_count}/{sli_report.total_slo_count} SLOs breached: {", ".join(sli_report.breached_slo_names)}',
                            }
                        )
                        critical_services.append(health_result)
                    else:
                        health_result['health_status'] = 'HEALTHY'
                        healthy_services.append(health_result)

                    logger.debug(
                        f'Service {svc_name}: SLI-based health - {health_result["health_status"]}'
                    )

            except Exception as e:
                logger.debug(f'Could not get SLI data for {svc_name}: {e}')

            # Step 2: Fall back to metrics if no SLI data
            if not sli_data_available:
                metrics_based_count += 1
                health_result['data_source'] = 'METRICS'

                try:
                    # Get service detail for metric references
                    service_response = applicationsignals_client.get_service(
                        StartTime=start_dt,
                        EndTime=end_dt,
                        KeyAttributes=key_attrs,
                    )

                    metric_refs = service_response.get('Service', {}).get('MetricReferences', [])

                    for metric_ref in metric_refs:
                        metric_name = metric_ref.get('MetricName', '')
                        metric_type = metric_ref.get('MetricType', '')
                        namespace = metric_ref.get('Namespace', '')
                        dimensions = metric_ref.get('Dimensions', [])

                        if metric_type == 'Fault':
                            stats = fetch_metric_stats(
                                cloudwatch_client,
                                namespace,
                                metric_name,
                                dimensions,
                                start_dt,
                                end_dt,
                                period,
                            )
                            if stats:
                                avg_fault = stats['average']
                                health_result['fault_rate'] = avg_fault

                                try:
                                    if avg_fault > fault_threshold_critical:
                                        health_result['anomalies'].append(
                                            {
                                                'type': 'HIGH_FAULT_RATE',
                                                'severity': 'CRITICAL',
                                                'value': avg_fault,
                                                'threshold': fault_threshold_critical,
                                                'message': f'Fault rate {avg_fault:.2f}% exceeds critical threshold ({fault_threshold_critical}%)',
                                            }
                                        )
                                    elif avg_fault > fault_threshold_warning:
                                        health_result['anomalies'].append(
                                            {
                                                'type': 'HIGH_FAULT_RATE',
                                                'severity': 'WARNING',
                                                'value': avg_fault,
                                                'threshold': fault_threshold_warning,
                                                'message': f'Fault rate {avg_fault:.2f}% exceeds warning threshold ({fault_threshold_warning}%)',
                                            }
                                        )
                                except Exception as e:
                                    logger.warning(
                                        f'Failed to evaluate Fault thresholds for {svc_name}: {e}'
                                    )

                        elif metric_type == 'Error':
                            stats = fetch_metric_stats(
                                cloudwatch_client,
                                namespace,
                                metric_name,
                                dimensions,
                                start_dt,
                                end_dt,
                                period,
                            )
                            if stats:
                                avg_error = stats['average']
                                health_result['error_rate'] = avg_error

                                try:
                                    if avg_error > error_threshold_critical:
                                        health_result['anomalies'].append(
                                            {
                                                'type': 'HIGH_ERROR_RATE',
                                                'severity': 'CRITICAL',
                                                'value': avg_error,
                                                'threshold': error_threshold_critical,
                                                'message': f'Error rate {avg_error:.2f}% exceeds critical threshold ({error_threshold_critical}%)',
                                            }
                                        )
                                    elif avg_error > error_threshold_warning:
                                        health_result['anomalies'].append(
                                            {
                                                'type': 'HIGH_ERROR_RATE',
                                                'severity': 'WARNING',
                                                'value': avg_error,
                                                'threshold': error_threshold_warning,
                                                'message': f'Error rate {avg_error:.2f}% exceeds warning threshold ({error_threshold_warning}%)',
                                            }
                                        )
                                except Exception as e:
                                    logger.warning(
                                        f'Failed to evaluate Error thresholds for {svc_name}: {e}'
                                    )

                        elif metric_type == 'Latency':
                            stats = fetch_metric_stats(
                                cloudwatch_client,
                                namespace,
                                metric_name,
                                dimensions,
                                start_dt,
                                end_dt,
                                period,
                                extended_statistics=['p99'],
                            )
                            if stats and stats.get('extended'):
                                p99_values = [
                                    dp.get('ExtendedStatistics', {}).get('p99', 0)
                                    for dp in stats['extended']
                                ]
                                if p99_values:
                                    max_p99 = max(p99_values)
                                    health_result['latency_p99'] = max_p99

                                    try:
                                        if max_p99 > latency_p99_threshold_critical:
                                            health_result['anomalies'].append(
                                                {
                                                    'type': 'HIGH_LATENCY',
                                                    'severity': 'CRITICAL',
                                                    'value': max_p99,
                                                    'threshold': latency_p99_threshold_critical,
                                                    'message': f'Latency P99 {max_p99:.2f}ms exceeds critical threshold ({latency_p99_threshold_critical}ms)',
                                                }
                                            )
                                        elif max_p99 > latency_p99_threshold_warning:
                                            health_result['anomalies'].append(
                                                {
                                                    'type': 'HIGH_LATENCY',
                                                    'severity': 'WARNING',
                                                    'value': max_p99,
                                                    'threshold': latency_p99_threshold_warning,
                                                    'message': f'Latency P99 {max_p99:.2f}ms exceeds warning threshold ({latency_p99_threshold_warning}ms)',
                                                }
                                            )
                                    except Exception as e:
                                        logger.warning(
                                            f'Failed to evaluate Latency thresholds for {svc_name}: {e}'
                                        )

                    # Determine health status from metrics
                    if health_result['anomalies']:
                        severities = [a['severity'] for a in health_result['anomalies']]
                        if 'CRITICAL' in severities:
                            health_result['health_status'] = 'CRITICAL'
                            critical_services.append(health_result)
                        else:
                            health_result['health_status'] = 'WARNING'
                            warning_services.append(health_result)
                    else:
                        health_result['health_status'] = 'HEALTHY'
                        healthy_services.append(health_result)

                    logger.debug(
                        f'Service {svc_name}: Metrics-based health - {health_result["health_status"]}'
                    )

                except Exception as e:
                    logger.warning(f'Failed to get metrics for service {svc_name}: {e}')
                    health_result['health_status'] = 'ERROR'
                    health_result['error'] = str(e)
                    error_services.append(health_result)

        # Health Summary
        result += '=' * 50 + '\n'
        result += '**HEALTH SUMMARY**\n'
        result += '=' * 50 + '\n\n'

        result += f'📊 Data Sources: {sli_based_count} services with SLIs, {metrics_based_count} using metrics fallback\n\n'

        total = len(group_services)
        result += f'🚨 Critical: {len(critical_services)}/{total}\n'
        result += f'⚠️  Warning:  {len(warning_services)}/{total}\n'
        result += f'✅ Healthy:  {len(healthy_services)}/{total}\n'
        if error_services:
            result += f'❓ Unknown:  {len(error_services)}/{total}\n'
        result += '\n'

        # Overall status
        if critical_services:
            result += '🚨 **Overall Status: CRITICAL** - Immediate attention required\n\n'
        elif warning_services:
            result += '⚠️ **Overall Status: WARNING** - Investigation recommended\n\n'
        else:
            result += '✅ **Overall Status: HEALTHY** - All services operating normally\n\n'

        # Critical Issues Detail
        if critical_services:
            result += '=' * 50 + '\n'
            result += '🚨 **CRITICAL ISSUES**\n'
            result += '=' * 50 + '\n'

            for svc in critical_services:
                result += (
                    f'\n**{svc["service_name"]}** ({svc["environment"]}) [{svc["data_source"]}]\n'
                )
                for anomaly in svc.get('anomalies', []):
                    if anomaly['severity'] == 'CRITICAL':
                        result += f'   • {anomaly["message"]}\n'
                if svc.get('slo_info'):
                    info = svc['slo_info']
                    result += f'   SLOs: {info["ok_slos"]}/{info["total_slos"]} OK\n'
                if svc.get('fault_rate') is not None:
                    result += f'   Fault Rate: {svc["fault_rate"]:.2f}%\n'
                if svc.get('error_rate') is not None:
                    result += f'   Error Rate: {svc["error_rate"]:.2f}%\n'
                if svc.get('latency_p99') is not None:
                    result += f'   Latency P99: {svc["latency_p99"]:.2f}ms\n'

        # Warning Issues Detail
        if warning_services:
            result += '\n' + '=' * 50 + '\n'
            result += '⚠️ **WARNING ISSUES**\n'
            result += '=' * 50 + '\n'

            for svc in warning_services:
                result += (
                    f'\n**{svc["service_name"]}** ({svc["environment"]}) [{svc["data_source"]}]\n'
                )
                for anomaly in svc.get('anomalies', []):
                    result += f'   • {anomaly["message"]}\n'
                if svc.get('fault_rate') is not None:
                    result += f'   Fault Rate: {svc["fault_rate"]:.2f}%\n'
                if svc.get('error_rate') is not None:
                    result += f'   Error Rate: {svc["error_rate"]:.2f}%\n'

        # Recommendations
        if critical_services or warning_services:
            result += '\n' + '=' * 50 + '\n'
            result += '💡 **RECOMMENDATIONS**\n'
            result += '=' * 50 + '\n\n'

            if critical_services:
                result += '**Immediate Actions:**\n'
                for svc in critical_services:
                    result += f'   • Investigate {svc["service_name"]} using audit_services()\n'
                result += '\n'

            result += '**Next Steps:**\n'
            result += '   • Use audit_services() for detailed root cause analysis\n'
            result += '   • Use get_group_changes() to check for recent deployments\n'
            result += '   • Use get_group_dependencies() to check downstream impact\n'

        elapsed = timer() - start_time_perf
        logger.debug(f'audit_group_health completed in {elapsed:.3f}s')

        return result

    except Exception as e:
        logger.error(f'Unexpected error in audit_group_health: {e}', exc_info=True)
        return f'Error: {str(e)}'


# =============================================================================
# TOOL 3: GET GROUP DEPENDENCIES
# =============================================================================


async def get_group_dependencies(
    group_name: str = Field(
        ...,
        description="REQUIRED. The group name or value to analyze. Supports wildcards like '*payment*'.",
    ),
    start_time: Optional[str] = Field(
        default=None,
        description="Start time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now-3h UTC.",
    ),
    end_time: Optional[str] = Field(
        default=None,
        description="End time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now UTC.",
    ),
) -> str:
    """DEPENDENCY MAPPING TOOL - Analyze dependencies within and across groups.

    Use this tool when users ask:
    - "What are the dependencies of the Payment group?"
    - "What does the checkout application depend on?"
    - "What external services does the Checkout group use?"
    - "Show me the dependency map for the API group"

    **WHAT THIS TOOL DOES:**
    Maps all dependencies for services in a group:
    - Intra-group: Dependencies between services within the same group
    - Cross-group: Dependencies on services in other groups
    - External: Dependencies on AWS services (S3, DynamoDB, SQS, etc.)

    **OUTPUT INCLUDES:**
    - Intra-group dependency graph
    - Cross-group dependencies
    - External AWS service dependencies

    **EXAMPLES:**
    ```
    get_group_dependencies(group_name='Payments')
    get_group_dependencies(group_name='*api*')
    ```
    """
    start_time_perf = timer()
    logger.debug(f'Starting get_group_dependencies for group: {group_name}')

    try:
        group_services, start_dt, end_dt, result, _ = await _setup_group_tool(
            group_name, start_time, end_time, '🔗', 'GROUP DEPENDENCIES'
        )
        if group_services is None or start_dt is None or end_dt is None:
            return result

        # Collect dependencies - track both (name, env) pairs and name-only set
        group_service_keys = {
            (
                svc.get('KeyAttributes', {}).get('Name', '').lower(),
                svc.get('KeyAttributes', {}).get('Environment', '').lower(),
            )
            for svc in group_services
        }

        intra_group_deps = {}  # service -> [dependencies within group]
        cross_group_deps = []  # dependencies to services outside group
        external_deps = set()  # AWS service dependencies
        dep_group_cache = {}  # Cache for dependency group lookups: (name, env) -> groups

        for svc in group_services:
            key_attrs = svc.get('KeyAttributes', {})
            svc_name = key_attrs.get('Name', 'Unknown')

            intra_group_deps[svc_name] = []

            # Get dependencies
            try:
                response = applicationsignals_client.list_service_dependencies(
                    StartTime=start_dt,
                    EndTime=end_dt,
                    KeyAttributes=key_attrs,
                    MaxResults=100,
                )

                for dep in response.get('ServiceDependencies', []):
                    dep_key_attrs = dep.get('DependencyKeyAttributes', {})
                    dep_name = dep_key_attrs.get('Name') or dep_key_attrs.get(
                        'Identifier', 'Unknown'
                    )
                    dep_type = dep_key_attrs.get('Type', 'Unknown')
                    dep_resource_type = dep_key_attrs.get('ResourceType', '')
                    dep_env = dep_key_attrs.get('Environment', '')
                    operation = dep.get('OperationName', '')

                    # Categorize dependency
                    # 1. Check intra-group first by name + environment
                    if (dep_name.lower(), dep_env.lower()) in group_service_keys:
                        intra_group_deps[svc_name].append(
                            {
                                'name': dep_name,
                                'operation': operation,
                            }
                        )
                    # 2. AWS resources (DynamoDB, S3, etc.) and AWS managed services
                    elif dep_type.startswith('AWS::') or dep_resource_type.startswith('AWS::'):
                        display_type = dep_resource_type or dep_type
                        external_deps.add(f'{display_type}:{dep_name}')
                    # 3. Other services not in our group - look up their group info
                    else:
                        cache_key = (dep_name.lower(), dep_env.lower())
                        if cache_key not in dep_group_cache:
                            try:
                                dep_svc_response = applicationsignals_client.get_service(
                                    StartTime=start_dt,
                                    EndTime=end_dt,
                                    KeyAttributes=dep_key_attrs,
                                )
                                dep_group_cache[cache_key] = dep_svc_response.get(
                                    'Service', {}
                                ).get('ServiceGroups', [])
                            except Exception as e:
                                logger.debug(
                                    f'Could not get service details for dependency {dep_name}: {e}'
                                )
                                dep_group_cache[cache_key] = []

                        cross_group_deps.append(
                            {
                                'from': svc_name,
                                'to': dep_name,
                                'to_env': dep_env,
                                'type': dep_type,
                                'operation': operation,
                                'groups': dep_group_cache[cache_key],
                            }
                        )

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code != 'ResourceNotFoundException':
                    logger.warning(f'Failed to get dependencies for {svc_name}: {e}')

        # Format output
        result += '=' * 50 + '\n'
        result += '**INTRA-GROUP DEPENDENCIES**\n'
        result += '(Services within this group calling each other)\n'
        result += '=' * 50 + '\n\n'

        has_intra_deps = False
        for svc_name, deps in intra_group_deps.items():
            if deps:
                has_intra_deps = True
                dep_names = [d['name'] for d in deps]
                result += f'   {svc_name} → {", ".join(dep_names)}\n'

        if not has_intra_deps:
            result += '   (No intra-group dependencies found)\n'

        result += '\n' + '=' * 50 + '\n'
        result += '**CROSS-GROUP DEPENDENCIES**\n'
        result += '(Services in this group calling services in OTHER groups)\n'
        result += '=' * 50 + '\n\n'

        if cross_group_deps:
            # Group by source service
            by_source = {}
            for dep in cross_group_deps:
                src = dep['from']
                if src not in by_source:
                    by_source[src] = []
                by_source[src].append(dep)

            for src, deps in by_source.items():
                result += f'   **{src}** depends on:\n'
                for dep in deps:
                    result += f'      → {dep["to"]} ({dep["to_env"]})\n'
                    if dep.get('groups'):
                        group_strs = [
                            f'{g.get("GroupName", "")}={g.get("GroupValue", "")} (source: {g.get("GroupSource", "")})'
                            for g in dep['groups']
                        ]
                        result += f'        Groups: {", ".join(group_strs)}\n'
        else:
            result += '   (No cross-group dependencies found)\n'

        result += '\n' + '=' * 50 + '\n'
        result += '**EXTERNAL DEPENDENCIES**\n'
        result += '(AWS services used by this group)\n'
        result += '=' * 50 + '\n\n'

        if external_deps:
            for ext_dep in sorted(external_deps):
                result += f'   • {ext_dep}\n'
        else:
            result += '   (No external AWS service dependencies found)\n'

        # Summary
        result += '\n' + '=' * 50 + '\n'
        result += '**SUMMARY**\n'
        result += '=' * 50 + '\n\n'

        intra_count = sum(len(deps) for deps in intra_group_deps.values())
        result += f'   • Intra-group dependencies: {intra_count}\n'
        result += f'   • Cross-group dependencies: {len(cross_group_deps)}\n'
        result += f'   • External AWS dependencies: {len(external_deps)}\n'

        elapsed = timer() - start_time_perf
        logger.debug(f'get_group_dependencies completed in {elapsed:.3f}s')

        return result

    except Exception as e:
        logger.error(f'Unexpected error in get_group_dependencies: {e}', exc_info=True)
        return f'Error: {str(e)}'


# =============================================================================
# TOOL 4: GET GROUP CHANGES
# =============================================================================


async def get_group_changes(
    group_name: str = Field(
        ...,
        description="REQUIRED. The group name or value to check for changes. Supports wildcards like '*payment*'.",
    ),
    start_time: Optional[str] = Field(
        default=None,
        description="Start time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now-3h UTC.",
    ),
    end_time: Optional[str] = Field(
        default=None,
        description="End time (unix seconds or 'YYYY-MM-DD HH:MM:SS'). Defaults to now UTC.",
    ),
) -> str:
    """CHANGE TRACKING TOOL - Monitor deployments in a group.

    Use this tool when users ask:
    - "What deployments happened in the Payment group today?"
    - "Any recent deployments in the Checkout services?"
    - "Show me the deployment history for the API group"
    - "Did anything deploy to the checkout application recently?"

    **WHAT THIS TOOL DOES:**
    Retrieves deployment events for all services in a group, helping
    correlate issues with recent deployments.

    **OUTPUT INCLUDES:**
    - Summary of deployments
    - Timeline of deployment events
    - Details: timestamp, event type, user, affected service

    **EXAMPLES:**
    ```
    get_group_changes(group_name='Payments')
    get_group_changes(group_name='Checkout', start_time='2024-01-01 00:00:00')
    ```
    """
    start_time_perf = timer()
    logger.debug(f'Starting get_group_changes for group: {group_name}')

    try:
        group_services, start_dt, end_dt, result, _ = await _setup_group_tool(
            group_name, start_time, end_time, '📦', 'GROUP CHANGES'
        )
        if group_services is None or start_dt is None or end_dt is None:
            return result

        # Get service names for filtering
        group_service_names = {
            svc.get('KeyAttributes', {}).get('Name', '').lower() for svc in group_services
        }

        # Collect change events
        change_events = []
        deployment_count = 0
        configuration_count = 0

        try:
            next_token = None

            while True:
                list_params = {
                    'StartTime': start_dt,
                    'EndTime': end_dt,
                    'MaxResults': 100,
                }
                if next_token:
                    list_params['NextToken'] = next_token

                response = applicationsignals_client.list_service_states(**list_params)
                service_states = response.get('ServiceStates', [])
                next_token = response.get('NextToken')

                for svc_state in service_states:
                    service_info = svc_state.get('Service', {})
                    svc_name = service_info.get('Name', '')

                    # Filter to only include services in our group
                    if svc_name.lower() not in group_service_names:
                        continue

                    # Process change events
                    for event in svc_state.get('LatestChangeEvents', []):
                        timestamp = event.get('Timestamp')
                        if hasattr(timestamp, 'isoformat'):
                            timestamp_str = timestamp.isoformat()
                        else:
                            timestamp_str = str(timestamp) if timestamp else ''

                        event_type = event.get('ChangeEventType', '')

                        change_events.append(
                            {
                                'service_name': svc_name,
                                'timestamp': timestamp_str,
                                'event_type': event_type,
                                'event_name': event.get('EventName', ''),
                                'event_id': event.get('EventId', ''),
                                'user_name': event.get('UserName', ''),
                                'region': event.get('Region', ''),
                            }
                        )

                        if event_type == 'DEPLOYMENT':
                            deployment_count += 1
                        elif event_type == 'CONFIGURATION':
                            configuration_count += 1

                if not next_token:
                    break

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code not in ['ResourceNotFoundException', 'ValidationException']:
                logger.warning(f'Failed to get service states: {e}')
            result += '⚠️ Note: Service state tracking may not be available in this region.\n\n'

        # Sort by timestamp (most recent first)
        change_events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Summary
        result += '=' * 50 + '\n'
        result += '**CHANGE SUMMARY**\n'
        result += '=' * 50 + '\n\n'

        result += f'   📦 Deployments: {deployment_count}\n'
        result += f'   ⚙️  Configuration Changes: {configuration_count}\n'
        result += f'   📋 Total Events: {len(change_events)}\n\n'

        # Change timeline
        if change_events:
            result += '=' * 50 + '\n'
            result += '**CHANGE TIMELINE** (most recent first)\n'
            result += '=' * 50 + '\n\n'

            for event in change_events[:20]:
                event_emoji = '📦' if event['event_type'] == 'DEPLOYMENT' else '⚙️'
                result += f'{event_emoji} **{event["service_name"]}**\n'
                result += f'   Time: {event["timestamp"]}\n'
                result += f'   Type: {event["event_type"]}\n'
                if event['event_name']:
                    result += f'   Event: {event["event_name"]}\n'
                if event['user_name']:
                    result += f'   User: {event["user_name"]}\n'
                result += '\n'

            if len(change_events) > 20:
                result += f'... and {len(change_events) - 20} more events\n\n'

            # Group by service
            result += '=' * 50 + '\n'
            result += '**CHANGES BY SERVICE**\n'
            result += '=' * 50 + '\n\n'

            by_service = {}
            for event in change_events:
                svc = event['service_name']
                if svc not in by_service:
                    by_service[svc] = {'deployments': 0, 'configs': 0}
                if event['event_type'] == 'DEPLOYMENT':
                    by_service[svc]['deployments'] += 1
                else:
                    by_service[svc]['configs'] += 1

            for svc, counts in sorted(by_service.items()):
                result += f'   **{svc}**: {counts["deployments"]} deployments, {counts["configs"]} config changes\n'

        else:
            result += 'ℹ️ No change events found in the specified time range.\n'

        # Recommendations
        if change_events:
            result += '\n' + '=' * 50 + '\n'
            result += '💡 **TIPS**\n'
            result += '=' * 50 + '\n\n'
            result += '   • Use audit_group_health() to check if changes caused issues\n'
            result += '   • Use audit_services() for detailed service analysis\n'
            result += '   • Compare health before/after deployment times\n'

        elapsed = timer() - start_time_perf
        logger.debug(f'get_group_changes completed in {elapsed:.3f}s')

        return result

    except Exception as e:
        logger.error(f'Unexpected error in get_group_changes: {e}', exc_info=True)
        return f'Error: {str(e)}'


# =============================================================================
# TOOL 5: LIST GROUPING ATTRIBUTE DEFINITIONS
# =============================================================================


async def list_grouping_attribute_definitions() -> str:
    """GROUPING CONFIGURATION TOOL - List all custom grouping attribute definitions.

    Use this tool when users ask:
    - "What grouping attributes are configured?"
    - "List all custom groups"
    - "What groups have been defined in my account?"
    - "Show me the grouping configuration"
    - "What grouping attributes are available?"

    **WHAT THIS TOOL DOES:**
    Retrieves all custom grouping attribute definitions configured in the account.
    These definitions determine how services are logically grouped based on
    telemetry attributes, AWS tags, or predefined mappings.

    **OUTPUT INCLUDES:**
    - List of all grouping attribute definitions
    - Grouping name (e.g., "BusinessUnit", "Team")
    - Source keys used to derive group values
    - Default grouping value when source data is missing
    - Last configuration update timestamp

    **EXAMPLES:**
    ```
    list_grouping_attribute_definitions()
    ```
    """
    start_time_perf = timer()
    logger.debug('Starting list_grouping_attribute_definitions')

    try:
        all_definitions = []
        next_token = None
        updated_at = None

        while True:
            list_params = {}
            if next_token:
                list_params['NextToken'] = next_token

            response = applicationsignals_client.list_grouping_attribute_definitions(**list_params)
            definitions = response.get('GroupingAttributeDefinitions', [])
            all_definitions.extend(definitions)

            if not updated_at and 'UpdatedAt' in response:
                updated_at = response['UpdatedAt']

            next_token = response.get('NextToken')
            if not next_token:
                break

        # Build result
        result = '📋 **GROUPING ATTRIBUTE DEFINITIONS**\n'
        result += f'🌎 Region: {AWS_REGION}\n'
        if updated_at:
            if hasattr(updated_at, 'strftime'):
                result += f'🕐 Last Updated: {updated_at.strftime("%Y-%m-%d %H:%M:%S")} UTC\n'
            else:
                result += f'🕐 Last Updated: {updated_at}\n'
        result += '\n'

        if not all_definitions:
            result += 'ℹ️ No custom grouping attribute definitions found.\n\n'
            result += '💡 **Tips:**\n'
            result += '   • Grouping attributes can be configured via the Application Signals console or API\n'
            result += '   • Groups can be derived from OpenTelemetry attributes, AWS tags, or predefined mappings\n'
            return result

        result += f'✅ Found **{len(all_definitions)} grouping attribute definition(s)**\n\n'

        for i, definition in enumerate(all_definitions, 1):
            grouping_name = definition.get('GroupingName', 'Unknown')
            source_keys = definition.get('GroupingSourceKeys', [])
            default_value = definition.get('DefaultGroupingValue', '')

            result += f'**{i}. {grouping_name}**\n'
            if source_keys:
                result += f'   Source Keys: {", ".join(source_keys)}\n'
            if default_value:
                result += f'   Default Value: {default_value}\n'
            result += '\n'

        result += '💡 **Tips:**\n'
        result += "   • Use list_group_services(group_name='<GroupValue>') to find services in a specific group\n"
        result += (
            "   • Use audit_group_health(group_name='<GroupValue>') to check health of a group\n"
        )

        elapsed = timer() - start_time_perf
        logger.debug(f'list_grouping_attribute_definitions completed in {elapsed:.3f}s')

        return result

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
        logger.error(
            f'AWS ClientError in list_grouping_attribute_definitions: {error_code} - {error_message}'
        )
        return f'Error: {error_code} - {error_message}'
    except Exception as e:
        logger.error(
            f'Unexpected error in list_grouping_attribute_definitions: {e}', exc_info=True
        )
        return f'Error: {str(e)}'
