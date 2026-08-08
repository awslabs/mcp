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

"""Test cases for the check_endpoint_connectivity tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


check_conn_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.vpc_endpoints.check_endpoint_connectivity'
)

SAMPLE_ENDPOINT_ID = 'vpce-0123456789abcdef0'


class TestCheckEndpointConnectivity:
    """Test cases for check_endpoint_connectivity function."""

    @pytest.fixture
    def sample_interface_endpoint(self):
        """Sample interface endpoint from DescribeVpcEndpoints."""
        return {
            'VpcEndpointId': SAMPLE_ENDPOINT_ID,
            'ServiceName': 'com.amazonaws.us-east-1.execute-api',
            'VpcEndpointType': 'Interface',
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'PrivateDnsEnabled': True,
            'DnsEntries': [
                {
                    'DnsName': 'vpce-0123456789abcdef0.execute-api.us-east-1.vpce.amazonaws.com',
                    'HostedZoneId': 'Z1234567890',
                },
            ],
            'Groups': [
                {'GroupId': 'sg-aaa', 'GroupName': 'endpoint-sg'},
            ],
            'NetworkInterfaceIds': ['eni-111', 'eni-222'],
        }

    @pytest.fixture
    def sample_gateway_endpoint(self):
        """Sample gateway endpoint from DescribeVpcEndpoints."""
        return {
            'VpcEndpointId': 'vpce-gw-0123456789abcdef0',
            'ServiceName': 'com.amazonaws.us-east-1.s3',
            'VpcEndpointType': 'Gateway',
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'PrivateDnsEnabled': False,
            'DnsEntries': [],
            'Groups': [],
            'NetworkInterfaceIds': [],
            'RouteTableIds': ['rtb-111'],
        }

    @pytest.fixture
    def sample_security_groups(self):
        """Sample security groups response."""
        return {
            'SecurityGroups': [
                {
                    'GroupId': 'sg-aaa',
                    'GroupName': 'endpoint-sg',
                    'IpPermissions': [
                        {
                            'IpProtocol': 'tcp',
                            'FromPort': 443,
                            'ToPort': 443,
                            'IpRanges': [{'CidrIp': '10.0.0.0/8'}],
                            'Ipv6Ranges': [],
                            'PrefixListIds': [],
                            'UserIdGroupPairs': [],
                        },
                    ],
                }
            ]
        }

    @pytest.fixture
    def sample_enis(self):
        """Sample network interfaces response."""
        return {
            'NetworkInterfaces': [
                {
                    'NetworkInterfaceId': 'eni-111',
                    'SubnetId': 'subnet-aaa',
                    'AvailabilityZone': 'us-east-1a',
                    'PrivateIpAddress': '10.0.1.100',
                },
                {
                    'NetworkInterfaceId': 'eni-222',
                    'SubnetId': 'subnet-bbb',
                    'AvailabilityZone': 'us-east-1b',
                    'PrivateIpAddress': '10.0.2.100',
                },
            ]
        }

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_success(
        self,
        mock_get_client,
        sample_interface_endpoint,
        sample_security_groups,
        sample_enis,
    ):
        """Test successful connectivity check for interface endpoint."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {
            'VpcEndpoints': [sample_interface_endpoint]
        }
        mock_client.describe_security_groups.return_value = sample_security_groups
        mock_client.describe_network_interfaces.return_value = sample_enis

        result = await check_conn_module.check_endpoint_connectivity(
            vpc_endpoint_id=SAMPLE_ENDPOINT_ID, region='us-east-1'
        )

        assert result['endpoint']['id'] == SAMPLE_ENDPOINT_ID
        assert result['endpoint']['is_available'] is True
        assert result['private_dns']['enabled'] is True
        assert len(result['private_dns']['dns_entries']) == 1
        assert result['security_groups'] is not None
        assert len(result['security_groups']) == 1
        assert result['security_groups'][0]['id'] == 'sg-aaa'
        assert result['security_groups'][0]['inbound_rules'][0]['port_range'] == '443'
        assert result['security_groups'][0]['inbound_rules'][0]['source'] == '10.0.0.0/8'
        assert result['security_groups_error'] is None
        assert result['network_interfaces'] is not None
        assert len(result['network_interfaces']) == 2
        assert result['network_interfaces_error'] is None
        assert result['connectivity_checks']['state_ok'] is True
        assert result['connectivity_checks']['has_dns_entries'] is True
        assert result['connectivity_checks']['private_dns_enabled'] is True
        assert result['region'] == 'us-east-1'
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)

    async def test_check_connectivity_invalid_id(self):
        """Test invalid endpoint ID validation."""
        with pytest.raises(
            ToolError,
            match='Invalid vpc_endpoint_id format',
        ):
            await check_conn_module.check_endpoint_connectivity(
                vpc_endpoint_id='invalid-id', region='us-east-1'
            )

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_not_found(self, mock_get_client):
        """Test endpoint not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {'VpcEndpoints': []}

        with pytest.raises(
            ToolError,
            match='VPC endpoint not found',
        ):
            await check_conn_module.check_endpoint_connectivity(
                vpc_endpoint_id=SAMPLE_ENDPOINT_ID, region='us-east-1'
            )

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_unavailable_state(self, mock_get_client):
        """Test endpoint in non-available state."""
        ep = {
            'VpcEndpointId': SAMPLE_ENDPOINT_ID,
            'ServiceName': 'com.amazonaws.us-east-1.s3',
            'VpcEndpointType': 'Interface',
            'VpcId': 'vpc-12345678',
            'State': 'pending',
            'PrivateDnsEnabled': False,
            'DnsEntries': [],
            'Groups': [],
            'NetworkInterfaceIds': [],
        }
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {'VpcEndpoints': [ep]}

        result = await check_conn_module.check_endpoint_connectivity(
            vpc_endpoint_id=SAMPLE_ENDPOINT_ID, region='us-east-1'
        )

        assert result['endpoint']['state'] == 'pending'
        assert result['endpoint']['is_available'] is False
        assert result['connectivity_checks']['state_ok'] is False

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_sg_retrieval_failure(
        self, mock_get_client, sample_interface_endpoint, sample_enis
    ):
        """Test partial failure when security group retrieval fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {
            'VpcEndpoints': [sample_interface_endpoint]
        }
        mock_client.describe_security_groups.side_effect = Exception('AccessDenied')
        mock_client.describe_network_interfaces.return_value = sample_enis

        result = await check_conn_module.check_endpoint_connectivity(
            vpc_endpoint_id=SAMPLE_ENDPOINT_ID, region='us-east-1'
        )

        assert result['security_groups'] is None
        assert result['security_groups_error'] == 'AccessDenied'
        assert result['network_interfaces'] is not None
        assert len(result['network_interfaces']) == 2
        assert result['network_interfaces_error'] is None

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_eni_retrieval_failure(
        self, mock_get_client, sample_interface_endpoint, sample_security_groups
    ):
        """Test partial failure when ENI retrieval fails."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {
            'VpcEndpoints': [sample_interface_endpoint]
        }
        mock_client.describe_security_groups.return_value = sample_security_groups
        mock_client.describe_network_interfaces.side_effect = Exception('Throttling')

        result = await check_conn_module.check_endpoint_connectivity(
            vpc_endpoint_id=SAMPLE_ENDPOINT_ID, region='us-east-1'
        )

        assert result['security_groups'] is not None
        assert result['security_groups_error'] is None
        assert result['network_interfaces'] is None
        assert result['network_interfaces_error'] == 'Throttling'

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_gateway_no_sgs_no_enis(
        self, mock_get_client, sample_gateway_endpoint
    ):
        """Test gateway endpoint has no SGs or ENIs to check."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {
            'VpcEndpoints': [sample_gateway_endpoint]
        }

        result = await check_conn_module.check_endpoint_connectivity(
            vpc_endpoint_id='vpce-gw-0123456789abcdef0', region='us-east-1'
        )

        assert result['endpoint']['type'] == 'Gateway'
        assert result['security_groups'] is None
        assert result['security_groups_error'] is None
        assert result['network_interfaces'] is None
        assert result['network_interfaces_error'] is None

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_private_dns_disabled(self, mock_get_client):
        """Test endpoint with private DNS disabled."""
        ep = {
            'VpcEndpointId': SAMPLE_ENDPOINT_ID,
            'ServiceName': 'com.amazonaws.us-east-1.s3',
            'VpcEndpointType': 'Interface',
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'PrivateDnsEnabled': False,
            'DnsEntries': [
                {
                    'DnsName': 'vpce-0123456789abcdef0.s3.us-east-1.vpce.amazonaws.com',
                    'HostedZoneId': 'Z1234567890',
                },
            ],
            'Groups': [],
            'NetworkInterfaceIds': [],
        }
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {'VpcEndpoints': [ep]}

        result = await check_conn_module.check_endpoint_connectivity(
            vpc_endpoint_id=SAMPLE_ENDPOINT_ID, region='us-east-1'
        )

        assert result['private_dns']['enabled'] is False
        assert result['connectivity_checks']['private_dns_enabled'] is False
        assert result['connectivity_checks']['has_dns_entries'] is True

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_with_profile(
        self, mock_get_client, sample_interface_endpoint
    ):
        """Test connectivity check with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.return_value = {
            'VpcEndpoints': [sample_interface_endpoint]
        }
        mock_client.describe_security_groups.return_value = {'SecurityGroups': []}
        mock_client.describe_network_interfaces.return_value = {'NetworkInterfaces': []}

        await check_conn_module.check_endpoint_connectivity(
            vpc_endpoint_id=SAMPLE_ENDPOINT_ID,
            region='us-east-1',
            profile_name='test-profile',
        )

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', 'test-profile')

    @patch.object(check_conn_module, 'get_aws_client')
    async def test_check_connectivity_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpc_endpoints.side_effect = Exception('ServiceUnavailableException')

        with pytest.raises(
            ToolError,
            match='Error checking endpoint connectivity. Error: ServiceUnavailableException. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await check_conn_module.check_endpoint_connectivity(
                vpc_endpoint_id=SAMPLE_ENDPOINT_ID, region='us-east-1'
            )
