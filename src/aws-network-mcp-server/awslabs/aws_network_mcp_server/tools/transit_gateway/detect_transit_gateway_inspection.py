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


async def detect_tgw_inspection(
    transit_gateway_id: Annotated[str, Field(..., description='Transit Gateway ID')],
    region: Annotated[str, Field(..., description='AWS region where TGW is deployed')],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Detect AWS Network Firewalls and 3rd party firewalls attached to a Transit Gateway.

    Use this tool when:
    - Analyzing network security architecture and traffic inspection points
    - Troubleshooting connectivity issues that may involve firewall filtering
    - Validating that firewalls are properly attached to Transit Gateway for inspection
    - Planning network changes that could affect firewall traffic flow
    - Auditing security posture of Transit Gateway-based networks
    - Determining if traffic between specific segments will be inspected by firewalls

    This tool analyzes three types of firewall deployments:
    1. AWS Network Firewalls attached via VPC attachments
    2. AWS Network Firewalls attached via network-function attachments
    3. 3rd party firewalls behind Gateway Load Balancer endpoints

    Common troubleshooting scenarios:
    - "Why is traffic being blocked between two VPCs?"
    - "Is my traffic going through a firewall for inspection?"
    - "What firewalls are protecting my Transit Gateway traffic?"

    Returns:
        Dict containing inspection firewall details, traffic inspection status, and detailed
        analysis of which firewalls will process traffic through the Transit Gateway:
        - vpc_firewall_attachments: AWS Network Firewalls in VPCs attached to TGW
        - tgw_firewall_attachments: AWS Network Firewalls directly attached to TGW
        - gwlb_firewalls: 3rd party firewalls behind GWLB endpoints
        - has_firewalls: Boolean indicating if any firewalls were detected
        - total_firewalls: Total count of all detected firewalls
        - inspection_summary: Human-readable summary of findings
    """
    try:
        ec2_client = get_aws_client('ec2', region, profile_name)
        nfw_client = get_aws_client('network-firewall', region, profile_name)

        # Get AWS Network Firewalls (VPC-attached)
        aws_firewalls = nfw_client.list_firewalls()['Firewalls']
        aws_firewall_vpcs = {fw['VpcId'] for fw in aws_firewalls}

        # Get all TGW attachments (VPC and Network Function)
        all_attachments = ec2_client.describe_transit_gateway_attachments(
            Filters=[
                {'Name': 'transit-gateway-id', 'Values': [transit_gateway_id]},
                {'Name': 'state', 'Values': ['available']},
            ]
        )['TransitGatewayAttachments']

        # Separate VPC and Network Function attachments
        vpc_attachments = [att for att in all_attachments if att['ResourceType'] == 'vpc']
        nf_attachments = [
            att for att in all_attachments if att['ResourceType'] == 'network-function'
        ]

        attached_vpc_ids = [att['ResourceId'] for att in vpc_attachments]

        # Find VPC-attached AWS firewall attachments
        vpc_firewall_attachments = [
            att for att in vpc_attachments if att['ResourceId'] in aws_firewall_vpcs
        ]

        # Find TGW-attached AWS Network Firewalls
        tgw_firewall_attachments = []
        for nf_att in nf_attachments:
            # Check if this is a Network Firewall attachment
            try:
                firewall_arn = nf_att.get('ResourceId', '')
                if 'network-firewall' in firewall_arn:
                    # Get firewall details
                    firewall_name = firewall_arn.split('/')[-1]
                    firewall_details = nfw_client.describe_firewall(FirewallName=firewall_name)
                    tgw_firewall_attachments.append(
                        {
                            'attachment_id': nf_att['TransitGatewayAttachmentId'],
                            'firewall_arn': firewall_arn,
                            'firewall_name': firewall_name,
                            'attachment_state': nf_att['State'],
                            'firewall_status': firewall_details['Firewall']['FirewallStatus'][
                                'Status'
                            ],
                        }
                    )
            except Exception:
                # If we can't get firewall details, still record the attachment
                tgw_firewall_attachments.append(
                    {
                        'attachment_id': nf_att['TransitGatewayAttachmentId'],
                        'resource_id': nf_att.get('ResourceId', ''),
                        'attachment_state': nf_att['State'],
                        'note': 'Network function attachment - unable to verify if Network Firewall',
                    }
                )

        # Detect 3rd party firewalls via Gateway Load Balancer endpoints
        gwlb_firewalls = []

        if attached_vpc_ids:
            # Find GWLB endpoints in attached VPCs
            vpc_endpoints = ec2_client.describe_vpc_endpoints(
                Filters=[
                    {'Name': 'vpc-id', 'Values': attached_vpc_ids},
                    {'Name': 'vpc-endpoint-type', 'Values': ['GatewayLoadBalancer']},
                    {'Name': 'state', 'Values': ['available']},
                ]
            )['VpcEndpoints']

            for endpoint in vpc_endpoints:
                # Get the target GWLB details
                gwlb_arn = endpoint.get('ServiceName', '')
                if gwlb_arn.startswith('com.amazonaws.vpce.'):
                    # Extract service name and get GWLB details
                    try:
                        elbv2_client = get_aws_client('elbv2', region, profile_name)
                        # Parse GWLB name from service name
                        service_parts = gwlb_arn.split('.')
                        if len(service_parts) >= 4:
                            gwlb_name = service_parts[-1]

                            # Get GWLB details
                            gwlbs = elbv2_client.describe_load_balancers(Names=[gwlb_name])[
                                'LoadBalancers'
                            ]

                            if gwlbs:
                                gwlb = gwlbs[0]
                                gwlb_firewalls.append(
                                    {
                                        'vpc_endpoint_id': endpoint['VpcEndpointId'],
                                        'vpc_id': endpoint['VpcId'],
                                        'gwlb_arn': gwlb['LoadBalancerArn'],
                                        'gwlb_name': gwlb['LoadBalancerName'],
                                        'gwlb_dns': gwlb['DNSName'],
                                        'gwlb_scheme': gwlb['Scheme'],
                                        'gwlb_type': gwlb['Type'],
                                        'endpoint_state': endpoint['State'],
                                        'service_name': endpoint['ServiceName'],
                                    }
                                )
                    except Exception:
                        # If GWLB details can't be retrieved, still record the endpoint
                        gwlb_firewalls.append(
                            {
                                'vpc_endpoint_id': endpoint['VpcEndpointId'],
                                'vpc_id': endpoint['VpcId'],
                                'service_name': endpoint['ServiceName'],
                                'endpoint_state': endpoint['State'],
                                'gwlb_details': 'Unable to retrieve GWLB details',
                            }
                        )

        total_aws_firewalls = len(vpc_firewall_attachments) + len(tgw_firewall_attachments)
        total_firewalls = total_aws_firewalls + len(gwlb_firewalls)

        return {
            'transit_gateway_id': transit_gateway_id,
            'region': region,
            'vpc_firewall_attachments': vpc_firewall_attachments,
            'tgw_firewall_attachments': tgw_firewall_attachments,
            'gwlb_firewalls': gwlb_firewalls,
            'has_firewalls': total_firewalls > 0,
            'total_vpc_firewalls': len(vpc_firewall_attachments),
            'total_tgw_firewalls': len(tgw_firewall_attachments),
            'total_gwlb_firewalls': len(gwlb_firewalls),
            'total_firewalls': total_firewalls,
            'inspection_summary': f'Found {len(vpc_firewall_attachments)} VPC firewalls, {len(tgw_firewall_attachments)} TGW firewalls, and {len(gwlb_firewalls)} GWLB firewalls',
        }

    except Exception as e:
        raise ToolError(
            f'Error detecting firewall attachments: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
