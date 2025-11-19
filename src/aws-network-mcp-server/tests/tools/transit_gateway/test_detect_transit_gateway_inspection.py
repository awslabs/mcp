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

"""Test cases for the detect_tgw_inspection tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection import (
    detect_tgw_inspection,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestDetectTgwInspection:
    """Test cases for detect_tgw_inspection function."""

    @pytest.fixture
    def mock_clients(self):
        """Mock AWS clients."""
        ec2_client = MagicMock()
        nfw_client = MagicMock()
        elbv2_client = MagicMock()
        return ec2_client, nfw_client, elbv2_client

    @pytest.fixture
    def sample_firewalls(self):
        """Sample Network Firewall response."""
        return {
            'Firewalls': [
                {'FirewallName': 'test-fw', 'VpcId': 'vpc-fw123'},
                {'FirewallName': 'test-fw2', 'VpcId': 'vpc-fw456'},
            ]
        }

    @pytest.fixture
    def sample_attachments(self):
        """Sample TGW attachments."""
        return {
            'TransitGatewayAttachments': [
                {
                    'TransitGatewayAttachmentId': 'tgw-attach-vpc1',
                    'ResourceType': 'vpc',
                    'ResourceId': 'vpc-fw123',
                    'State': 'available',
                },
                {
                    'TransitGatewayAttachmentId': 'tgw-attach-vpc2',
                    'ResourceType': 'vpc',
                    'ResourceId': 'vpc-regular',
                    'State': 'available',
                },
                {
                    'TransitGatewayAttachmentId': 'tgw-attach-nf1',
                    'ResourceType': 'network-function',
                    'ResourceId': 'arn:aws:network-firewall:us-east-1:123456789012:firewall/test-nf',
                    'State': 'available',
                },
            ]
        }

    @pytest.fixture
    def sample_vpc_endpoints(self):
        """Sample VPC endpoints."""
        return {
            'VpcEndpoints': [
                {
                    'VpcEndpointId': 'vpce-gwlb123',
                    'VpcId': 'vpc-regular',
                    'ServiceName': 'com.amazonaws.vpce.us-east-1.vpce-svc-123.test-gwlb',
                    'State': 'available',
                }
            ]
        }

    @pytest.fixture
    def sample_gwlb(self):
        """Sample GWLB response."""
        return {
            'LoadBalancers': [
                {
                    'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/gwy/test-gwlb/123',
                    'LoadBalancerName': 'test-gwlb',
                    'DNSName': 'test-gwlb-123.elb.us-east-1.amazonaws.com',
                    'Scheme': 'internal',
                    'Type': 'gateway',
                }
            ]
        }

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_no_firewalls(self, mock_get_client, mock_clients):
        """Test when no firewalls are detected."""
        ec2_client, nfw_client, _ = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client]

        nfw_client.list_firewalls.return_value = {'Firewalls': []}
        ec2_client.describe_transit_gateway_attachments.return_value = {
            'TransitGatewayAttachments': []
        }

        result = await detect_tgw_inspection('tgw-123', 'us-east-1')

        assert result['has_firewalls'] is False
        assert result['total_firewalls'] == 0
        assert result['vpc_firewall_attachments'] == []
        assert result['tgw_firewall_attachments'] == []
        assert result['gwlb_firewalls'] == []

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_vpc_firewall_detection(
        self, mock_get_client, mock_clients, sample_firewalls, sample_attachments
    ):
        """Test VPC-attached firewall detection."""
        ec2_client, nfw_client, _ = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client]

        nfw_client.list_firewalls.return_value = sample_firewalls
        ec2_client.describe_transit_gateway_attachments.return_value = sample_attachments

        result = await detect_tgw_inspection('tgw-123', 'us-east-1')

        assert result['has_firewalls'] is True
        assert result['total_vpc_firewalls'] == 1
        assert len(result['vpc_firewall_attachments']) == 1
        assert result['vpc_firewall_attachments'][0]['ResourceId'] == 'vpc-fw123'

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_tgw_firewall_detection(
        self, mock_get_client, mock_clients, sample_firewalls, sample_attachments
    ):
        """Test TGW-attached firewall detection."""
        ec2_client, nfw_client, _ = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client]

        nfw_client.list_firewalls.return_value = sample_firewalls
        nfw_client.describe_firewall.return_value = {
            'Firewall': {'FirewallStatus': {'Status': 'READY'}}
        }
        ec2_client.describe_transit_gateway_attachments.return_value = sample_attachments

        result = await detect_tgw_inspection('tgw-123', 'us-east-1')

        assert result['total_tgw_firewalls'] == 1
        assert len(result['tgw_firewall_attachments']) == 1
        assert result['tgw_firewall_attachments'][0]['firewall_name'] == 'test-nf'
        assert result['tgw_firewall_attachments'][0]['firewall_status'] == 'READY'

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_gwlb_firewall_detection(
        self,
        mock_get_client,
        mock_clients,
        sample_firewalls,
        sample_attachments,
        sample_vpc_endpoints,
        sample_gwlb,
    ):
        """Test GWLB firewall detection."""
        ec2_client, nfw_client, elbv2_client = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client, elbv2_client]

        nfw_client.list_firewalls.return_value = sample_firewalls
        ec2_client.describe_transit_gateway_attachments.return_value = sample_attachments
        ec2_client.describe_vpc_endpoints.return_value = sample_vpc_endpoints
        elbv2_client.describe_load_balancers.return_value = sample_gwlb

        result = await detect_tgw_inspection('tgw-123', 'us-east-1')

        assert result['total_gwlb_firewalls'] == 1
        assert len(result['gwlb_firewalls']) == 1
        assert result['gwlb_firewalls'][0]['gwlb_name'] == 'test-gwlb'

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_nfw_describe_error(
        self, mock_get_client, mock_clients, sample_firewalls, sample_attachments
    ):
        """Test handling of Network Firewall describe errors."""
        ec2_client, nfw_client, _ = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client]

        nfw_client.list_firewalls.return_value = sample_firewalls
        nfw_client.describe_firewall.side_effect = Exception('Firewall not found')
        ec2_client.describe_transit_gateway_attachments.return_value = sample_attachments

        result = await detect_tgw_inspection('tgw-123', 'us-east-1')

        assert result['total_tgw_firewalls'] == 1
        assert 'note' in result['tgw_firewall_attachments'][0]

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_gwlb_describe_error(
        self,
        mock_get_client,
        mock_clients,
        sample_firewalls,
        sample_attachments,
        sample_vpc_endpoints,
    ):
        """Test handling of GWLB describe errors."""
        ec2_client, nfw_client, elbv2_client = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client, elbv2_client]

        nfw_client.list_firewalls.return_value = sample_firewalls
        ec2_client.describe_transit_gateway_attachments.return_value = sample_attachments
        ec2_client.describe_vpc_endpoints.return_value = sample_vpc_endpoints
        elbv2_client.describe_load_balancers.side_effect = Exception('GWLB not found')

        result = await detect_tgw_inspection('tgw-123', 'us-east-1')

        assert result['total_gwlb_firewalls'] == 1
        assert 'gwlb_details' in result['gwlb_firewalls'][0]

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_with_profile(self, mock_get_client, mock_clients, sample_firewalls):
        """Test with custom profile."""
        ec2_client, nfw_client, _ = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client]

        nfw_client.list_firewalls.return_value = sample_firewalls
        ec2_client.describe_transit_gateway_attachments.return_value = {
            'TransitGatewayAttachments': []
        }

        await detect_tgw_inspection('tgw-123', 'us-west-2', 'test-profile')

        assert mock_get_client.call_count == 2
        mock_get_client.assert_any_call('ec2', 'us-west-2', 'test-profile')
        mock_get_client.assert_any_call('network-firewall', 'us-west-2', 'test-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_get_client.side_effect = Exception('AWS API Error')

        with pytest.raises(ToolError, match='Error detecting firewall attachments'):
            await detect_tgw_inspection('tgw-123', 'us-east-1')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.detect_transit_gateway_inspection.get_aws_client'
    )
    async def test_all_firewall_types(
        self,
        mock_get_client,
        mock_clients,
        sample_firewalls,
        sample_attachments,
        sample_vpc_endpoints,
        sample_gwlb,
    ):
        """Test detection of all firewall types together."""
        ec2_client, nfw_client, elbv2_client = mock_clients
        mock_get_client.side_effect = [ec2_client, nfw_client, elbv2_client]

        nfw_client.list_firewalls.return_value = sample_firewalls
        nfw_client.describe_firewall.return_value = {
            'Firewall': {'FirewallStatus': {'Status': 'READY'}}
        }
        ec2_client.describe_transit_gateway_attachments.return_value = sample_attachments
        ec2_client.describe_vpc_endpoints.return_value = sample_vpc_endpoints
        elbv2_client.describe_load_balancers.return_value = sample_gwlb

        result = await detect_tgw_inspection('tgw-123', 'us-east-1')

        assert result['has_firewalls'] is True
        assert result['total_vpc_firewalls'] == 1
        assert result['total_tgw_firewalls'] == 1
        assert result['total_gwlb_firewalls'] == 1
        assert result['total_firewalls'] == 3
        assert (
            'Found 1 VPC firewalls, 1 TGW firewalls, and 1 GWLB firewalls'
            in result['inspection_summary']
        )
