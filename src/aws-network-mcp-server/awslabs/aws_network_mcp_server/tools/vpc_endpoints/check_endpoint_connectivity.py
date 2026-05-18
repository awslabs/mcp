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


async def check_endpoint_connectivity(
    vpc_endpoint_id: Annotated[
        str,
        Field(
            ...,
            description='The VPC endpoint ID to check connectivity for (must start with vpce-).',
        ),
    ],
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the VPC endpoint is deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Check connectivity diagnostics for a specific VPC endpoint.

    Aggregates endpoint state, private DNS config, security group rules, and ENI
    details into a single connectivity diagnostic view. Handles partial failures
    gracefully — if a sub-call (security groups or ENIs) fails, the successfully
    retrieved data is still returned with an error indicator for the failed check.

    Use this tool when:
    - Diagnosing why a PrivateLink connection is failing
    - Verifying security group rules allow traffic to the endpoint
    - Checking private DNS configuration for interface endpoints
    - Confirming ENI placement across Availability Zones

    Common workflows:
    1. list_vpc_endpoints_detailed() → check_endpoint_connectivity() for a specific endpoint
    2. check_endpoint_connectivity() → Review SG rules → get_eni_details() for deeper analysis
    3. check_endpoint_connectivity() → Verify private DNS → query_dns_records() for DNS validation

    Returns:
        Dict containing:
        - endpoint: Basic endpoint info with state and availability
        - private_dns: DNS configuration and entries
        - security_groups: SG rules (interface endpoints only) or None
        - security_groups_error: Error message if SG retrieval failed
        - network_interfaces: ENI details or None
        - network_interfaces_error: Error message if ENI retrieval failed
        - connectivity_checks: Summary of key connectivity indicators
        - region: AWS region queried
    """
    if not vpc_endpoint_id.startswith('vpce-'):
        raise ToolError(
            'Error checking endpoint connectivity. Error: Invalid vpc_endpoint_id format. '
            'Must start with "vpce-". '
            'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    try:
        client = get_aws_client('ec2', region, profile_name)
        response = client.describe_vpc_endpoints(VpcEndpointIds=[vpc_endpoint_id])
        endpoints = response.get('VpcEndpoints', [])
        if not endpoints:
            raise ToolError(
                f'Error checking endpoint connectivity. Error: VPC endpoint not found: '
                f'{vpc_endpoint_id}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )
        ep = endpoints[0]
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error checking endpoint connectivity. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    endpoint_type = ep.get('VpcEndpointType', '')
    endpoint_state = ep.get('State', '')
    is_available = endpoint_state == 'available'

    endpoint_info = {
        'id': ep.get('VpcEndpointId', ''),
        'service_name': ep.get('ServiceName', ''),
        'type': endpoint_type,
        'vpc_id': ep.get('VpcId', ''),
        'state': endpoint_state,
        'is_available': is_available,
    }

    # Private DNS info
    dns_entries = [
        {
            'dns_name': d.get('DnsName', ''),
            'hosted_zone_id': d.get('HostedZoneId', ''),
        }
        for d in ep.get('DnsEntries', [])
    ]
    private_dns_enabled = ep.get('PrivateDnsEnabled', False)
    private_dns = {
        'enabled': private_dns_enabled,
        'dns_entries': dns_entries,
    }

    # Security groups — only for interface endpoints
    security_groups = None
    security_groups_error = None
    sg_ids = [g.get('GroupId', '') for g in ep.get('Groups', [])]
    if endpoint_type == 'Interface' and sg_ids:
        try:
            sg_response = client.describe_security_groups(GroupIds=sg_ids)
            security_groups = []
            for sg in sg_response.get('SecurityGroups', []):
                inbound_rules = []
                for rule in sg.get('IpPermissions', []):
                    protocol = rule.get('IpProtocol', '-1')
                    from_port = rule.get('FromPort')
                    to_port = rule.get('ToPort')
                    if from_port is not None and to_port is not None:
                        port_range = (
                            str(from_port) if from_port == to_port else f'{from_port}-{to_port}'
                        )
                    else:
                        port_range = 'all'

                    sources = []
                    for ip_range in rule.get('IpRanges', []):
                        sources.append(ip_range.get('CidrIp', ''))
                    for ip_range in rule.get('Ipv6Ranges', []):
                        sources.append(ip_range.get('CidrIpv6', ''))
                    for prefix in rule.get('PrefixListIds', []):
                        sources.append(prefix.get('PrefixListId', ''))
                    for group in rule.get('UserIdGroupPairs', []):
                        sources.append(group.get('GroupId', ''))

                    for source in sources:
                        inbound_rules.append(
                            {
                                'protocol': protocol,
                                'port_range': port_range,
                                'source': source,
                            }
                        )

                security_groups.append(
                    {
                        'id': sg.get('GroupId', ''),
                        'name': sg.get('GroupName', ''),
                        'inbound_rules': inbound_rules,
                    }
                )
        except Exception as e:
            security_groups = None
            security_groups_error = str(e)

    # Network interfaces
    network_interfaces = None
    network_interfaces_error = None
    eni_ids = ep.get('NetworkInterfaceIds', [])
    if eni_ids:
        try:
            eni_response = client.describe_network_interfaces(NetworkInterfaceIds=eni_ids)
            network_interfaces = []
            for eni in eni_response.get('NetworkInterfaces', []):
                network_interfaces.append(
                    {
                        'id': eni.get('NetworkInterfaceId', ''),
                        'subnet_id': eni.get('SubnetId', ''),
                        'availability_zone': eni.get('AvailabilityZone', ''),
                        'private_ip': eni.get('PrivateIpAddress', ''),
                    }
                )
        except Exception as e:
            network_interfaces = None
            network_interfaces_error = str(e)

    connectivity_checks = {
        'state_ok': is_available,
        'has_dns_entries': len(dns_entries) > 0,
        'private_dns_enabled': private_dns_enabled,
    }

    return {
        'endpoint': endpoint_info,
        'private_dns': private_dns,
        'security_groups': security_groups,
        'security_groups_error': security_groups_error,
        'network_interfaces': network_interfaces,
        'network_interfaces_error': network_interfaces_error,
        'connectivity_checks': connectivity_checks,
        'region': region,
    }
