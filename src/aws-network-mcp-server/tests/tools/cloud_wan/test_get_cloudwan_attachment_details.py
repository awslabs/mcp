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

"""Test cases for the get_cloudwan_attachment_details tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
attachment_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_attachment_details'
)


@patch.object(attachment_module, 'get_aws_client')
async def test_vpc_attachment_success(mock_get_client):
    """Test successful VPC attachment retrieval."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {
        'VpcAttachment': {
            'Attachment': {'AttachmentId': 'attachment-123'},
            'SubnetArns': ['arn:aws:ec2:us-east-1:123456789012:subnet/subnet-123'],
            'Options': {'Ipv6Support': False},
        }
    }

    result = await attachment_module.get_cwan_attachment('attachment-123', 'us-east-1')

    assert result['attachment_type'] == 'VPC'
    assert result['attachment']['AttachmentId'] == 'attachment-123'
    assert result['vpc_specific']['subnet_arns'] == [
        'arn:aws:ec2:us-east-1:123456789012:subnet/subnet-123'
    ]
    assert result['vpc_specific']['options']['Ipv6Support'] is False


@patch.object(attachment_module, 'get_aws_client')
async def test_connect_attachment_success(mock_get_client):
    """Test successful Connect attachment retrieval."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {}
    mock_client.get_connect_attachment.return_value = {
        'ConnectAttachment': {
            'Attachment': {'AttachmentId': 'attachment-456'},
            'TransportAttachmentId': 'transport-123',
            'Options': {'Protocol': 'GRE'},
        }
    }

    result = await attachment_module.get_cwan_attachment('attachment-456', 'us-east-1')

    assert result['attachment_type'] == 'CONNECT'
    assert result['attachment']['AttachmentId'] == 'attachment-456'
    assert result['connect_specific']['transport_attachment_id'] == 'transport-123'
    assert result['connect_specific']['options']['Protocol'] == 'GRE'


@patch.object(attachment_module, 'get_aws_client')
async def test_direct_connect_gateway_attachment_success(mock_get_client):
    """Test successful Direct Connect Gateway attachment retrieval."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {}
    mock_client.get_connect_attachment.return_value = {}
    mock_client.get_direct_connect_gateway_attachment.return_value = {
        'DirectConnectGatewayAttachment': {
            'Attachment': {'AttachmentId': 'attachment-789'},
            'DirectConnectGatewayArn': 'arn:aws:directconnect:us-east-1:123456789012:dx-gateway/dx-gw-123',
        }
    }

    result = await attachment_module.get_cwan_attachment('attachment-789', 'us-east-1')

    assert result['attachment_type'] == 'DIRECT_CONNECT_GATEWAY'
    assert result['attachment']['AttachmentId'] == 'attachment-789'
    assert (
        result['direct_connect_specific']['direct_connect_gateway_arn']
        == 'arn:aws:directconnect:us-east-1:123456789012:dx-gateway/dx-gw-123'
    )


@patch.object(attachment_module, 'get_aws_client')
async def test_site_to_site_vpn_attachment_success(mock_get_client):
    """Test successful Site-to-Site VPN attachment retrieval."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {}
    mock_client.get_connect_attachment.return_value = {}
    mock_client.get_direct_connect_gateway_attachment.return_value = {}
    mock_client.get_site_to_site_vpn_attachment.return_value = {
        'SiteToSiteVpnAttachment': {
            'Attachment': {'AttachmentId': 'attachment-vpn'},
            'VpnConnectionArn': 'arn:aws:ec2:us-east-1:123456789012:vpn-connection/vpn-123',
        }
    }

    result = await attachment_module.get_cwan_attachment('attachment-vpn', 'us-east-1')

    assert result['attachment_type'] == 'SITE_TO_SITE_VPN'
    assert result['attachment']['AttachmentId'] == 'attachment-vpn'
    assert (
        result['vpn_specific']['vpn_connection_arn']
        == 'arn:aws:ec2:us-east-1:123456789012:vpn-connection/vpn-123'
    )


@patch.object(attachment_module, 'get_aws_client')
async def test_transit_gateway_route_table_attachment_success(mock_get_client):
    """Test successful Transit Gateway Route Table attachment retrieval."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {}
    mock_client.get_connect_attachment.return_value = {}
    mock_client.get_direct_connect_gateway_attachment.return_value = {}
    mock_client.get_site_to_site_vpn_attachment.return_value = {}
    mock_client.get_transit_gateway_route_table_attachment.return_value = {
        'TransitGatewayRouteTableAttachment': {
            'Attachment': {'AttachmentId': 'attachment-tgw'},
            'PeeringId': 'peering-123',
            'TransitGatewayRouteTableArn': 'arn:aws:ec2:us-east-1:123456789012:transit-gateway-route-table/tgw-rtb-123',
        }
    }

    result = await attachment_module.get_cwan_attachment('attachment-tgw', 'us-east-1')

    assert result['attachment_type'] == 'TRANSIT_GATEWAY_ROUTE_TABLE'
    assert result['attachment']['AttachmentId'] == 'attachment-tgw'
    assert result['transit_gateway_specific']['peering_id'] == 'peering-123'
    assert (
        result['transit_gateway_specific']['transit_gateway_route_table_arn']
        == 'arn:aws:ec2:us-east-1:123456789012:transit-gateway-route-table/tgw-rtb-123'
    )


@patch.object(attachment_module, 'get_aws_client')
async def test_attachment_not_found(mock_get_client):
    """Test attachment not found error."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {}
    mock_client.get_connect_attachment.return_value = {}
    mock_client.get_direct_connect_gateway_attachment.return_value = {}
    mock_client.get_site_to_site_vpn_attachment.return_value = {}
    mock_client.get_transit_gateway_route_table_attachment.return_value = {}

    with pytest.raises(ToolError) as exc_info:
        await attachment_module.get_cwan_attachment('invalid-attachment', 'us-east-1')

    assert 'Attachment invalid-attachment not found or unsupported attachment type' in str(
        exc_info.value
    )


@patch.object(attachment_module, 'get_aws_client')
async def test_with_profile_name(mock_get_client):
    """Test function with custom profile name."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {
        'VpcAttachment': {
            'Attachment': {'AttachmentId': 'attachment-123'},
            'SubnetArns': ['arn:aws:ec2:us-east-1:123456789012:subnet/subnet-123'],
        }
    }

    await attachment_module.get_cwan_attachment('attachment-123', 'us-east-1', 'custom-profile')

    mock_get_client.assert_called_with('networkmanager', 'us-east-1', 'custom-profile')


@patch.object(attachment_module, 'get_aws_client')
async def test_vpc_attachment_with_missing_optional_fields(mock_get_client):
    """Test VPC attachment with missing optional fields."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_vpc_attachment.return_value = {
        'VpcAttachment': {'Attachment': {'AttachmentId': 'attachment-123'}}
    }

    result = await attachment_module.get_cwan_attachment('attachment-123', 'us-east-1')

    assert result['attachment_type'] == 'VPC'
    assert result['vpc_specific']['subnet_arns'] is None
    assert result['vpc_specific']['options'] is None
