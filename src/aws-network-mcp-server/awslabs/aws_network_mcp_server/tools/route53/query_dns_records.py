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
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


VALID_RECORD_TYPES = (
    'A',
    'AAAA',
    'CNAME',
    'MX',
    'TXT',
    'SRV',
    'NS',
    'SOA',
    'PTR',
    'CAA',
    'NAPTR',
    'SPF',
)


def _determine_routing_policy(record: dict) -> str:
    """Determine the routing policy from record fields."""
    if 'Weight' in record:
        return 'weighted'
    if 'Region' in record:
        return 'latency'
    if 'Failover' in record:
        return 'failover'
    if 'GeoLocation' in record:
        return 'geolocation'
    if 'MultiValueAnswer' in record:
        return 'multivalue'
    return 'simple'


async def query_dns_records(
    hosted_zone_id: Annotated[
        str,
        Field(..., description='Route 53 hosted zone ID to query records from.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    record_type: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter by DNS record type: A, AAAA, CNAME, MX, TXT, SRV, NS, SOA, PTR, CAA, NAPTR, SPF. Returns all types if not specified.',
        ),
    ] = None,
    name_prefix: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter records whose name starts with this prefix. Uses StartRecordName to optimize pagination start point, then filters client-side.',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Query DNS records within a Route 53 hosted zone with optional filtering.

    Use this tool when:
    - Looking up specific DNS records in a hosted zone
    - Verifying DNS configuration for a domain
    - Finding alias records and their targets
    - Checking routing policies (weighted, latency, failover, geolocation)
    - Diagnosing DNS resolution issues

    Common workflows:
    1. list_hosted_zones() → Identify zone → query_dns_records() for record details
    2. Query A/AAAA records → Verify IP addresses or alias targets
    3. Query CNAME records → Trace DNS resolution chain

    Note: StartRecordName/StartRecordType are pagination cursors, NOT filters.
    Client-side filtering is mandatory for accurate results.

    Returns:
        Dict containing:
        - records: List of DNS record objects with name, type, TTL, values, alias info, routing policy
        - count: Number of records found
        - hosted_zone_id: The queried hosted zone ID
    """
    if not hosted_zone_id:
        raise ToolError(
            'Error querying DNS records. Error: hosted_zone_id is required. '
            'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    if record_type is not None and record_type not in VALID_RECORD_TYPES:
        raise ToolError(
            f'Error querying DNS records. Error: Invalid record_type "{record_type}". '
            f'Must be one of: {", ".join(VALID_RECORD_TYPES)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    try:
        client = get_aws_client('route53', None, profile_name)

        params: Dict[str, Any] = {'HostedZoneId': hosted_zone_id}
        if name_prefix:
            params['StartRecordName'] = name_prefix
            if record_type:
                params['StartRecordType'] = record_type

        all_records = []
        while True:
            response = client.list_resource_record_sets(**params)
            record_sets = response.get('ResourceRecordSets', [])

            for rs in record_sets:
                rs_name = rs.get('Name', '')
                rs_type = rs.get('Type', '')

                # Client-side name_prefix filter
                if name_prefix and not rs_name.startswith(name_prefix):
                    # Early-stop: records are lexicographically ordered
                    # If we already collected records and this one doesn't match, stop
                    if all_records or rs_name > name_prefix:
                        return {
                            'records': all_records,
                            'count': len(all_records),
                            'hosted_zone_id': hosted_zone_id,
                        }
                    continue

                # Client-side record_type filter
                if record_type and rs_type != record_type:
                    continue

                is_alias = 'AliasTarget' in rs
                alias_target = None
                if is_alias:
                    at = rs['AliasTarget']
                    alias_target = {
                        'dns_name': at.get('DNSName', ''),
                        'hosted_zone_id': at.get('HostedZoneId', ''),
                        'evaluate_target_health': at.get('EvaluateTargetHealth', False),
                    }

                resource_records = None
                if 'ResourceRecords' in rs:
                    resource_records = [r.get('Value', '') for r in rs['ResourceRecords']]

                record_info = {
                    'name': rs_name,
                    'type': rs_type,
                    'ttl': rs.get('TTL'),
                    'resource_records': resource_records,
                    'alias_target': alias_target,
                    'is_alias': is_alias,
                    'routing_policy': _determine_routing_policy(rs),
                    'health_check_id': rs.get('HealthCheckId'),
                }
                all_records.append(record_info)

            if not response.get('IsTruncated', False):
                break

            params['StartRecordName'] = response['NextRecordName']
            params['StartRecordType'] = response['NextRecordType']
            if 'NextRecordIdentifier' in response:
                params['StartRecordIdentifier'] = response['NextRecordIdentifier']

        return {
            'records': all_records,
            'count': len(all_records),
            'hosted_zone_id': hosted_zone_id,
        }
    except ToolError:
        raise
    except Exception as e:
        error_msg = str(e)
        if 'NoSuchHostedZone' in error_msg:
            raise ToolError(
                f'Error querying DNS records. Error: Hosted zone {hosted_zone_id} not found. '
                f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )
        raise ToolError(
            f'Error querying DNS records. Error: {error_msg}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
