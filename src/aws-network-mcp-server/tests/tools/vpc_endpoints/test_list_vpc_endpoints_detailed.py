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

"""Test cases for the list_vpc_endpoints_detailed tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


list_endpoints_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.vpc_endpoints.list_vpc_endpoints_detailed'
)


class TestListVpcEndpointsDetailed:
    """Test cases for list_vpc_endpoints_detailed function."""

    @pytest.fixture
    def sample_interface_endpoint(self):
        """Sample interface VPC endpoint."""
        return {
            'VpcEndpointId': 'vpce-0123456789abcdef0',
            'ServiceName': 'com.amazonaws.us-east-1.s3',
            'VpcEndpointType': 'Interface',
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'CreationTimestamp': '2024-01-15T10:30:00+00:00',
            'PolicyDocument': '{"Version":"2012-10-17"}',
            'Tags': [{'Key': 'Name', 'Value': 'my-endpoint'}],
            'SubnetIds': ['subnet-111', 'subnet-222'],
            'Groups': [
                {'GroupId': 'sg-aaa', 'GroupName': 'endpoint-sg'},
            ],
            'PrivateDnsEnabled': True,
            'DnsEntries': [
                {
                    'DnsName': 'vpce-0123456789abcdef0-abc.s3.us-east-1.vpce.amazonaws.com',
                    'HostedZoneId': 'Z1234567890',
                },
            ],
            'NetworkInterfaceIds': ['eni-111', 'eni-222'],
        }

    @pytest.fixture
    def sample_gateway_endpoint(self):
        """Sample gateway VPC endpoint."""
        return {
            'VpcEndpointId': 'vpce-gw-0123456789abcdef0',
            'ServiceName': 'com.amazonaws.us-east-1.s3',
            'VpcEndpointType': 'Gateway',
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'CreationTimestamp': '2024-01-10T08:00:00+00:00',
            'PolicyDocument': '{"Version":"2012-10-17"}',
            'Tags': [],
            'RouteTableIds': ['rtb-111', 'rtb-222'],
        }

    @pytest.fixture
    def sample_gwlb_endpoint(self):
        """Sample GatewayLoadBalancer VPC endpoint."""
        return {
            'VpcEndpointId': 'vpce-gwlb-0123456789abcdef0',
            'ServiceName': 'com.amazonaws.vpce.us-east-1.vpce-svc-123',
            'VpcEndpointType': 'GatewayLoadBalancer',
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'CreationTimestamp': '2024-02-01T12:00:00+00:00',
            'PolicyDocument': None,
            'Tags': [],
            'SubnetIds': ['subnet-333'],
            'NetworkInterfaceIds': ['eni-333'],
        }

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_success_interface(
        self, mock_get_client, sample_interface_endpoint
    ):
        """Test successful listing with an interface endpoint."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': [sample_interface_endpoint]}]

        result = await list_endpoints_module.list_vpc_endpoints_detailed(region='us-east-1')

        assert result['count'] == 1
        assert result['region'] == 'us-east-1'
        ep = result['vpc_endpoints'][0]
        assert ep['id'] == 'vpce-0123456789abcdef0'
        assert ep['type'] == 'Interface'
        assert ep['security_group_ids'] == ['sg-aaa']
        assert ep['private_dns_enabled'] is True
        assert len(ep['dns_entries']) == 1
        assert ep['network_interface_ids'] == ['eni-111', 'eni-222']
        assert ep['subnet_ids'] == ['subnet-111', 'subnet-222']
        assert ep['route_table_ids'] is None
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_success_gateway(self, mock_get_client, sample_gateway_endpoint):
        """Test successful listing with a gateway endpoint."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': [sample_gateway_endpoint]}]

        result = await list_endpoints_module.list_vpc_endpoints_detailed(region='us-east-1')

        assert result['count'] == 1
        ep = result['vpc_endpoints'][0]
        assert ep['type'] == 'Gateway'
        assert ep['route_table_ids'] == ['rtb-111', 'rtb-222']
        assert ep['security_group_ids'] is None
        assert ep['private_dns_enabled'] is None
        assert ep['dns_entries'] is None
        assert ep['network_interface_ids'] is None
        assert ep['subnet_ids'] is None

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_success_gwlb(self, mock_get_client, sample_gwlb_endpoint):
        """Test successful listing with a GatewayLoadBalancer endpoint."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': [sample_gwlb_endpoint]}]

        result = await list_endpoints_module.list_vpc_endpoints_detailed(region='us-east-1')

        assert result['count'] == 1
        ep = result['vpc_endpoints'][0]
        assert ep['type'] == 'GatewayLoadBalancer'
        assert ep['subnet_ids'] == ['subnet-333']
        assert ep['network_interface_ids'] == ['eni-333']
        assert ep['security_group_ids'] is None
        assert ep['private_dns_enabled'] is None
        assert ep['dns_entries'] is None
        assert ep['route_table_ids'] is None

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_empty(self, mock_get_client):
        """Test listing with no endpoints found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': []}]

        result = await list_endpoints_module.list_vpc_endpoints_detailed(region='us-east-1')

        assert result['vpc_endpoints'] == []
        assert result['count'] == 0

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_with_vpc_filter(
        self, mock_get_client, sample_interface_endpoint
    ):
        """Test listing with vpc_id filter."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': [sample_interface_endpoint]}]

        result = await list_endpoints_module.list_vpc_endpoints_detailed(
            region='us-east-1', vpc_id='vpc-12345678'
        )

        assert result['count'] == 1
        mock_paginator.paginate.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': ['vpc-12345678']}]
        )

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_with_service_name_filter(
        self, mock_get_client, sample_interface_endpoint
    ):
        """Test listing with service_name filter."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': [sample_interface_endpoint]}]

        result = await list_endpoints_module.list_vpc_endpoints_detailed(
            region='us-east-1', service_name='com.amazonaws.us-east-1.s3'
        )

        assert result['count'] == 1
        mock_paginator.paginate.assert_called_once_with(
            Filters=[{'Name': 'service-name', 'Values': ['com.amazonaws.us-east-1.s3']}]
        )

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_with_both_filters(
        self, mock_get_client, sample_interface_endpoint
    ):
        """Test listing with both vpc_id and service_name filters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': [sample_interface_endpoint]}]

        await list_endpoints_module.list_vpc_endpoints_detailed(
            region='us-east-1',
            vpc_id='vpc-12345678',
            service_name='com.amazonaws.us-east-1.s3',
        )

        mock_paginator.paginate.assert_called_once_with(
            Filters=[
                {'Name': 'vpc-id', 'Values': ['vpc-12345678']},
                {'Name': 'service-name', 'Values': ['com.amazonaws.us-east-1.s3']},
            ]
        )

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_with_profile(self, mock_get_client, sample_interface_endpoint):
        """Test listing with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'VpcEndpoints': [sample_interface_endpoint]}]

        await list_endpoints_module.list_vpc_endpoints_detailed(
            region='us-east-1', profile_name='test-profile'
        )

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', 'test-profile')

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_mixed_types(
        self,
        mock_get_client,
        sample_interface_endpoint,
        sample_gateway_endpoint,
        sample_gwlb_endpoint,
    ):
        """Test listing with mixed endpoint types."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'VpcEndpoints': [
                    sample_interface_endpoint,
                    sample_gateway_endpoint,
                    sample_gwlb_endpoint,
                ]
            }
        ]

        result = await list_endpoints_module.list_vpc_endpoints_detailed(region='us-east-1')

        assert result['count'] == 3
        types = [ep['type'] for ep in result['vpc_endpoints']]
        assert 'Interface' in types
        assert 'Gateway' in types
        assert 'GatewayLoadBalancer' in types

    @patch.object(list_endpoints_module, 'get_aws_client')
    async def test_list_endpoints_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.side_effect = Exception('UnauthorizedAccess')

        with pytest.raises(
            ToolError,
            match='Error listing VPC endpoints. Error: UnauthorizedAccess. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await list_endpoints_module.list_vpc_endpoints_detailed(region='us-east-1')
