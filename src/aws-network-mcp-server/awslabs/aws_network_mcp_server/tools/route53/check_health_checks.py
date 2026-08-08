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

from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from datetime import datetime, timedelta, timezone
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


VALID_STATUS_FILTERS = ('healthy', 'unhealthy')
RATE_LIMIT_THRESHOLD = 20


def _extract_hc_config(hc: dict) -> dict:
    """Extract health check configuration into a structured dict."""
    config = hc.get('HealthCheckConfig', {})
    return {
        'ip_address': config.get('IPAddress'),
        'fqdn': config.get('FullyQualifiedDomainName'),
        'port': config.get('Port'),
        'resource_path': config.get('ResourcePath'),
        'request_interval': config.get('RequestInterval', 30),
        'failure_threshold': config.get('FailureThreshold', 3),
    }


def _is_calculated(hc: dict) -> bool:
    """Check if a health check is a calculated health check."""
    hc_type = hc.get('HealthCheckConfig', {}).get('Type', '')
    return hc_type == 'CALCULATED'


def _get_hc_type(hc: dict) -> str:
    """Get the health check type string."""
    return hc.get('HealthCheckConfig', {}).get('Type', 'UNKNOWN')


def _determine_status_from_checkers(status_response: dict) -> str:
    """Determine overall status from GetHealthCheckStatus response."""
    checkers = status_response.get('HealthCheckObservations', [])
    if not checkers:
        return 'unknown'
    for checker in checkers:
        sr = checker.get('StatusReport', {})
        status = sr.get('Status', '')
        if 'Failure' in status or 'Unhealthy' in status:
            return 'unhealthy'
    return 'healthy'


def _parse_checker_results(status_response: dict) -> List[dict]:
    """Parse per-region checker results from GetHealthCheckStatus."""
    results = []
    for obs in status_response.get('HealthCheckObservations', []):
        sr = obs.get('StatusReport', {})
        results.append(
            {
                'region': obs.get('Region', ''),
                'status': sr.get('Status', ''),
                'ip_address': obs.get('IPAddress', ''),
            }
        )
    return results


async def check_health_checks(
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    health_check_id: Annotated[
        Optional[str],
        Field(
            ...,
            description='Specific health check ID to inspect. When provided, returns detailed per-region checker status.',
        ),
    ] = None,
    status_filter: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter by health check status: "healthy" or "unhealthy". Returns all if not specified.',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Check Route 53 health check statuses and identify failing endpoints.

    Use this tool when:
    - Diagnosing DNS failover issues
    - Identifying unhealthy endpoints monitored by Route 53
    - Verifying health check configuration and status
    - Troubleshooting calculated health checks
    - Auditing health check inventory

    Common workflows:
    1. check_health_checks() → Identify failing HCs → Investigate endpoint issues
    2. check_health_checks(status_filter="unhealthy") → Focus on problems
    3. check_health_checks(health_check_id="...") → Detailed per-region checker status

    Notes:
    - GetHealthCheckStatus cannot be used for calculated health checks (uses CloudWatch instead)
    - GetHealthCheckStatus is rate-limited; only called when health_check_id is specified or count ≤ 20
    - CloudWatch Route 53 metrics are only available in us-east-1

    Returns:
        Dict containing:
        - health_checks: List of health check objects with config and status
        - count: Number of health checks found
        - status_retrieval_note: Explanation if status retrieval was limited
    """
    if status_filter is not None and status_filter not in VALID_STATUS_FILTERS:
        raise ToolError(
            f'Error checking health checks. Error: Invalid status_filter "{status_filter}". '
            f'Must be one of: {", ".join(VALID_STATUS_FILTERS)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    try:
        # Route 53 is global — no region needed
        r53_client = get_aws_client('route53', None, profile_name)
        # CloudWatch Route 53 metrics are ONLY in us-east-1
        cw_client = get_aws_client('cloudwatch', 'us-east-1', profile_name)

        status_note = None

        if health_check_id:
            return await _check_single_health_check(
                r53_client, cw_client, health_check_id, status_filter
            )

        # List all health checks
        paginator = r53_client.get_paginator('list_health_checks')
        all_hcs = []
        for page in paginator.paginate():
            all_hcs.extend(page.get('HealthChecks', []))

        calculated = [hc for hc in all_hcs if _is_calculated(hc)]
        non_calculated = [hc for hc in all_hcs if not _is_calculated(hc)]

        health_checks = []

        # Process non-calculated health checks
        fetch_status = len(non_calculated) <= RATE_LIMIT_THRESHOLD
        if not fetch_status:
            status_note = (
                f'Status retrieval skipped for non-calculated health checks '
                f'({len(non_calculated)} exceeds threshold of {RATE_LIMIT_THRESHOLD}). '
                f'Provide a specific health_check_id to get detailed status.'
            )

        for hc in non_calculated:
            hc_id = hc.get('Id', '')
            hc_info = {
                'id': hc_id,
                'type': _get_hc_type(hc),
                'config': _extract_hc_config(hc),
                'status': 'unknown',
                'checker_results': None,
            }
            if fetch_status:
                try:
                    status_resp = r53_client.get_health_check_status(HealthCheckId=hc_id)
                    hc_info['status'] = _determine_status_from_checkers(status_resp)
                    hc_info['checker_results'] = _parse_checker_results(status_resp)
                except Exception:
                    hc_info['status'] = 'unknown'
            health_checks.append(hc_info)

        # Process calculated health checks via CloudWatch
        for hc in calculated:
            hc_id = hc.get('Id', '')
            hc_info = {
                'id': hc_id,
                'type': _get_hc_type(hc),
                'config': _extract_hc_config(hc),
                'status': 'unknown',
                'checker_results': None,
            }
            hc_info['status'] = _get_cloudwatch_hc_status(cw_client, hc_id)
            health_checks.append(hc_info)

        # Apply status filter
        if status_filter:
            health_checks = [hc for hc in health_checks if hc['status'] == status_filter]

        return {
            'health_checks': health_checks,
            'count': len(health_checks),
            'status_retrieval_note': status_note,
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error checking health checks. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )


async def _check_single_health_check(
    r53_client: Any,
    cw_client: Any,
    health_check_id: str,
    status_filter: Optional[str],
) -> Dict[str, Any]:
    """Get detailed status for a single health check."""
    # Find the health check config
    paginator = r53_client.get_paginator('list_health_checks')
    target_hc = None
    for page in paginator.paginate():
        for hc in page.get('HealthChecks', []):
            if hc.get('Id') == health_check_id:
                target_hc = hc
                break
        if target_hc:
            break

    if not target_hc:
        raise ToolError(
            f'Error checking health checks. Error: Health check {health_check_id} not found. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    hc_info = {
        'id': health_check_id,
        'type': _get_hc_type(target_hc),
        'config': _extract_hc_config(target_hc),
        'status': 'unknown',
        'checker_results': None,
    }

    if _is_calculated(target_hc):
        hc_info['status'] = _get_cloudwatch_hc_status(cw_client, health_check_id)
    else:
        try:
            status_resp = r53_client.get_health_check_status(HealthCheckId=health_check_id)
            hc_info['status'] = _determine_status_from_checkers(status_resp)
            hc_info['checker_results'] = _parse_checker_results(status_resp)
        except Exception:
            hc_info['status'] = 'unknown'

    result_list = [hc_info]
    if status_filter and hc_info['status'] != status_filter:
        result_list = []

    return {
        'health_checks': result_list,
        'count': len(result_list),
        'status_retrieval_note': None,
    }


def _get_cloudwatch_hc_status(cw_client: Any, health_check_id: str) -> str:
    """Get health check status from CloudWatch for calculated health checks."""
    try:
        now = datetime.now(timezone.utc)
        response = cw_client.get_metric_statistics(
            Namespace='AWS/Route53',
            MetricName='HealthCheckStatus',
            Dimensions=[
                {'Name': 'HealthCheckId', 'Value': health_check_id},
            ],
            Period=60,
            Statistics=['Average'],
            StartTime=now - timedelta(minutes=5),
            EndTime=now,
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 'unknown'
        # Use the most recent datapoint
        latest = max(datapoints, key=lambda d: d.get('Timestamp', ''))
        avg = latest.get('Average', 0.0)
        return 'healthy' if avg >= 1.0 else 'unhealthy'
    except Exception:
        return 'unknown'
