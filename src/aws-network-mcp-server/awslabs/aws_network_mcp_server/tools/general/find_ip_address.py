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


async def find_ip_address(
    ip_address: Annotated[str, Field(..., description='IP address')],
    region: Annotated[
        str,
        Field(
            ...,
            description='AWS Region where to find the IP address. If all_regions is set, then thiss will be ignored.',
        ),
    ],
    all_regions: Annotated[
        bool,
        Field(
            ...,
            description='If set to true, this tool will loop through all regions in the account to find the IP address. False by default',
        ),
    ] = False,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Locate an AWS Elastic Network Interface (ENI) by its IP address.

    Use this tool when:
    - Starting network troubleshooting to find where an IP address is located
    - Identifying which VPC, subnet, and security groups are associated with an IP
    - Determining the AWS resource (EC2, Lambda, RDS, etc.) using a specific IP
    - Beginning path trace analysis by locating source or destination endpoints

    The tool searches for both private and public IP addresses. If all_regions is False,
    it searches only the specified region. If all_regions is True, it searches all
    enabled regions in the account until the IP is found.

    Common workflow:
    1. Use this tool to locate the IP address
    2. Use get_eni_details() to analyze security groups and routing
    3. Use get_vpc_network_details() to understand VPC configuration
    4. Follow routing through Transit Gateway or Cloud WAN as needed

    Returns:
        Dict containing ENI details including:
        - NetworkInterfaceId: The ENI identifier
        - VpcId: The VPC where the ENI is located
        - SubnetId: The subnet where the ENI is located
        - PrivateIpAddress: The primary private IP
        - Association: Public IP details (if assigned)
        - Groups: Security groups attached to the ENI
        - Attachment: Information about attached resource (EC2, Lambda, etc.)
    """
    ec2_client = get_aws_client('ec2', region, profile_name)

    if not all_regions:
        try:
            response = ec2_client.describe_network_interfaces(
                Filters=[{'Name': 'private-ip-address', 'Values': [ip_address]}]
            )

            if response['NetworkInterfaces']:
                return response['NetworkInterfaces'][0]

            # Try public IP if private IP not found
            response = ec2_client.describe_network_interfaces(
                Filters=[{'Name': 'association.public-ip', 'Values': [ip_address]}]
            )

            if response['NetworkInterfaces']:
                return response['NetworkInterfaces'][0]

            raise ToolError(
                f'IP address {ip_address} not found in region {region}. VALIDATE PARAMETERS BEFORE CONTINUING.'
            )

        except Exception as e:
            raise ToolError(
                f'Error searching IP address: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )
    else:
        response = ec2_client.describe_regions()
        regions = [region['RegionName'] for region in response['Regions']]

        error = None
        for region in regions:
            ec2_client = get_aws_client('ec2', region, profile_name)
            try:
                response = ec2_client.describe_network_interfaces(
                    Filters=[{'Name': 'private-ip-address', 'Values': [ip_address]}]
                )

                if response['NetworkInterfaces']:
                    return response['NetworkInterfaces'][0]

                # Try public IP if private IP not found
                response = ec2_client.describe_network_interfaces(
                    Filters=[{'Name': 'association.public-ip', 'Values': [ip_address]}]
                )

                if response['NetworkInterfaces']:
                    return response['NetworkInterfaces'][0]

            except Exception as e:
                error = str(e)
                continue

        # Return error if we got one during the search to not hide it.
        if error:
            raise ToolError(
                f'Error searching IP address in all regions: {error}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )

        raise ToolError('IP address was not found in any region')
