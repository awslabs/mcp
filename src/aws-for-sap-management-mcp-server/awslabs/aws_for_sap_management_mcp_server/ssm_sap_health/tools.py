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

"""SSM for SAP health summary and report tools for MCP server."""

import asyncio
from boto3 import Session
from awslabs.aws_for_sap_management_mcp_server.client_factory import get_aws_client
from awslabs.aws_for_sap_management_mcp_server.common import format_datetime
from awslabs.aws_for_sap_management_mcp_server.ssm_sap_health.models import (
    ApplicationHealthEntry,
    BackupStatusEntry,
    CloudWatchMetricsEntry,
    ComponentEntry,
    ConfigCheckEntry,
    FilesystemUsageEntry,
    HealthReportResponse,
    HealthSummaryResponse,
    LogBackupStatusEntry,
    RuleResultEntry,
    SubCheckEntry,
)
from datetime import datetime, timedelta, timezone
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


# Parent component types in SSM for SAP — these are logical groupings,
# not actual host-level nodes. We extract metadata from them but only
# render child components (HANA_NODE, ASCS, ERS, APP, etc.) in reports.
_PARENT_COMPONENT_TYPES = {'HANA', 'ABAP', 'WEBDISP'}


# Status emoji mappings for Markdown report
_STATUS_EMOJI = {
    'ACTIVATED': '🟢',
    'SUCCESS': '🟢',
    'PASS': '🟢',
    'STARTING': '🟡',
    'REGISTERING': '🟡',
    'IN_PROGRESS': '🟡',
    'STOPPED': '🔴',
    'STOPPING': '🔴',
    'FAILED': '🔴',
    'REGISTRATION_FAILED': '🔴',
    'REFRESH_FAILED': '🔴',
    'DELETING': '⚪',
    'UNKNOWN': '⚪',
    'ERROR': '🔴',
    'WARN': '🟡',
    'INFO': '🔵',
}


def _emoji(status: str) -> str:
    """Get status emoji, defaulting to ⚪ for unknown statuses."""
    return _STATUS_EMOJI.get(status, '⚪')


def _format_bytes(num_bytes: float) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f'{num_bytes:.0f} B'
    elif num_bytes < 1024 * 1024:
        return f'{num_bytes / 1024:.1f} KB'
    elif num_bytes < 1024 * 1024 * 1024:
        return f'{num_bytes / (1024 * 1024):.1f} MB'
    else:
        return f'{num_bytes / (1024 * 1024 * 1024):.2f} GB'


def _get_all_app_ids(client) -> List[str]:
    """Retrieve all application IDs from SSM for SAP."""
    app_ids = []
    response = client.list_applications()
    for app in response.get('Applications', []):
        app_id = app.get('Id')
        if app_id:
            app_ids.append(app_id)
    while response.get('NextToken'):
        response = client.list_applications(NextToken=response['NextToken'])
        for app in response.get('Applications', []):
            app_id = app.get('Id')
            if app_id:
                app_ids.append(app_id)
    return app_ids


def _discover_cwagent_dimensions(
    cloudwatch_client,
    metric_name: str,
    instance_id: str,
) -> Optional[List[Dict[str, str]]]:
    """Discover actual CWAgent dimensions for a metric on an instance.

    CWAgent metrics often include extra dimensions like CustomComponentName,
    path, device, fstype. This uses list_metrics to find the real dimensions.

    Returns the first matching dimension set, or None if not found.
    """
    try:
        resp = cloudwatch_client.list_metrics(
            Namespace='CWAgent',
            MetricName=metric_name,
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        )
        metrics = resp.get('Metrics', [])
        if metrics:
            return metrics[0].get('Dimensions', [])
    except Exception:
        pass
    return None


def _discover_cwagent_disk_dimensions(
    cloudwatch_client,
    instance_id: str,
    target_paths: Optional[List[str]] = None,
) -> List[List[Dict[str, str]]]:
    """Discover CWAgent disk_used_percent dimensions for SAP-relevant paths.

    Returns a list of dimension sets, one per matching path.
    """
    if target_paths is None:
        target_paths = ['/', '/usr/sap', '/hana/data', '/hana/log', '/hana/shared', '/backup']
    results = []
    try:
        resp = cloudwatch_client.list_metrics(
            Namespace='CWAgent',
            MetricName='disk_used_percent',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        )
        for metric in resp.get('Metrics', []):
            dims = metric.get('Dimensions', [])
            dim_map = {d['Name']: d['Value'] for d in dims}
            path = dim_map.get('path', '')
            if path in target_paths:
                results.append(dims)
    except Exception:
        pass
    return results


async def _run_ssm_command(
    ssm_client,
    instance_id: str,
    command: str,
    timeout_seconds: int = 30,
) -> Optional[str]:
    """Run a shell command on an instance via SSM and return the output.

    Sends the command via AWS-RunShellScript and polls for completion.
    Returns the stdout output or None on failure.
    """
    try:
        resp = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [command]},
            TimeoutSeconds=60,
        )
        cmd_id = resp.get('Command', {}).get('CommandId')
        if not cmd_id:
            return None

        # Poll for completion
        for _ in range(timeout_seconds // 3):
            await asyncio.sleep(3)
            try:
                inv_resp = ssm_client.get_command_invocation(
                    CommandId=cmd_id,
                    InstanceId=instance_id,
                )
                status = inv_resp.get('Status', '')
                if status in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
                    if status == 'Success':
                        return inv_resp.get('StandardOutputContent', '')
                    return None
            except ssm_client.exceptions.InvocationDoesNotExist:
                continue
            except Exception:
                return None
        return None
    except Exception:
        return None


def _run_ssm_command_sync(
    ssm_client,
    instance_id: str,
    command: str,
    timeout_seconds: int = 30,
) -> Optional[str]:
    """Run a shell command on an instance via SSM and return the output (sync version).

    Sends the command via AWS-RunShellScript and polls for completion using time.sleep.
    Returns the stdout output or None on failure.
    """
    import time as _time

    try:
        resp = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [command]},
            TimeoutSeconds=60,
        )
        cmd_id = resp.get('Command', {}).get('CommandId')
        if not cmd_id:
            return None

        for _ in range(timeout_seconds // 3):
            _time.sleep(3)
            try:
                inv_resp = ssm_client.get_command_invocation(
                    CommandId=cmd_id,
                    InstanceId=instance_id,
                )
                status = inv_resp.get('Status', '')
                if status in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
                    if status == 'Success':
                        return inv_resp.get('StandardOutputContent', '')
                    return None
            except Exception:
                continue
        return None
    except Exception:
        return None


def _has_recent_config_checks(config_check_ops: list, max_age_hours: int = 24) -> bool:
    """Check if there are config check results within the given age threshold."""
    if not config_check_ops:
        return False
    now = datetime.now(timezone.utc)
    for op in config_check_ops:
        # Real API uses EndTime; fall back to LastUpdatedTime for compatibility
        last_updated = op.get('EndTime') or op.get('LastUpdatedTime')
        if last_updated:
            if isinstance(last_updated, datetime):
                ts = (
                    last_updated
                    if last_updated.tzinfo
                    else last_updated.replace(tzinfo=timezone.utc)
                )
            else:
                continue
            if (now - ts).total_seconds() < max_age_hours * 3600:
                return True
    return False


def _trigger_config_checks(client, app_id: str) -> list:
    """Trigger all available config checks for an application and return the operations."""
    try:
        defs_response = client.list_configuration_check_definitions()
        check_ids = [
            c.get('Id') for c in defs_response.get('ConfigurationChecks', []) if c.get('Id')
        ]
        if not check_ids:
            return []
        response = client.start_configuration_checks(
            ApplicationId=app_id,
            ConfigurationCheckIds=check_ids,
        )
        return response.get('ConfigurationCheckOperations', [])
    except Exception:
        return []


async def _wait_for_config_checks(
    client,
    operations: list,
    poll_interval_seconds: int = 10,
    max_wait_seconds: int = 180,
) -> None:
    """Poll config check operations until all complete or timeout is reached.

    Args:
        client: SSM for SAP boto3 client.
        operations: List of config check operations returned by start_configuration_checks.
        poll_interval_seconds: Seconds between polling attempts. Default: 10.
        max_wait_seconds: Maximum total seconds to wait. Default: 180 (3 minutes).
    """
    operation_ids = [op.get('OperationId') for op in operations if op.get('OperationId')]
    if not operation_ids:
        return

    terminal_statuses = {'SUCCESS', 'FAILED', 'ERROR'}
    elapsed = 0

    while elapsed < max_wait_seconds:
        all_done = True
        for op_id in operation_ids:
            try:
                resp = client.get_configuration_check_operation(OperationId=op_id)
                status = resp.get('ConfigurationCheckOperation', {}).get('Status', '')
                if status not in terminal_statuses:
                    all_done = False
                    break
            except Exception:
                # If we can't poll, skip this one and move on
                pass
        if all_done:
            return
        await asyncio.sleep(poll_interval_seconds)
        elapsed += poll_interval_seconds

    logger.warning(
        f'Config check polling timed out after {max_wait_seconds}s for app operations: {operation_ids}'
    )


def _extract_ec2_ids(detail: dict) -> List[str]:
    """Extract EC2 instance IDs from a component detail response.

    Checks multiple paths in order:
    1. Hosts[].EC2InstanceId / InstanceId (standard for HANA components)
    2. AssociatedHost.Ec2InstanceId (used by HANA_NODE components)
    3. PrimaryHost / SecondaryHost (fallback for HA setups)
    """
    ids = []
    seen = set()

    # Path 1: Hosts array
    for host in detail.get('Hosts', []):
        iid = host.get('EC2InstanceId') or host.get('InstanceId')
        if iid and iid not in seen:
            ids.append(iid)
            seen.add(iid)

    # Path 2: AssociatedHost (HANA_NODE components)
    assoc = detail.get('AssociatedHost')
    if assoc:
        iid = assoc.get('Ec2InstanceId') or assoc.get('EC2InstanceId')
        if iid and iid not in seen:
            ids.append(iid)
            seen.add(iid)

    # Path 3: PrimaryHost / SecondaryHost fallback
    for key in ('PrimaryHost', 'SecondaryHost'):
        host_info = detail.get(key)
        if isinstance(host_info, dict):
            iid = host_info.get('Ec2InstanceId') or host_info.get('EC2InstanceId')
            if iid and iid not in seen:
                ids.append(iid)
                seen.add(iid)
        elif isinstance(host_info, str) and host_info.startswith('i-') and host_info not in seen:
            ids.append(host_info)
            seen.add(host_info)

    return ids


async def _get_app_summary(
    client,
    app_id: str,
    ssm_client=None,
    backup_client=None,
    cloudwatch_client=None,
    include_config_checks: bool = True,
    include_subchecks: bool = True,
    include_rule_results: bool = True,
    include_log_backup_status: bool = True,
    include_aws_backup_status: bool = True,
    include_cloudwatch_metrics: bool = True,
    auto_trigger_config_checks: bool = True,
    config_check_max_age_hours: int = 24,
) -> ApplicationHealthEntry:
    """Get comprehensive health status for a single SAP application.

    Gathers application status, components, config checks (auto-triggering if none recent),
    CloudWatch metrics, SSM log backup status, and AWS Backup status.

    Returns:
        ApplicationHealthEntry with full health data.
    """
    try:
        response = client.get_application(ApplicationId=app_id)
        app = response.get('Application', {})
        app_status = app.get('Status', 'UNKNOWN')
        discovery_status = app.get('DiscoveryStatus', 'UNKNOWN')
        app_type = app.get('Type', 'UNKNOWN')
        status_message = app.get('StatusMessage')

        # Components
        components = []
        ec2_instance_ids = []
        try:
            comp_response = client.list_components(ApplicationId=app_id)
            for comp in comp_response.get('Components', []):
                comp_id = comp.get('ComponentId', '')
                try:
                    detail = client.get_component(ApplicationId=app_id, ComponentId=comp_id).get(
                        'Component', {}
                    )
                    instance_ids = _extract_ec2_ids(detail)
                    for iid in instance_ids:
                        if iid not in ec2_instance_ids:
                            ec2_instance_ids.append(iid)

                    # Extract richer HANA details
                    hana_version = None
                    replication_mode = None
                    operation_mode = None
                    databases = None
                    cluster_status = None
                    comp_type = detail.get('ComponentType', 'UNKNOWN')

                    # Skip parent components — extract metadata but don't add to output
                    if comp_type in _PARENT_COMPONENT_TYPES:
                        if comp_type == 'HANA':
                            hdb_info = detail.get('HdbVersion') or detail.get('HanaVersion')
                            dbs = detail.get('Databases')
                            if dbs and isinstance(dbs, list):
                                # Store on the first child we find later
                                pass
                        continue

                    if comp_type in ('HANA_NODE',):
                        hdb_info = detail.get('HdbVersion') or detail.get('HanaVersion')
                        if hdb_info:
                            hana_version = str(hdb_info)
                        # Resilience info (nested in Resilience dict for HANA_NODE)
                        resilience = detail.get('Resilience', {})
                        repl = (
                            resilience.get('HsrReplicationMode')
                            or detail.get('ReplicationMode')
                            or detail.get('SystemReplicationMode')
                        )
                        if repl:
                            replication_mode = str(repl)
                        op_mode = (
                            resilience.get('HsrOperationMode')
                            or detail.get('OperationMode')
                            or detail.get('SystemReplicationOperationMode')
                        )
                        if op_mode:
                            operation_mode = str(op_mode)
                        cls_status = resilience.get('ClusterStatus')
                        if cls_status:
                            cluster_status = str(cls_status)
                        dbs = detail.get('Databases')
                        if dbs and isinstance(dbs, list):
                            databases = [
                                str(d.get('DatabaseId', d) if isinstance(d, dict) else d)
                                for d in dbs
                            ]

                    components.append(
                        ComponentEntry(
                            component_id=comp_id,
                            component_type=comp_type,
                            status=detail.get('Status', 'UNKNOWN'),
                            sid=detail.get('Sid', '-'),
                            ec2_instance_ids=instance_ids,
                            hana_version=hana_version,
                            replication_mode=replication_mode,
                            operation_mode=operation_mode,
                            databases=databases,
                            cluster_status=cluster_status,
                        )
                    )
                except Exception:
                    components.append(ComponentEntry(component_id=comp_id, status='ERROR'))
        except Exception:
            pass

        # Config checks
        config_checks = []
        if include_config_checks:
            try:
                cc_response = client.list_configuration_check_operations(
                    ApplicationId=app_id,
                    ListMode='LATEST_PER_CHECK',
                )
                check_ops = cc_response.get('ConfigurationCheckOperations', [])

                # Save previous results before potentially triggering new checks
                previous_check_ops = list(check_ops)

                # Auto-trigger if no recent checks
                triggered = False
                if auto_trigger_config_checks and not _has_recent_config_checks(
                    check_ops, config_check_max_age_hours
                ):
                    new_ops = _trigger_config_checks(client, app_id)
                    if new_ops:
                        triggered = True
                        # Wait for triggered checks to complete
                        await _wait_for_config_checks(client, new_ops)
                        # Re-fetch to get the completed results
                        cc_response = client.list_configuration_check_operations(
                            ApplicationId=app_id,
                            ListMode='LATEST_PER_CHECK',
                        )
                        check_ops = cc_response.get('ConfigurationCheckOperations', [])

                        # If new checks are still in progress, prefer previous results
                        any_in_progress = any(op.get('Status') == 'INPROGRESS' for op in check_ops)
                        if any_in_progress and previous_check_ops:
                            check_ops = previous_check_ops

                for op in check_ops:
                    # Build result summary from RuleStatusCounts if available
                    result = op.get('Result', '-')
                    rule_counts = op.get('RuleStatusCounts', {})
                    if rule_counts and isinstance(rule_counts, dict):
                        parts = []
                        for key in ('Failed', 'Warning', 'Passed', 'Info', 'Unknown'):
                            val = rule_counts.get(key, 0)
                            if val:
                                parts.append(f'{key}: {val}')
                        if parts:
                            result = ', '.join(parts)

                    # Fetch sub-check details when requested
                    subchecks = []
                    if include_subchecks:
                        operation_id = op.get('Id') or op.get('OperationId', '')
                        # Fallback: if operation ID is missing, try list_operations
                        if not operation_id:
                            try:
                                ops_resp = client.list_operations(
                                    ApplicationId=app_id,
                                    MaxResults=10,
                                )
                                for list_op in ops_resp.get('Operations', []):
                                    if list_op.get(
                                        'Type'
                                    ) == 'CONFIGURATION_CHECK' and list_op.get('Id'):
                                        operation_id = list_op['Id']
                                        break
                            except Exception:
                                pass
                        if operation_id:
                            try:
                                sc_response = client.list_sub_check_results(
                                    OperationId=operation_id
                                )
                                for sc in sc_response.get('SubCheckResults', []):
                                    sc_id = sc.get('Id', '')
                                    rule_results = []
                                    if include_rule_results and sc_id:
                                        try:
                                            rr_response = client.list_sub_check_rule_results(
                                                SubCheckResultId=sc_id
                                            )
                                            for rule in rr_response.get('RuleResults', []):
                                                rule_results.append(
                                                    RuleResultEntry(
                                                        rule_id=rule.get('Id', 'UNKNOWN'),
                                                        description=rule.get('Description'),
                                                        status=rule.get('Status', 'UNKNOWN'),
                                                        message=rule.get('Message'),
                                                        metadata=rule.get('Metadata'),
                                                    )
                                                )
                                        except Exception:
                                            pass
                                    subchecks.append(
                                        SubCheckEntry(
                                            id=sc_id or None,
                                            name=sc.get('Name', 'UNKNOWN'),
                                            result=sc.get('Result', 'UNKNOWN'),
                                            description=sc.get('Description'),
                                            rule_results=rule_results,
                                        )
                                    )
                            except Exception:
                                pass

                    config_checks.append(
                        ConfigCheckEntry(
                            check_id=op.get('ConfigurationCheckId', 'UNKNOWN'),
                            status=op.get('Status', 'UNKNOWN'),
                            result=result,
                            last_updated=format_datetime(
                                op.get('EndTime') or op.get('LastUpdatedTime')
                            ),
                            triggered_by_summary=triggered,
                            subchecks=subchecks,
                        )
                    )
            except Exception:
                pass

        # CloudWatch metrics
        cw_metrics = []
        if include_cloudwatch_metrics and cloudwatch_client and ec2_instance_ids:
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(hours=1)
            for instance_id in ec2_instance_ids:
                cpu_avg = None
                cpu_max = None
                status_check = 'N/A'
                try:
                    cpu_resp = cloudwatch_client.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=now,
                        Period=3600,
                        Statistics=['Average', 'Maximum'],
                    )
                    dps = cpu_resp.get('Datapoints', [])
                    if dps:
                        cpu_avg = round(dps[0].get('Average', 0), 1)
                        cpu_max = round(dps[0].get('Maximum', 0), 1)
                except Exception:
                    pass
                try:
                    sc_resp = cloudwatch_client.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='StatusCheckFailed',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=now,
                        Period=3600,
                        Statistics=['Maximum'],
                    )
                    dps = sc_resp.get('Datapoints', [])
                    if dps:
                        failed = dps[0].get('Maximum', 0)
                        status_check = 'OK' if failed == 0 else 'FAILED'
                    else:
                        status_check = 'No data'
                except Exception:
                    status_check = 'Error'
                # CWAgent metrics (memory, disk, network)
                memory_used_pct = None
                disk_used_pct = None
                network_in = None
                network_out = None
                try:
                    mem_dims = _discover_cwagent_dimensions(
                        cloudwatch_client,
                        'mem_used_percent',
                        instance_id,
                    )
                    if mem_dims:
                        mem_resp = cloudwatch_client.get_metric_statistics(
                            Namespace='CWAgent',
                            MetricName='mem_used_percent',
                            Dimensions=mem_dims,
                            StartTime=start_time,
                            EndTime=now,
                            Period=3600,
                            Statistics=['Average'],
                        )
                        dps = mem_resp.get('Datapoints', [])
                        if dps:
                            memory_used_pct = round(dps[0].get('Average', 0), 1)
                except Exception:
                    pass
                try:
                    # Query SAP-relevant disk paths
                    disk_dim_sets = _discover_cwagent_disk_dimensions(
                        cloudwatch_client,
                        instance_id,
                    )
                    if disk_dim_sets:
                        # Use root '/' path for the summary metric; collect all for detail
                        for dim_set in disk_dim_sets:
                            dim_map = {d['Name']: d['Value'] for d in dim_set}
                            if dim_map.get('path') == '/':
                                disk_resp = cloudwatch_client.get_metric_statistics(
                                    Namespace='CWAgent',
                                    MetricName='disk_used_percent',
                                    Dimensions=dim_set,
                                    StartTime=start_time,
                                    EndTime=now,
                                    Period=3600,
                                    Statistics=['Average'],
                                )
                                dps = disk_resp.get('Datapoints', [])
                                if dps:
                                    disk_used_pct = round(dps[0].get('Average', 0), 1)
                                break
                except Exception:
                    pass
                try:
                    net_dims = _discover_cwagent_dimensions(
                        cloudwatch_client,
                        'net_bytes_recv',
                        instance_id,
                    )
                    if net_dims:
                        net_in_resp = cloudwatch_client.get_metric_statistics(
                            Namespace='CWAgent',
                            MetricName='net_bytes_recv',
                            Dimensions=net_dims,
                            StartTime=start_time,
                            EndTime=now,
                            Period=3600,
                            Statistics=['Sum'],
                        )
                        dps = net_in_resp.get('Datapoints', [])
                        if dps:
                            network_in = round(dps[0].get('Sum', 0), 0)
                except Exception:
                    pass
                try:
                    net_dims = _discover_cwagent_dimensions(
                        cloudwatch_client,
                        'net_bytes_sent',
                        instance_id,
                    )
                    if net_dims:
                        net_out_resp = cloudwatch_client.get_metric_statistics(
                            Namespace='CWAgent',
                            MetricName='net_bytes_sent',
                            Dimensions=net_dims,
                            StartTime=start_time,
                            EndTime=now,
                            Period=3600,
                            Statistics=['Sum'],
                        )
                        dps = net_out_resp.get('Datapoints', [])
                        if dps:
                            network_out = round(dps[0].get('Sum', 0), 0)
                except Exception:
                    pass
                cw_metrics.append(
                    CloudWatchMetricsEntry(
                        instance_id=instance_id,
                        cpu_avg=cpu_avg,
                        cpu_max=cpu_max,
                        status_check=status_check,
                        memory_used_pct=memory_used_pct,
                        disk_used_pct=disk_used_pct,
                        network_in=network_in,
                        network_out=network_out,
                    )
                )

        # Log backup status — only for HANA applications
        log_backup = []
        if include_log_backup_status and ssm_client and ec2_instance_ids and app_type == 'HANA':
            for instance_id in ec2_instance_ids:
                agent_status = 'UNKNOWN'
                agent_version = None
                backup_check_status = None
                backup_check_details = None
                try:
                    resp = ssm_client.describe_instance_information(
                        Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
                    )
                    instances = resp.get('InstanceInformationList', [])
                    if instances:
                        agent_status = instances[0].get('PingStatus', 'UNKNOWN')
                        agent_version = instances[0].get('AgentVersion')
                    else:
                        agent_status = 'Not managed'
                except Exception:
                    agent_status = 'Error'

                # Try to get HANA log backup status via SSM command
                if agent_status == 'Online':
                    try:
                        # Query by document name using paginator
                        all_cmds = []
                        paginator = ssm_client.get_paginator('list_commands')
                        for page in paginator.paginate(
                            Filters=[
                                {
                                    'key': 'DocumentName',
                                    'value': 'AWSSystemsManagerSAP-HanaLogBackupStatusCheck',
                                }
                            ],
                            PaginationConfig={'MaxItems': 50},
                        ):
                            all_cmds.extend(page.get('Commands', []))
                        # Find commands targeting this instance
                        matching = [c for c in all_cmds if instance_id in c.get('InstanceIds', [])]
                        if matching:
                            cmd_id = matching[0].get('CommandId')
                            if cmd_id:
                                # Use list_command_invocations with details to get
                                # the PerformAction step output (step 3)
                                try:
                                    inv_detail = ssm_client.list_command_invocations(
                                        CommandId=cmd_id,
                                        InstanceId=instance_id,
                                        Details=True,
                                    )
                                    for inv in inv_detail.get('CommandInvocations', []):
                                        backup_check_status = inv.get('Status', 'UNKNOWN')
                                        plugins = inv.get('CommandPlugins', [])
                                        for plugin in plugins:
                                            if plugin.get('Name') == 'PerformAction':
                                                output = plugin.get('Output', '')
                                                if output:
                                                    # Extract JSON payload after pip install noise
                                                    json_start = output.find('{"executionStatus"')
                                                    if json_start >= 0:
                                                        backup_check_details = output[
                                                            json_start : json_start + 500
                                                        ]
                                                    else:
                                                        backup_check_details = output[:500]
                                                break
                                except Exception as e:
                                    logger.warning(
                                        f'Error getting invocation details for {instance_id}: {e}'
                                    )
                    except Exception as e:
                        logger.warning(f'Error checking log backup for {instance_id}: {e}')

                log_backup.append(
                    LogBackupStatusEntry(
                        instance_id=instance_id,
                        ssm_agent_status=agent_status,
                        agent_version=agent_version,
                        log_backup_status=backup_check_status,
                        log_backup_details=backup_check_details,
                    )
                )

        # AWS Backup status — only for HANA applications
        backup_entries = []
        if include_aws_backup_status and backup_client and ec2_instance_ids and app_type == 'HANA':
            try:
                # Query SAP HANA specific backups first
                # SAP HANA backup ARNs use format: arn:aws:ssm-sap:REGION:ACCOUNT:HANA/APP_ID/DB/SID
                try:
                    jobs_resp = backup_client.list_backup_jobs(
                        ByResourceType='SAP HANA on Amazon EC2',
                        MaxResults=50,
                    )
                    sap_jobs = jobs_resp.get('BackupJobs', [])
                    # Filter jobs matching this application by app_id in the ResourceArn
                    app_jobs = []
                    for job in sap_jobs:
                        resource_arn = job.get('ResourceArn', '')
                        if app_id in resource_arn:
                            app_jobs.append(job)
                    if app_jobs:
                        # Show all recent jobs grouped by state to surface EXPIRED/FAILED
                        seen_states = set()
                        for job in app_jobs:
                            b_status = job.get('State', 'UNKNOWN')
                            # Always include the first job of each state
                            if b_status in seen_states:
                                continue
                            seen_states.add(b_status)
                            last_backup = format_datetime(
                                job.get('CompletionDate') or job.get('CreationDate')
                            )
                            backup_type = job.get('BackupType', '')
                            status_str = f'{b_status} ({backup_type})' if backup_type else b_status
                            # Capture failure reason from the API
                            failure_reason = None
                            if b_status in ('FAILED', 'EXPIRED', 'ABORTED'):
                                failure_reason = job.get('StatusMessage') or job.get(
                                    'MessageCategory'
                                )
                                # If list_backup_jobs didn't return StatusMessage,
                                # call describe_backup_job for the detailed failure reason
                                job_id = job.get('BackupJobId', '')
                                if not failure_reason and job_id:
                                    try:
                                        detail_resp = backup_client.describe_backup_job(
                                            BackupJobId=job_id
                                        )
                                        failure_reason = detail_resp.get(
                                            'StatusMessage'
                                        ) or detail_resp.get('MessageCategory')
                                    except Exception:
                                        pass
                            backup_entries.append(
                                BackupStatusEntry(
                                    instance_id=app_id,
                                    last_backup=last_backup,
                                    backup_status=status_str,
                                    failure_reason=failure_reason,
                                )
                            )
                    else:
                        # Fallback: query per-instance by EC2 resource ARN
                        for instance_id in ec2_instance_ids:
                            last_backup = None
                            b_status = 'N/A'
                            failure_reason = None
                            try:
                                jobs_resp = backup_client.list_backup_jobs(
                                    ByResourceArn=f'arn:aws:ec2:*:*:instance/{instance_id}',
                                    MaxResults=1,
                                )
                                jobs = jobs_resp.get('BackupJobs', [])
                                if jobs:
                                    b_status = jobs[0].get('State', 'UNKNOWN')
                                    last_backup = format_datetime(jobs[0].get('CompletionDate'))
                                    if b_status in ('FAILED', 'EXPIRED', 'ABORTED'):
                                        failure_reason = jobs[0].get('StatusMessage') or jobs[
                                            0
                                        ].get('MessageCategory')
                                        job_id = jobs[0].get('BackupJobId', '')
                                        if not failure_reason and job_id:
                                            try:
                                                detail_resp = backup_client.describe_backup_job(
                                                    BackupJobId=job_id
                                                )
                                                failure_reason = detail_resp.get(
                                                    'StatusMessage'
                                                ) or detail_resp.get('MessageCategory')
                                            except Exception:
                                                pass
                                else:
                                    b_status = 'No backups'
                            except Exception:
                                b_status = 'Error'
                            backup_entries.append(
                                BackupStatusEntry(
                                    instance_id=instance_id,
                                    last_backup=last_backup,
                                    backup_status=b_status,
                                    failure_reason=failure_reason,
                                )
                            )
                except Exception:
                    # Fallback: query per-instance by EC2 resource ARN
                    for instance_id in ec2_instance_ids:
                        last_backup = None
                        b_status = 'N/A'
                        failure_reason = None
                        try:
                            jobs_resp = backup_client.list_backup_jobs(
                                ByResourceArn=f'arn:aws:ec2:*:*:instance/{instance_id}',
                                MaxResults=1,
                            )
                            jobs = jobs_resp.get('BackupJobs', [])
                            if jobs:
                                b_status = jobs[0].get('State', 'UNKNOWN')
                                last_backup = format_datetime(jobs[0].get('CompletionDate'))
                                if b_status in ('FAILED', 'EXPIRED', 'ABORTED'):
                                    failure_reason = jobs[0].get('StatusMessage') or jobs[0].get(
                                        'MessageCategory'
                                    )
                                    job_id = jobs[0].get('BackupJobId', '')
                                    if not failure_reason and job_id:
                                        try:
                                            detail_resp = backup_client.describe_backup_job(
                                                BackupJobId=job_id
                                            )
                                            failure_reason = detail_resp.get(
                                                'StatusMessage'
                                            ) or detail_resp.get('MessageCategory')
                                        except Exception:
                                            pass
                            else:
                                b_status = 'No backups'
                        except Exception:
                            b_status = 'Error'
                        backup_entries.append(
                            BackupStatusEntry(
                                instance_id=instance_id,
                                last_backup=last_backup,
                                backup_status=b_status,
                                failure_reason=failure_reason,
                            )
                        )
            except Exception:
                pass

        # Filesystem usage via SSM RunCommand
        fs_entries = []
        if include_log_backup_status and ssm_client and ec2_instance_ids:
            for instance_id in ec2_instance_ids:
                fs_info = None
                fs_status = 'N/A'
                try:
                    # Check if instance is managed by SSM first (reuse log_backup data)
                    managed = any(
                        lb.instance_id == instance_id and lb.ssm_agent_status == 'Online'
                        for lb in log_backup
                    )
                    if managed:
                        # Run df -h to get filesystem usage for SAP-relevant paths
                        output = await _run_ssm_command(
                            ssm_client,
                            instance_id,
                            'df -h / /usr/sap /hana/data /hana/log /hana/shared /backup 2>/dev/null | sort -u',
                        )
                        if output:
                            fs_info = output[:1000]
                            fs_status = 'Success'
                        else:
                            # Fallback: look for recent df command results via SSM command history
                            try:
                                cmd_resp = ssm_client.list_commands(
                                    InstanceId=instance_id,
                                    Filters=[
                                        {'key': 'DocumentName', 'value': 'AWS-RunShellScript'}
                                    ],
                                    MaxResults=5,
                                )
                                for cmd in cmd_resp.get('Commands', []):
                                    params = cmd.get('Parameters', {})
                                    cmds = params.get('commands', [])
                                    if any('df' in c for c in cmds):
                                        cmd_id = cmd.get('CommandId')
                                        if cmd_id:
                                            inv_resp = ssm_client.get_command_invocation(
                                                CommandId=cmd_id,
                                                InstanceId=instance_id,
                                            )
                                            fs_status = inv_resp.get('Status', 'UNKNOWN')
                                            hist_output = inv_resp.get('StandardOutputContent', '')
                                            if hist_output:
                                                fs_info = hist_output[:1000]
                                        break
                            except Exception:
                                pass
                    else:
                        fs_status = 'Not managed'
                except Exception:
                    fs_status = 'Error'
                fs_entries.append(
                    FilesystemUsageEntry(
                        instance_id=instance_id,
                        filesystem_info=fs_info,
                        status=fs_status,
                    )
                )

        return ApplicationHealthEntry(
            application_id=app_id,
            app_type=app_type,
            status=app_status,
            discovery_status=discovery_status,
            component_count=len(components),
            status_message=status_message,
            components=components,
            config_checks=config_checks,
            cloudwatch_metrics=cw_metrics,
            backup_status=backup_entries,
            log_backup_status=log_backup,
            filesystem_usage=fs_entries,
        )
    except Exception as e:
        return ApplicationHealthEntry(
            application_id=app_id,
            status='ERROR',
            discovery_status='ERROR',
            status_message=str(e),
        )


def _check_app_health(
    client,
    ssm_client,
    backup_client,
    cloudwatch_client,
    app_id: str,
    include_config_checks: bool,
    include_subchecks: bool,
    include_rule_results: bool,
    include_log_backup_status: bool,
    include_aws_backup_status: bool,
    include_cloudwatch_metrics: bool,
) -> tuple:
    """Check health of a single SAP application.

    Returns:
        Tuple of (markdown_report, app_status, discovery_status)
    """
    lines = []
    app_status = 'UNKNOWN'
    discovery_status = 'UNKNOWN'

    try:
        response = client.get_application(ApplicationId=app_id)
        app = response.get('Application', {})
        app_status = app.get('Status', 'UNKNOWN')
        discovery_status = app.get('DiscoveryStatus', 'UNKNOWN')
        app_type = app.get('Type', 'UNKNOWN')

        # Translate status for display — only show if unhealthy
        _status_labels = {
            'ACTIVATED': 'Running and monitored',
            'STOPPED': 'Stopped',
            'STOPPING': 'Shutting down',
            'STARTING': 'Starting up',
            'FAILED': 'Failed — investigate immediately',
            'REGISTERING': 'Registration in progress',
            'DELETING': 'Being removed',
        }
        _discovery_labels = {
            'SUCCESS': 'Components discovered successfully',
            'REFRESH_FAILED': 'Discovery refresh failed — component info may be stale',
            'REGISTRATION_FAILED': 'Registration did not complete successfully',
            'REGISTERING': 'Discovery in progress',
            'DELETING': 'Being removed',
        }

        is_healthy = app_status == 'ACTIVATED' and discovery_status == 'SUCCESS'

        lines.append(f'## Application: `{app_id}`')
        lines.append('')

        if not is_healthy:
            # Only show status when something is wrong
            lines.append('| Property | Value |')
            lines.append('|----------|-------|')
            lines.append(f'| Type | {app_type} |')
            status_label = _status_labels.get(app_status, app_status)
            lines.append(f'| Status | {_emoji(app_status)} {status_label} |')
            disc_label = _discovery_labels.get(discovery_status, discovery_status)
            lines.append(f'| Discovery | {_emoji(discovery_status)} {disc_label} |')
            if app.get('StatusMessage'):
                lines.append(f'| Message | {app["StatusMessage"]} |')
            lines.append('')

        # Components — present as readable nodes, not raw API structures
        ec2_instance_ids = []
        try:
            comp_response = client.list_components(ApplicationId=app_id)
            components = comp_response.get('Components', [])
            if components:
                # Collect component details first
                node_details = []
                hana_version = None
                databases = []
                for comp in components:
                    comp_id = comp.get('ComponentId', '')
                    try:
                        detail = client.get_component(
                            ApplicationId=app_id, ComponentId=comp_id
                        ).get('Component', {})
                        comp_type = detail.get('ComponentType', 'UNKNOWN')
                        instance_ids = _extract_ec2_ids(detail)
                        for iid in instance_ids:
                            if iid not in ec2_instance_ids:
                                ec2_instance_ids.append(iid)

                        # Skip parent components — extract metadata but don't render
                        # Parent types (HANA, ABAP) are logical groupings;
                        # child types (HANA_NODE, ASCS, ERS, etc.) are the actual nodes.
                        if comp_type in _PARENT_COMPONENT_TYPES:
                            dbs = detail.get('Databases', [])
                            if dbs:
                                databases = dbs
                            ver = detail.get('HdbVersion') or detail.get('HanaVersion')
                            if ver and not hana_version:
                                hana_version = ver
                            continue  # Skip parent — show only child nodes

                        # For HANA_NODE or other components with instances
                        comp_status = detail.get('Status', 'UNKNOWN')
                        resilience = detail.get('Resilience', {})
                        repl = (
                            resilience.get('HsrReplicationMode')
                            or detail.get('ReplicationMode')
                            or ''
                        )
                        op_mode = (
                            resilience.get('HsrOperationMode') or detail.get('OperationMode') or ''
                        )
                        cluster = resilience.get('ClusterStatus', '')
                        ver = detail.get('HdbVersion') or detail.get('HanaVersion')
                        if ver and not hana_version:
                            hana_version = ver

                        # Determine role label
                        if repl == 'PRIMARY' or op_mode == 'PRIMARY':
                            role = 'Primary'
                        elif repl and repl != 'NONE':
                            role = (
                                f'Secondary ({repl}/{op_mode})'
                                if op_mode and op_mode != 'NONE'
                                else f'Secondary ({repl})'
                            )
                        else:
                            role = comp_type

                        # Extract hostname from component ID (e.g. HDB-HDB00-sappridb -> sappridb)
                        hostname = comp_id.rsplit('-', 1)[-1] if '-' in comp_id else comp_id

                        node_details.append(
                            {
                                'hostname': hostname,
                                'role': role,
                                'comp_type': comp_type,
                                'status': comp_status,
                                'cluster': cluster,
                                'instance_ids': instance_ids,
                            }
                        )
                    except Exception:
                        node_details.append(
                            {
                                'hostname': comp_id,
                                'role': '-',
                                'comp_type': 'UNKNOWN',
                                'status': 'Error',
                                'cluster': '-',
                                'instance_ids': [],
                            }
                        )

                # Render system overview
                lines.append('| Property | Value |')
                lines.append('|----------|-------|')
                lines.append(f'| Type | {app_type} |')
                if hana_version:
                    lines.append(f'| HANA Version | {hana_version} |')
                if databases:
                    lines.append(f'| Databases | {", ".join(databases)} |')
                lines.append('')

                # Render nodes table
                # Determine table layout based on app type and component composition
                is_single_node = len(node_details) == 1
                is_abap = app_type == 'SAP_ABAP'

                if is_abap:
                    lines.append('### SAP Components')
                else:
                    lines.append('### SAP HANA Nodes')
                lines.append('')

                if is_single_node:
                    # Single node (HANA or ABAP) — no Role/Cluster columns
                    lines.append('| Hostname | Status | EC2 Instance |')
                    lines.append('|----------|--------|--------------|')
                elif is_abap:
                    # ABAP — show Component Type, no Cluster
                    lines.append('| Hostname | Component Type | Status | EC2 Instance |')
                    lines.append('|----------|----------------|--------|--------------|')
                else:
                    # HA HANA — show Role and Cluster
                    lines.append('| Hostname | Role | Status | Cluster | EC2 Instance |')
                    lines.append('|----------|------|--------|---------|--------------|')

                for node in node_details:
                    ids_str = (
                        ', '.join(f'`{i}`' for i in node['instance_ids'])
                        if node['instance_ids']
                        else '-'
                    )
                    status_str = f'{_emoji(node["status"])} {node["status"]}'
                    if is_single_node:
                        lines.append(f'| {node["hostname"]} | {status_str} | {ids_str} |')
                    elif is_abap:
                        lines.append(
                            f'| {node["hostname"]} | {node["comp_type"]} | {status_str} | {ids_str} |'
                        )
                    else:
                        lines.append(
                            f'| {node["hostname"]} | {node["role"]} | {_emoji(node["status"])} {node["status"]} | {node["cluster"]} | {ids_str} |'
                        )
                lines.append('')
        except Exception as e:
            lines.append(f'> ⚠️ Could not list components: {e}')
            lines.append('')

        # Shared findings list for consolidated Recommended Actions
        findings: List[Dict[str, str]] = []

        # Configuration checks
        if include_config_checks:
            _append_config_checks(
                client,
                app_id,
                lines,
                include_subchecks,
                include_rule_results,
                findings=findings,
            )

        # HANA log backup status — only for HANA applications
        is_hana = app_type == 'HANA'
        if include_log_backup_status and ssm_client and is_hana:
            _append_log_backup_status(
                ssm_client, app_id, ec2_instance_ids, lines, findings=findings
            )

        # AWS Backup status — only for HANA applications
        if include_aws_backup_status and backup_client and is_hana:
            _append_aws_backup_status(
                backup_client, app_id, ec2_instance_ids, lines, findings=findings
            )

        # CloudWatch metrics
        if include_cloudwatch_metrics and cloudwatch_client:
            _append_cloudwatch_metrics(
                cloudwatch_client, ec2_instance_ids, lines, findings=findings
            )

        # Filesystem usage via SSM
        if include_log_backup_status and ssm_client and ec2_instance_ids:
            _append_filesystem_usage(ssm_client, ec2_instance_ids, lines, findings=findings)

        # Consolidated Recommended Actions — at the very end
        if findings:
            failures = [f for f in findings if f.get('severity') == 'failure']
            warnings = [f for f in findings if f.get('severity') == 'warning']

            lines.append('### Recommended Actions')
            lines.append('')

            if failures:
                lines.append('#### Failures (Action Required)')
                lines.append('')
                for i, f in enumerate(failures, 1):
                    actual = f.get('actual', '')
                    expected = f.get('expected', '')
                    vals = ''
                    if actual and expected:
                        vals = f' (current: {actual}, recommended: {expected})'
                    elif actual:
                        vals = f' (current: {actual})'
                    section = f.get('section', '')
                    section_tag = f' [{section}]' if section else ''
                    lines.append(f'{i}. 🔴 **{f["rule"]}**{vals}{section_tag}')
                    if f.get('message'):
                        lines.append(f'   - {f["message"]}')
                    lines.append('')

            if warnings:
                lines.append('#### Warnings (Review Recommended)')
                lines.append('')
                for i, f in enumerate(warnings, 1):
                    actual = f.get('actual', '')
                    expected = f.get('expected', '')
                    vals = ''
                    if actual and expected:
                        vals = f' (current: {actual}, recommended: {expected})'
                    elif actual:
                        vals = f' (current: {actual})'
                    section = f.get('section', '')
                    section_tag = f' [{section}]' if section else ''
                    lines.append(f'{i}. ⚠️ **{f["rule"]}**{vals}{section_tag}')
                    if f.get('message'):
                        lines.append(f'   - {f["message"]}')
                    lines.append('')

            lines.append('')

    except Exception as e:
        lines.append(f'## ⚠️ Application: `{app_id}`')
        lines.append('')
        lines.append(f'> Error retrieving application details: {e}')
        lines.append('')
        app_status = 'ERROR'
        discovery_status = 'ERROR'

    return '\n'.join(lines), app_status, discovery_status


def _append_config_checks(
    client,
    app_id: str,
    lines: List[str],
    include_subchecks: bool,
    include_rule_results: bool,
    findings: List[Dict[str, str]] | None = None,
) -> None:
    """Append configuration check results to the report.

    Args:
        client: SSM for SAP boto3 client.
        app_id: The application ID to query config checks for.
        lines: List of markdown lines to append report content to.
        include_subchecks: Whether to include sub-check details.
        include_rule_results: Whether to include rule-level results within sub-checks.
        findings: Optional shared list to collect FAILED/WARNING findings for
                  the consolidated Recommended Actions section at report end.
    """
    if findings is None:
        findings = []
    try:
        response = client.list_configuration_check_operations(
            ApplicationId=app_id,
            ListMode='LATEST_PER_CHECK',
        )
        check_ops = response.get('ConfigurationCheckOperations', [])
        if not check_ops:
            lines.append('### Configuration Checks')
            lines.append('')
            lines.append('> No configuration check results found.')
            lines.append('')
            return

        # Map internal check IDs to human-readable names
        _check_names = {
            'SAP_CHECK_01': 'EC2 Instance Type Selection',
            'SAP_CHECK_02': 'Storage Configuration',
            'SAP_CHECK_03': 'Pacemaker HA Configuration',
        }

        lines.append('### Configuration Checks')
        lines.append('')

        # Health overview summary table — what went well + what needs attention
        lines.append('| Check Category | ✅ Passed | 🔴 Failed | ⚠️ Warning | 🔵 Info |')
        lines.append('|----------------|-----------|-----------|------------|---------|')
        for check_op in check_ops:
            cid = check_op.get('ConfigurationCheckId', 'UNKNOWN')
            cname = _check_names.get(cid, cid)
            counts = check_op.get('RuleStatusCounts', {})
            passed = counts.get('Passed', 0)
            failed = counts.get('Failed', 0)
            warning = counts.get('Warning', 0)
            info = counts.get('Info', 0)
            lines.append(f'| {cname} | {passed} | {failed} | {warning} | {info} |')
        lines.append('')

        for check_op in check_ops:
            check_id = check_op.get('ConfigurationCheckId', 'UNKNOWN')
            check_name = _check_names.get(check_id, check_id)

            # Real API uses 'Id', fall back to 'OperationId' for compatibility
            operation_id = check_op.get('Id') or check_op.get('OperationId', '')

            # Fallback: if operation ID is missing, try list_operations
            if not operation_id and include_subchecks:
                try:
                    ops_resp = client.list_operations(
                        ApplicationId=app_id,
                        MaxResults=10,
                    )
                    for op in ops_resp.get('Operations', []):
                        if op.get('Type') == 'CONFIGURATION_CHECK' and op.get('Id'):
                            operation_id = op['Id']
                            break
                except Exception:
                    pass

            last_updated = format_datetime(
                check_op.get('EndTime') or check_op.get('LastUpdatedTime')
            )

            lines.append(f'#### {check_name}')
            lines.append('')
            lines.append(f'*Last evaluated: {last_updated}*')
            lines.append('')

            # Go straight to sub-checks — no summary table
            if include_subchecks and operation_id:
                try:
                    sc_response = client.list_sub_check_results(OperationId=operation_id)
                    subchecks = sc_response.get('SubCheckResults', [])
                    if subchecks:
                        for sc in subchecks:
                            sc_name = sc.get('Name', 'UNKNOWN')
                            sc_desc = sc.get('Description', '-')
                            sc_id = sc.get('Id', '')

                            lines.append(f'**{sc_name}**')
                            lines.append(f'> {sc_desc}')
                            lines.append('')

                            # Rule results — this is the actual useful content
                            if include_rule_results and sc_id:
                                try:
                                    rr_response = client.list_sub_check_rule_results(
                                        SubCheckResultId=sc_id
                                    )
                                    rules = rr_response.get('RuleResults', [])
                                    if rules:
                                        for rule in rules:
                                            rule_name = rule.get(
                                                'Description', rule.get('Id', 'UNKNOWN')
                                            )
                                            rule_status = rule.get('Status', 'UNKNOWN')
                                            rule_msg = rule.get('Message', '')
                                            metadata = rule.get('Metadata', {})
                                            detail = f' — {rule_msg}' if rule_msg else ''
                                            lines.append(
                                                f'- {_emoji(rule_status)} **{rule_name}**: {rule_status}{detail}'
                                            )

                                            # Collect for consolidated remediation
                                            if rule_status in ('FAILED', 'WARNING'):
                                                severity = (
                                                    'failure'
                                                    if rule_status == 'FAILED'
                                                    else 'warning'
                                                )
                                                finding = {
                                                    'severity': severity,
                                                    'section': check_name,
                                                    'rule': rule_name,
                                                    'message': rule_msg,
                                                    'actual': metadata.get('ActualValue', ''),
                                                    'expected': metadata.get('ExpectedValue', ''),
                                                }
                                                # Deduplicate (same rule on both nodes)
                                                key = f'{rule_name}|{rule_msg}'
                                                if not any(f.get('_key') == key for f in findings):
                                                    finding['_key'] = key
                                                    findings.append(finding)
                                        lines.append('')
                                except Exception:
                                    pass
                except Exception:
                    pass

        lines.append('')
    except Exception as e:
        lines.append('### Configuration Checks')
        lines.append('')
        lines.append(f'> ⚠️ Could not retrieve config checks: {e}')
        lines.append('')


def _append_log_backup_status(
    ssm_client,
    app_id: str,
    ec2_instance_ids: List[str],
    lines: List[str],
    findings: List[Dict[str, str]] | None = None,
) -> None:
    """Append HANA log backup status to the report.

    Uses SSM command history to check for AWSSystemsManagerSAP-HanaLogBackupStatusCheck
    results. Falls back to SSM agent status if no command history is available.
    """
    lines.append('### HANA Log Backup Status')
    lines.append('')

    if not ec2_instance_ids:
        lines.append('> No EC2 instances found to check log backup status.')
        lines.append('')
        return

    try:
        lines.append('| Instance | SSM Agent | Log Backup Check |')
        lines.append('|----------|-----------|------------------|')

        for instance_id in ec2_instance_ids:
            agent_info = 'Unknown'
            backup_info = 'N/A'
            try:
                response = ssm_client.describe_instance_information(
                    Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
                )
                instances = response.get('InstanceInformationList', [])
                if instances:
                    ping_status = instances[0].get('PingStatus', 'UNKNOWN')
                    agent_version = instances[0].get('AgentVersion', 'N/A')
                    agent_info = f'{_emoji("ACTIVATED" if ping_status == "Online" else "FAILED")} {ping_status} (v{agent_version})'

                    # Try to get HANA log backup status via SSM command history
                    if ping_status == 'Online':
                        try:
                            # Use paginator to find commands (same approach as summary tool)
                            all_cmds = []
                            paginator = ssm_client.get_paginator('list_commands')
                            for page in paginator.paginate(
                                Filters=[
                                    {
                                        'key': 'DocumentName',
                                        'value': 'AWSSystemsManagerSAP-HanaLogBackupStatusCheck',
                                    }
                                ],
                                PaginationConfig={'MaxItems': 50},
                            ):
                                all_cmds.extend(page.get('Commands', []))

                            # Find commands targeting this instance
                            matching = [
                                c for c in all_cmds if instance_id in c.get('InstanceIds', [])
                            ]
                            if matching:
                                cmd_id = matching[0].get('CommandId')
                                if cmd_id:
                                    # Use list_command_invocations with Details=True
                                    # to get the PerformAction step output
                                    try:
                                        inv_detail = ssm_client.list_command_invocations(
                                            CommandId=cmd_id,
                                            InstanceId=instance_id,
                                            Details=True,
                                        )
                                        for inv in inv_detail.get('CommandInvocations', []):
                                            cmd_status = inv.get('Status', 'UNKNOWN')
                                            plugins = inv.get('CommandPlugins', [])
                                            for plugin in plugins:
                                                if plugin.get('Name') == 'PerformAction':
                                                    output = plugin.get('Output', '')
                                                    if output and cmd_status == 'Success':
                                                        # Extract JSON payload
                                                        json_start = output.find(
                                                            '{"executionStatus"'
                                                        )
                                                        if json_start >= 0:
                                                            backup_info = f'🟢 {output[json_start : json_start + 200]}'
                                                        else:
                                                            backup_info = '🟢 Success'
                                                    elif cmd_status == 'Failed':
                                                        backup_info = '🔴 Failed'
                                                    else:
                                                        backup_info = f'⚪ {cmd_status}'
                                                    break
                                    except Exception:
                                        backup_info = 'Unable to query invocation'
                            else:
                                backup_info = 'No check history'
                        except Exception:
                            backup_info = 'Unable to query'
                else:
                    agent_info = '⚪ Not managed by SSM'
            except Exception:
                agent_info = '⚠️ Unable to query'

            lines.append(f'| `{instance_id}` | {agent_info} | {backup_info} |')

            # Collect findings for remediation
            if findings is not None:
                if backup_info == 'No check history':
                    findings.append(
                        {
                            'severity': 'warning',
                            'section': 'HANA Log Backup',
                            'rule': f'Log backup check not available for {instance_id}',
                            'message': 'No log backup check history found. Ensure AWSSystemsManagerSAP-HanaLogBackupStatusCheck is configured.',
                            'actual': '',
                            'expected': '',
                            '_key': f'log_backup_no_history|{instance_id}',
                        }
                    )
                elif '🔴' in backup_info:
                    findings.append(
                        {
                            'severity': 'failure',
                            'section': 'HANA Log Backup',
                            'rule': f'Log backup check failed for {instance_id}',
                            'message': 'HANA log backup check returned a failure status.',
                            'actual': '',
                            'expected': '',
                            '_key': f'log_backup_failed|{instance_id}',
                        }
                    )

        lines.append('')
    except Exception as e:
        lines.append(f'> ⚠️ Could not check log backup status: {e}')
        lines.append('')


def _append_aws_backup_status(
    backup_client,
    app_id: str,
    ec2_instance_ids: List[str],
    lines: List[str],
    findings: List[Dict[str, str]] | None = None,
) -> None:
    """Append AWS Backup status for SAP HANA resources.

    Includes actual failure reasons from the AWS Backup API (StatusMessage)
    for any FAILED, EXPIRED, or ABORTED backup jobs.
    """
    lines.append('### AWS Backup Status')
    lines.append('')

    if not ec2_instance_ids:
        lines.append('> No EC2 instances found to check backup status.')
        lines.append('')
        return

    try:
        lines.append('| Instance | Last Backup | Status | Type |')
        lines.append('|----------|-------------|--------|------|')

        # Collect failed job details for the failure reason section
        failed_jobs: List[Dict[str, Any]] = []

        # Try SAP HANA specific backup jobs first
        sap_jobs_found = False
        try:
            jobs_resp = backup_client.list_backup_jobs(
                ByResourceType='SAP HANA on Amazon EC2',
                MaxResults=50,
            )
            sap_jobs = jobs_resp.get('BackupJobs', [])
            if sap_jobs:
                # SAP HANA backup ARNs use app_id, not instance IDs
                app_jobs = [j for j in sap_jobs if app_id in j.get('ResourceArn', '')]
                if app_jobs:
                    sap_jobs_found = True
                    # Show all recent jobs grouped by state to surface EXPIRED/FAILED
                    seen_states = set()
                    for job in app_jobs:
                        job_status = job.get('State', 'UNKNOWN')
                        if job_status in seen_states:
                            continue
                        seen_states.add(job_status)
                        completion = format_datetime(
                            job.get('CompletionDate') or job.get('CreationDate')
                        )
                        backup_type = job.get('BackupType', 'SAP HANA')
                        lines.append(
                            f'| `{app_id}` | {completion} | {_emoji(job_status)} {job_status} | {backup_type} |'
                        )
                        # Collect failed/expired/aborted jobs with their failure reason
                        if job_status in ('FAILED', 'EXPIRED', 'ABORTED'):
                            failure_reason = job.get('StatusMessage') or job.get('MessageCategory')
                            # If list_backup_jobs didn't return StatusMessage,
                            # call describe_backup_job to get the detailed failure reason
                            job_id = job.get('BackupJobId', '')
                            if not failure_reason and job_id:
                                try:
                                    detail_resp = backup_client.describe_backup_job(
                                        BackupJobId=job_id
                                    )
                                    failure_reason = detail_resp.get(
                                        'StatusMessage'
                                    ) or detail_resp.get('MessageCategory')
                                except Exception:
                                    pass
                            failed_jobs.append(
                                {
                                    'instance': app_id,
                                    'status': job_status,
                                    'time': completion,
                                    'type': backup_type,
                                    'reason': failure_reason,
                                    'job_id': job_id or 'N/A',
                                }
                            )
        except Exception:
            pass

        # Fallback: query by EC2 instance resource ARN
        if not sap_jobs_found:
            for instance_id in ec2_instance_ids:
                resource_arn = f'arn:aws:ec2:*:*:instance/{instance_id}'
                try:
                    jobs_response = backup_client.list_backup_jobs(
                        ByResourceArn=resource_arn,
                        MaxResults=1,
                    )
                    jobs = jobs_response.get('BackupJobs', [])
                    if jobs:
                        job = jobs[0]
                        job_status = job.get('State', 'UNKNOWN')
                        completion = format_datetime(job.get('CompletionDate'))
                        lines.append(
                            f'| `{instance_id}` | {completion} | {_emoji(job_status)} {job_status} | EC2 |'
                        )
                        if job_status in ('FAILED', 'EXPIRED', 'ABORTED'):
                            failure_reason = job.get('StatusMessage') or job.get('MessageCategory')
                            job_id = job.get('BackupJobId', '')
                            if not failure_reason and job_id:
                                try:
                                    detail_resp = backup_client.describe_backup_job(
                                        BackupJobId=job_id
                                    )
                                    failure_reason = detail_resp.get(
                                        'StatusMessage'
                                    ) or detail_resp.get('MessageCategory')
                                except Exception:
                                    pass
                            failed_jobs.append(
                                {
                                    'instance': instance_id,
                                    'status': job_status,
                                    'time': completion,
                                    'type': 'EC2',
                                    'reason': failure_reason,
                                    'job_id': job_id or 'N/A',
                                }
                            )
                    else:
                        lines.append(f'| `{instance_id}` | No backups found | ⚪ N/A | - |')
                except Exception:
                    lines.append(f'| `{instance_id}` | Unable to query | ⚠️ Error | - |')

        lines.append('')

        # Display failure reasons from the AWS Backup API
        if failed_jobs:
            lines.append('#### Backup Failure Details')
            lines.append('')
            for fj in failed_jobs:
                reason = (
                    fj['reason']
                    if fj['reason']
                    else 'No failure reason returned by AWS Backup API'
                )
                lines.append(f'- 🔴 **{fj["status"]}** at {fj["time"]} (Job ID: `{fj["job_id"]}`)')
                lines.append(f'  - Failure Reason: {reason}')
                lines.append('')

            # Collect findings for consolidated remediation
            if findings is not None:
                for fj in failed_jobs:
                    reason = (
                        fj['reason']
                        if fj['reason']
                        else 'No failure reason returned by AWS Backup API'
                    )
                    findings.append(
                        {
                            'severity': 'failure',
                            'section': 'AWS Backup',
                            'rule': f'Backup {fj["status"].lower()} for {fj["instance"]}',
                            'message': f'Job {fj["job_id"]} at {fj["time"]}: {reason}',
                            'actual': fj['status'],
                            'expected': 'COMPLETED',
                            '_key': f'backup_{fj["status"].lower()}|{fj["instance"]}|{fj["job_id"]}',
                        }
                    )

    except Exception as e:
        lines.append(f'> ⚠️ Could not check AWS Backup status: {e}')
        lines.append('')


def _append_cloudwatch_metrics(
    cloudwatch_client,
    ec2_instance_ids: List[str],
    lines: List[str],
    findings: List[Dict[str, str]] | None = None,
) -> None:
    """Append CloudWatch metrics for EC2 instances running SAP.

    Includes both AWS/EC2 metrics (CPU, status checks) and CWAgent metrics
    (memory, disk, network) when available.
    """
    lines.append('### CloudWatch Metrics (Last 1 Hour)')
    lines.append('')

    if not ec2_instance_ids:
        lines.append('> No EC2 instances found to check metrics.')
        lines.append('')
        return

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=1)

    # Collect per-instance data first, then render only columns with data
    instance_data = []

    for instance_id in ec2_instance_ids:
        cpu_avg = None
        cpu_max = None
        status_check = '-'
        mem_pct = None
        disk_pct = None

        try:
            # CPU Utilization
            cpu_response = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=now,
                Period=3600,
                Statistics=['Average', 'Maximum'],
            )
            datapoints = cpu_response.get('Datapoints', [])
            if datapoints:
                dp = datapoints[0]
                cpu_avg = f'{dp.get("Average", 0):.1f}'
                cpu_max = f'{dp.get("Maximum", 0):.1f}'
        except Exception:
            pass

        try:
            # Status Check Failed
            status_response = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='StatusCheckFailed',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=now,
                Period=3600,
                Statistics=['Maximum'],
            )
            datapoints = status_response.get('Datapoints', [])
            if datapoints:
                failed = datapoints[0].get('Maximum', 0)
                status_check = '🟢 OK' if failed == 0 else '🔴 FAILED'
            else:
                status_check = '⚪ No data'
        except Exception:
            status_check = '⚠️ Error'

        # CWAgent metrics
        try:
            mem_dims = _discover_cwagent_dimensions(
                cloudwatch_client,
                'mem_used_percent',
                instance_id,
            )
            if mem_dims:
                mem_resp = cloudwatch_client.get_metric_statistics(
                    Namespace='CWAgent',
                    MetricName='mem_used_percent',
                    Dimensions=mem_dims,
                    StartTime=start_time,
                    EndTime=now,
                    Period=3600,
                    Statistics=['Average'],
                )
                dps = mem_resp.get('Datapoints', [])
                if dps:
                    mem_pct = f'{dps[0].get("Average", 0):.1f}'
        except Exception:
            pass
        try:
            disk_dim_sets = _discover_cwagent_disk_dimensions(
                cloudwatch_client,
                instance_id,
            )
            for dim_set in disk_dim_sets:
                dim_map = {d['Name']: d['Value'] for d in dim_set}
                if dim_map.get('path') == '/':
                    disk_resp = cloudwatch_client.get_metric_statistics(
                        Namespace='CWAgent',
                        MetricName='disk_used_percent',
                        Dimensions=dim_set,
                        StartTime=start_time,
                        EndTime=now,
                        Period=3600,
                        Statistics=['Average'],
                    )
                    dps = disk_resp.get('Datapoints', [])
                    if dps:
                        disk_pct = f'{dps[0].get("Average", 0):.1f}'
                    break
        except Exception:
            pass

        instance_data.append(
            {
                'id': instance_id,
                'cpu_avg': cpu_avg,
                'cpu_max': cpu_max,
                'mem_pct': mem_pct,
                'disk_pct': disk_pct,
                'status_check': status_check,
            }
        )

    # Determine which columns have data across all instances
    has_cpu = any(d['cpu_avg'] is not None for d in instance_data)
    has_mem = any(d['mem_pct'] is not None for d in instance_data)
    has_disk = any(d['disk_pct'] is not None for d in instance_data)

    # Build dynamic table header and rows — only include columns with data
    header_parts = ['Instance']
    separator_parts = ['----------']
    if has_cpu:
        header_parts.extend(['CPU Avg (%)', 'CPU Max (%)'])
        separator_parts.extend(['-------------', '-------------'])
    if has_mem:
        header_parts.append('Memory (%)')
        separator_parts.append('------------')
    if has_disk:
        header_parts.append('Disk (%)')
        separator_parts.append('----------')
    header_parts.append('Status Check')
    separator_parts.append('--------------')

    lines.append('| ' + ' | '.join(header_parts) + ' |')
    lines.append('| ' + ' | '.join(separator_parts) + ' |')

    for d in instance_data:
        row_parts = [f'`{d["id"]}`']
        if has_cpu:
            row_parts.append(d['cpu_avg'] or '-')
            row_parts.append(d['cpu_max'] or '-')
        if has_mem:
            row_parts.append(d['mem_pct'] or '-')
        if has_disk:
            row_parts.append(d['disk_pct'] or '-')
        row_parts.append(d['status_check'])
        lines.append('| ' + ' | '.join(row_parts) + ' |')

        # Collect findings for remediation
        if findings is not None:
            try:
                mem_val = float(d['mem_pct']) if d['mem_pct'] else 0
                if mem_val > 90:
                    findings.append(
                        {
                            'severity': 'failure',
                            'section': 'CloudWatch Metrics',
                            'rule': f'Memory usage critical on {d["id"]}',
                            'message': f'Memory at {d["mem_pct"]}% — exceeds 90% threshold',
                            'actual': f'{d["mem_pct"]}%',
                            'expected': '< 90%',
                            '_key': f'cw_mem_critical|{d["id"]}',
                        }
                    )
                elif mem_val > 80:
                    findings.append(
                        {
                            'severity': 'warning',
                            'section': 'CloudWatch Metrics',
                            'rule': f'Memory usage high on {d["id"]}',
                            'message': f'Memory at {d["mem_pct"]}% — approaching critical threshold',
                            'actual': f'{d["mem_pct"]}%',
                            'expected': '< 80%',
                            '_key': f'cw_mem_high|{d["id"]}',
                        }
                    )
            except (ValueError, TypeError):
                pass
            if '🔴' in d['status_check']:
                findings.append(
                    {
                        'severity': 'failure',
                        'section': 'CloudWatch Metrics',
                        'rule': f'EC2 status check failed on {d["id"]}',
                        'message': 'Instance or system status check is failing',
                        'actual': 'FAILED',
                        'expected': 'OK',
                        '_key': f'cw_status_failed|{d["id"]}',
                    }
                )

    # Detailed disk usage per SAP-relevant path (separate table)
    has_disk_detail = False
    disk_lines = []
    disk_lines.append('')
    disk_lines.append('#### Disk Usage by Path (CWAgent)')
    disk_lines.append('')
    disk_lines.append('| Instance | Path | Used (%) | Device |')
    disk_lines.append('|----------|------|----------|--------|')
    for instance_id in ec2_instance_ids:
        try:
            disk_dim_sets = _discover_cwagent_disk_dimensions(
                cloudwatch_client,
                instance_id,
            )
            for dim_set in disk_dim_sets:
                dim_map = {d['Name']: d['Value'] for d in dim_set}
                path = dim_map.get('path', '?')
                device = dim_map.get('device', '-')
                try:
                    disk_resp = cloudwatch_client.get_metric_statistics(
                        Namespace='CWAgent',
                        MetricName='disk_used_percent',
                        Dimensions=dim_set,
                        StartTime=start_time,
                        EndTime=now,
                        Period=3600,
                        Statistics=['Average'],
                    )
                    dps = disk_resp.get('Datapoints', [])
                    if dps:
                        pct = f'{dps[0].get("Average", 0):.1f}'
                        disk_lines.append(f'| `{instance_id}` | `{path}` | {pct} | `{device}` |')
                        has_disk_detail = True
                except Exception:
                    pass
        except Exception:
            pass
    disk_lines.append('')

    if has_disk_detail:
        lines.extend(disk_lines)

    # Network metrics (separate table for clarity)
    has_network = False
    net_lines = []
    net_lines.append('')
    net_lines.append('#### Network I/O (CWAgent)')
    net_lines.append('')
    net_lines.append('| Instance | Bytes In | Bytes Out |')
    net_lines.append('|----------|----------|-----------|')
    for instance_id in ec2_instance_ids:
        net_in = '-'
        net_out = '-'
        try:
            recv_dims = _discover_cwagent_dimensions(
                cloudwatch_client,
                'net_bytes_recv',
                instance_id,
            )
            if recv_dims:
                resp = cloudwatch_client.get_metric_statistics(
                    Namespace='CWAgent',
                    MetricName='net_bytes_recv',
                    Dimensions=recv_dims,
                    StartTime=start_time,
                    EndTime=now,
                    Period=3600,
                    Statistics=['Sum'],
                )
                dps = resp.get('Datapoints', [])
                if dps:
                    val = dps[0].get('Sum', 0)
                    net_in = _format_bytes(val)
                    has_network = True
        except Exception:
            pass
        try:
            sent_dims = _discover_cwagent_dimensions(
                cloudwatch_client,
                'net_bytes_sent',
                instance_id,
            )
            if sent_dims:
                resp = cloudwatch_client.get_metric_statistics(
                    Namespace='CWAgent',
                    MetricName='net_bytes_sent',
                    Dimensions=sent_dims,
                    StartTime=start_time,
                    EndTime=now,
                    Period=3600,
                    Statistics=['Sum'],
                )
                dps = resp.get('Datapoints', [])
                if dps:
                    val = dps[0].get('Sum', 0)
                    net_out = _format_bytes(val)
                    has_network = True
        except Exception:
            pass
        net_lines.append(f'| `{instance_id}` | {net_in} | {net_out} |')
    net_lines.append('')

    if has_network:
        lines.extend(net_lines)

    lines.append('')


def _append_filesystem_usage(
    ssm_client,
    ec2_instance_ids: List[str],
    lines: List[str],
    findings: List[Dict[str, str]] | None = None,
) -> None:
    """Append filesystem usage information for SAP-relevant paths.

    First attempts to run `df -h` via SSM RunShellScript on each instance.
    Falls back to looking at recent SSM command history if send_command fails.
    """
    lines.append('### Filesystem Usage')
    lines.append('')

    if not ec2_instance_ids:
        lines.append('> No EC2 instances found to check filesystem usage.')
        lines.append('')
        return

    df_command = 'df -h / /usr/sap /hana/data /hana/log /hana/shared /backup 2>/dev/null || df -h / /usr/sap 2>/dev/null || df -h'
    found_any = False

    for instance_id in ec2_instance_ids:
        output = None
        # Try running df -h via SSM
        try:
            output = _run_ssm_command_sync(ssm_client, instance_id, df_command)
        except Exception:
            pass

        # Fallback: check command history for recent df results
        if not output:
            try:
                cmd_resp = ssm_client.list_commands(
                    InstanceId=instance_id,
                    Filters=[{'key': 'DocumentName', 'value': 'AWS-RunShellScript'}],
                    MaxResults=10,
                )
                for cmd in cmd_resp.get('Commands', []):
                    params = cmd.get('Parameters', {})
                    cmds = params.get('commands', [])
                    if any('df' in c for c in cmds):
                        cmd_id = cmd.get('CommandId')
                        if cmd_id:
                            inv_resp = ssm_client.get_command_invocation(
                                CommandId=cmd_id,
                                InstanceId=instance_id,
                            )
                            if inv_resp.get('Status') == 'Success':
                                output = inv_resp.get('StandardOutputContent', '')
                                if output:
                                    break
            except Exception:
                pass

        if output and output.strip():
            lines.append(f'**`{instance_id}`:**')
            lines.append('')
            lines.append('```')
            lines.append(output.strip()[:1000])
            lines.append('```')
            lines.append('')
            found_any = True

            # Collect findings for filesystems at >80% usage
            if findings is not None:
                for line in output.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 5 and '%' in parts[-2]:
                        try:
                            pct = int(parts[-2].replace('%', ''))
                            mount = parts[-1]
                            if pct >= 95:
                                findings.append(
                                    {
                                        'severity': 'failure',
                                        'section': 'Filesystem Usage',
                                        'rule': f'Filesystem {mount} critically full on {instance_id}',
                                        'message': f'{mount} is at {pct}% — immediate action required',
                                        'actual': f'{pct}%',
                                        'expected': '< 80%',
                                        '_key': f'fs_critical|{instance_id}|{mount}',
                                    }
                                )
                            elif pct >= 80:
                                findings.append(
                                    {
                                        'severity': 'warning',
                                        'section': 'Filesystem Usage',
                                        'rule': f'Filesystem {mount} high usage on {instance_id}',
                                        'message': f'{mount} is at {pct}% — review and plan cleanup',
                                        'actual': f'{pct}%',
                                        'expected': '< 80%',
                                        '_key': f'fs_high|{instance_id}|{mount}',
                                    }
                                )
                        except (ValueError, IndexError):
                            pass

    if not found_any:
        lines.append(
            '> No filesystem usage data available. Ensure SSM agent is running on the instances.'
        )
        lines.append('')


def _build_overall_summary(
    total_apps: int,
    app_status_counts: Dict[str, int],
    discovery_status_counts: Dict[str, int],
) -> str:
    """Build the overall summary section of the report."""
    lines = []
    lines.append('### Overall Summary')
    lines.append('')

    # Quick health verdict — don't show raw status codes
    healthy = app_status_counts.get('ACTIVATED', 0)
    if healthy == total_apps and total_apps > 0:
        lines.append(f'> ✅ All {total_apps} application(s) are running and healthy.')
    elif total_apps > 0:
        unhealthy = total_apps - healthy
        lines.append(f'> ⚠️ {unhealthy} of {total_apps} application(s) require attention.')
        # Only show breakdown when there are problems
        for status, count in sorted(app_status_counts.items()):
            if status != 'ACTIVATED':
                lines.append(f'>   - {count} {status.lower()}')
    lines.append('')

    return '\n'.join(lines)


class SSMSAPHealthTools:
    """SSM for SAP health summary and report tools."""

    def __init__(self):
        """Initialize the health tools."""
        pass

    def register(self, mcp):
        """Register all health tools with the MCP server."""
        mcp.tool(name='get_sap_health_summary')(self.get_sap_health_summary)
        mcp.tool(name='generate_health_report')(self.generate_health_report)

    async def get_sap_health_summary(
        self,
        ctx: Context,
        application_id: Annotated[
            str | None,
            Field(
                description='Optional specific application ID. If not provided, checks all applications.'
            ),
        ] = None,
        include_config_checks: Annotated[
            bool,
            Field(description='Include configuration check results. Default: True.'),
        ] = True,
        include_subchecks: Annotated[
            bool,
            Field(description='Include sub-check details within config checks. Default: True.'),
        ] = True,
        include_rule_results: Annotated[
            bool,
            Field(description='Include rule-level results within sub-checks. Default: True.'),
        ] = True,
        include_log_backup_status: Annotated[
            bool,
            Field(description='Include HANA log backup status via SSM. Default: True.'),
        ] = True,
        include_aws_backup_status: Annotated[
            bool,
            Field(description='Include AWS Backup status for SAP HANA. Default: True.'),
        ] = True,
        include_cloudwatch_metrics: Annotated[
            bool,
            Field(description='Include CloudWatch metrics for EC2 instances. Default: True.'),
        ] = True,
        auto_trigger_config_checks: Annotated[
            bool,
            Field(
                description='Automatically trigger config checks if no recent results exist. Default: True.'
            ),
        ] = True,
        config_check_max_age_hours: Annotated[
            int,
            Field(
                description='Max age in hours for config check results before auto-triggering. Default: 24.'
            ),
        ] = 24,
        region: Annotated[
            str | None,
            Field(
                description='AWS region. Defaults to AWS_REGION environment variable or us-east-1.'
            ),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name. Falls back to AWS_PROFILE env var.'),
        ] = None,
    ) -> HealthSummaryResponse:
        """Get comprehensive health summary for SAP systems managed by SSM for SAP.

        Returns structured per-application health data including:
        - Application and discovery status
        - Component details with EC2 instance IDs
        - Configuration check results (auto-triggers checks if none recent)
        - HANA log backup status via SSM agent
        - AWS Backup status for SAP HANA instances
        - CloudWatch metrics (CPU, status checks) for EC2 instances
        - Overall health verdict

        Use generate_health_report for a detailed, downloadable Markdown report.

        Args:
            ctx: MCP context object.
            application_id: Optional specific application ID (checks all if not provided).
            include_config_checks: Whether to include configuration check results.
            include_subchecks: Whether to include subcheck details.
            include_rule_results: Whether to include rule-level results.
            include_log_backup_status: Whether to include HANA log backup status.
            include_aws_backup_status: Whether to include AWS Backup status.
            include_cloudwatch_metrics: Whether to include CloudWatch metrics.
            auto_trigger_config_checks: Whether to auto-trigger config checks if none recent.
            config_check_max_age_hours: Max age in hours before auto-triggering config checks.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            HealthSummaryResponse with per-application health entries and a summary.
        """
        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)

            ssm_client = None
            if include_log_backup_status:
                ssm_client = get_aws_client('ssm', region_name=region, profile_name=profile_name)

            backup_client = None
            if include_aws_backup_status:
                backup_client = get_aws_client(
                    'backup', region_name=region, profile_name=profile_name
                )

            cloudwatch_client = None
            if include_cloudwatch_metrics:
                cloudwatch_client = get_aws_client(
                    'cloudwatch', region_name=region, profile_name=profile_name
                )

            if application_id:
                app_ids = [application_id]
            else:
                app_ids = _get_all_app_ids(client)

            if not app_ids:
                return HealthSummaryResponse(
                    status='success',
                    message='No SAP applications found in this region.',
                    application_count=0,
                    healthy_count=0,
                    unhealthy_count=0,
                    summary='# SAP Health Summary\n\n> No SAP applications found.',
                )

            entries: List[ApplicationHealthEntry] = []
            for app_id in app_ids:
                entry = await _get_app_summary(
                    client,
                    app_id,
                    ssm_client=ssm_client,
                    backup_client=backup_client,
                    cloudwatch_client=cloudwatch_client,
                    include_config_checks=include_config_checks,
                    include_subchecks=include_subchecks,
                    include_rule_results=include_rule_results,
                    include_log_backup_status=include_log_backup_status,
                    include_aws_backup_status=include_aws_backup_status,
                    include_cloudwatch_metrics=include_cloudwatch_metrics,
                    auto_trigger_config_checks=auto_trigger_config_checks,
                    config_check_max_age_hours=config_check_max_age_hours,
                )
                entries.append(entry)

            healthy = sum(1 for e in entries if e.status == 'ACTIVATED')
            unhealthy = len(entries) - healthy

            # Build markdown summary
            lines = []
            effective_region = region or Session().region_name or 'us-east-1'
            current_time = datetime.now(timezone.utc)
            lines.append('# SAP Health Summary')
            lines.append('')
            lines.append('| | |')
            lines.append('|---|---|')
            lines.append(f'| Region | `{effective_region}` |')
            lines.append(f'| Timestamp | {current_time.strftime("%Y-%m-%d %H:%M:%S UTC")} |')
            lines.append(f'| Applications | {len(entries)} |')
            lines.append(f'| Healthy | {healthy} |')
            lines.append(f'| Needs Attention | {unhealthy} |')
            lines.append('')

            lines.append('| Application | Type | Components |')
            lines.append('|-------------|------|------------|')
            for e in entries:
                lines.append(f'| `{e.application_id}` | {e.app_type} | {e.component_count} |')
            lines.append('')

            if healthy == len(entries) and len(entries) > 0:
                lines.append(f'> ✅ All {len(entries)} application(s) are running and healthy.')
            elif len(entries) > 0:
                lines.append(
                    f'> ⚠️ {unhealthy} of {len(entries)} application(s) require attention.'
                )
            lines.append('')

            return HealthSummaryResponse(
                status='success',
                message=f'Health summary generated for {len(entries)} application(s)',
                application_count=len(entries),
                healthy_count=healthy,
                unhealthy_count=unhealthy,
                applications=entries,
                summary='\n'.join(lines),
            )

        except Exception as e:
            logger.error(f'Error generating health summary: {e}')
            return HealthSummaryResponse(
                status='error',
                message=f'Error generating health summary: {str(e)}',
            )

    async def generate_health_report(
        self,
        ctx: Context,
        application_id: Annotated[
            str | None,
            Field(
                description='Optional specific application ID. If not provided, checks all applications.'
            ),
        ] = None,
        include_config_checks: Annotated[
            bool,
            Field(description='Include configuration check results. Default: True.'),
        ] = True,
        include_subchecks: Annotated[
            bool,
            Field(description='Include sub-check details within config checks. Default: True.'),
        ] = True,
        include_rule_results: Annotated[
            bool,
            Field(description='Include rule-level results within sub-checks. Default: True.'),
        ] = True,
        include_log_backup_status: Annotated[
            bool,
            Field(description='Include HANA log backup status via SSM. Default: True.'),
        ] = True,
        include_aws_backup_status: Annotated[
            bool,
            Field(description='Include AWS Backup status for SAP HANA. Default: True.'),
        ] = True,
        include_cloudwatch_metrics: Annotated[
            bool,
            Field(description='Include CloudWatch metrics for EC2 instances. Default: True.'),
        ] = True,
        region: Annotated[
            str | None,
            Field(
                description='AWS region. Defaults to AWS_REGION environment variable or us-east-1.'
            ),
        ] = None,
        profile_name: Annotated[
            str | None,
            Field(description='AWS CLI Profile Name. Falls back to AWS_PROFILE env var.'),
        ] = None,
    ) -> HealthReportResponse:
        """Generate a detailed, downloadable health report for SAP systems managed by SSM for SAP.

        Produces a comprehensive Markdown-formatted report covering:
        - Discovery status (SUCCESS | REGISTRATION_FAILED | REFRESH_FAILED | REGISTERING | DELETING)
        - Application status (ACTIVATED | STARTING | STOPPED | STOPPING | FAILED | REGISTERING | DELETING | UNKNOWN)
        - Component status with host details
        - Configuration checks with subchecks and rule results (optional)
        - HANA Log Backup status via SSM agent (optional)
        - AWS Backup status for SAP HANA (optional)
        - CloudWatch metrics for EC2 instances (optional)

        Args:
            ctx: MCP context object.
            application_id: Optional specific application ID (checks all if not provided).
            include_config_checks: Whether to include configuration check results.
            include_subchecks: Whether to include subcheck details.
            include_rule_results: Whether to include rule-level results.
            include_log_backup_status: Whether to include HANA log backup status.
            include_aws_backup_status: Whether to include AWS Backup status.
            include_cloudwatch_metrics: Whether to include CloudWatch metrics.
            region: AWS region.
            profile_name: AWS CLI profile name.

        Returns:
            HealthReportResponse with Markdown-formatted detailed health report.
        """
        current_time = datetime.now(timezone.utc)

        try:
            client = get_aws_client('ssm-sap', region_name=region, profile_name=profile_name)

            ssm_client = None
            if include_log_backup_status:
                ssm_client = get_aws_client('ssm', region_name=region, profile_name=profile_name)

            backup_client = None
            if include_aws_backup_status:
                backup_client = get_aws_client(
                    'backup', region_name=region, profile_name=profile_name
                )

            cloudwatch_client = None
            if include_cloudwatch_metrics:
                cloudwatch_client = get_aws_client(
                    'cloudwatch', region_name=region, profile_name=profile_name
                )

            if application_id:
                app_ids = [application_id]
            else:
                app_ids = _get_all_app_ids(client)

            if not app_ids:
                return HealthReportResponse(
                    status='success',
                    message='No SAP applications found in this region.',
                    report='# SAP Health Report\n\n> No SAP applications found.',
                    application_count=0,
                )

            effective_region = region or Session().region_name or 'us-east-1'

            report_lines = []
            report_lines.append('# SAP Systems Health Report')
            report_lines.append('')
            report_lines.append('| | |')
            report_lines.append('|---|---|')
            report_lines.append(f'| Region | `{effective_region}` |')
            report_lines.append(
                f'| Timestamp | {current_time.strftime("%Y-%m-%d %H:%M:%S UTC")} |'
            )
            report_lines.append(f'| Applications | {len(app_ids)} |')
            report_lines.append('')

            app_status_counts: Dict[str, int] = {}
            discovery_status_counts: Dict[str, int] = {}
            app_reports: List[str] = []

            for app_id in app_ids:
                app_report, app_status, disc_status = _check_app_health(
                    client,
                    ssm_client,
                    backup_client,
                    cloudwatch_client,
                    app_id,
                    include_config_checks,
                    include_subchecks,
                    include_rule_results,
                    include_log_backup_status,
                    include_aws_backup_status,
                    include_cloudwatch_metrics,
                )
                app_reports.append(app_report)
                app_status_counts[app_status] = app_status_counts.get(app_status, 0) + 1
                discovery_status_counts[disc_status] = (
                    discovery_status_counts.get(disc_status, 0) + 1
                )

            summary = _build_overall_summary(
                len(app_ids), app_status_counts, discovery_status_counts
            )
            report_lines.append(summary)

            report_lines.append('---')
            report_lines.append('')
            for app_report in app_reports:
                report_lines.append(app_report)
                report_lines.append('')
                report_lines.append('---')
                report_lines.append('')

            full_report = '\n'.join(report_lines)

            return HealthReportResponse(
                status='success',
                message=f'Health report generated for {len(app_ids)} application(s)',
                report=full_report,
                application_count=len(app_ids),
            )

        except Exception as e:
            logger.error(f'Error generating health report: {e}')
            return HealthReportResponse(
                status='error',
                message=f'Error generating health report: {str(e)}',
            )
