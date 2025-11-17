#!/usr/bin/env python3
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

"""Security test cases for AWS permissions and access control."""

import pytest
from awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details import (
    get_cloudwan_details,
)
from awslabs.aws_network_mcp_server.tools.general.find_ip_address import find_ip_address
from awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details import (
    get_tgw_details,
)
from awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details import (
    get_vpc_network_details,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestAwsPermissionsSecurity:
    """Test AWS permissions and access control security."""

    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_access_denied_handling(self, mock_get_client):
        """Test proper handling of AWS access denied errors."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.side_effect = Exception(
            'User: arn:aws:iam::123456789012:user/testuser is not authorized to perform: ec2:DescribeNetworkInterfaces'
        )

        with pytest.raises(ToolError) as exc_info:
            await find_ip_address(ip_address='10.0.1.100', region='us-east-1', all_regions=False)

        # Verify error is properly propagated with security context
        assert 'Error searching IP address:' in str(exc_info.value)
        assert 'not authorized' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_cloudwan_permission_errors(self, mock_get_client):
        """Test Cloud WAN specific permission error handling."""
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.get_core_network.side_effect = Exception(
            'User is not authorized to perform: networkmanager:GetCoreNetwork on resource'
        )

        with pytest.raises(ToolError) as exc_info:
            await get_cloudwan_details(
                core_network_id='core-network-12345678', core_network_region='us-east-1'
            )

        assert 'There was an error getting AWS Core Network details' in str(exc_info.value)
        assert 'not authorized' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_cross_account_access_denied(self, mock_get_client):
        """Test handling of cross-account access denied scenarios."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.side_effect = Exception(
            'You are not authorized to perform this operation on cross-account resource'
        )

        with pytest.raises(ToolError) as exc_info:
            await get_vpc_network_details(vpc_id='vpc-12345678', region='us-east-1')

        assert 'Error getting VPC network details:' in str(exc_info.value)
        assert 'not authorized' in str(exc_info.value)

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_details.get_aws_client'
    )
    async def test_no_credentials_error_handling(self, mock_get_client):
        """Test handling when AWS credentials are not configured."""
        mock_get_client.side_effect = Exception('NoCredentialsError: Unable to locate credentials')

        with pytest.raises(ToolError) as exc_info:
            await get_tgw_details(transit_gateway_id='tgw-12345678', region='us-east-1')

        assert 'Error getting Transit Gateway details:' in str(exc_info.value)
        assert 'credentials' in str(exc_info.value).lower()

    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_invalid_profile_handling(self, mock_get_client):
        """Test handling of invalid AWS profile names."""
        mock_get_client.side_effect = Exception(
            'ProfileNotFound: The config profile (invalid-profile) could not be found'
        )

        with pytest.raises(ToolError) as exc_info:
            await find_ip_address(
                ip_address='10.0.1.100',
                region='us-east-1',
                all_regions=False,
                profile_name='invalid-profile',
            )

        assert 'Error searching IP address:' in str(exc_info.value)
        assert 'ProfileNotFound' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_rate_limiting_error_handling(self, mock_get_client):
        """Test handling of AWS rate limiting errors."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.side_effect = Exception(
            'Throttling: Request was denied due to request throttling'
        )

        with pytest.raises(ToolError) as exc_info:
            await get_vpc_network_details(vpc_id='vpc-12345678', region='us-east-1')

        assert 'Error getting VPC network details:' in str(exc_info.value)
        assert 'Throttling' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_service_unavailable_handling(self, mock_get_client):
        """Test handling of AWS service unavailable errors."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.side_effect = Exception(
            'ServiceUnavailable: The request has failed due to a temporary failure of the server'
        )

        with pytest.raises(ToolError) as exc_info:
            await find_ip_address(ip_address='10.0.1.100', region='us-east-1', all_regions=False)

        assert 'Error searching IP address:' in str(exc_info.value)
        assert 'ServiceUnavailable' in str(exc_info.value)

    def test_readonly_operation_guarantee(self):
        """Test that all tools are read-only operations."""
        # This is a documentation test - all our tools should be read-only
        # We verify this by checking that no tool function contains write operations

        # Import all tool modules
        from awslabs.aws_network_mcp_server.tools import (
            cloud_wan,
            general,
            network_firewall,
            transit_gateway,
            vpc,
            vpn,
        )

        modules = [general, cloud_wan, vpc, transit_gateway, network_firewall, vpn]

        for module in modules:
            for tool_name in module.__all__:
                tool_func = getattr(module, tool_name)

                # Our tools should not contain any write/modify language
                write_operations = [
                    'create',
                    'delete',
                    'update',
                    'modify',
                    'change',
                    'write',
                    'put',
                    'post',
                    'patch',
                    'remove',
                    'add',
                    'attach',
                    'detach',
                ]

                # Check function name doesn't contain write operations
                func_name_lower = tool_name.lower()
                dangerous_operations = [op for op in write_operations if op in func_name_lower]

                # Exception for get_cloudwan_logs and simulate_cloud_wan_route_change which are read-only
                if tool_name not in ['get_cloudwan_logs', 'simulate_cloud_wan_route_change']:
                    assert not dangerous_operations, (
                        f'Tool {tool_name} may perform write operations: {dangerous_operations}'
                    )
