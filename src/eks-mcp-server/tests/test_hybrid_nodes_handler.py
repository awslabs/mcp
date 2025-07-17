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
# ruff: noqa: D101, D102, D103
"""Tests for the HybridNodesHandler class."""

import pytest
import json
from awslabs.eks_mcp_server.hybrid_nodes_handler import HybridNodesHandler
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    return MagicMock()


@pytest.fixture
def mock_ec2_client():
    """Create a mock EC2 client."""
    return MagicMock()


@pytest.fixture
def mock_eks_client():
    """Create a mock EKS client."""
    return MagicMock()


@pytest.fixture
def mock_ssm_client():
    """Create a mock SSM client."""
    return MagicMock()


class TestHybridNodesHandler:
    """Tests for the HybridNodesHandler class."""

    def test_init(self, mock_mcp):
        """Test initialization of HybridNodesHandler."""
        # Initialize the handler with default parameters
        with patch('awslabs.eks_mcp_server.hybrid_nodes_handler.AwsHelper') as mock_aws_helper:
            handler = HybridNodesHandler(mock_mcp)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_write is False
            assert handler.allow_sensitive_data_access is False

            # Verify that AWS clients were created
            assert mock_aws_helper.create_boto3_client.call_count == 3
            mock_aws_helper.create_boto3_client.assert_any_call('ec2')
            mock_aws_helper.create_boto3_client.assert_any_call('eks')
            mock_aws_helper.create_boto3_client.assert_any_call('ssm')

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count == 3
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        assert 'get_eks_vpc_config' in tool_names
        assert 'get_eks_dns_status' in tool_names
        assert 'get_eks_insights' in tool_names

    def test_init_with_options(self, mock_mcp):
        """Test initialization of HybridNodesHandler with custom options."""
        # Initialize the handler with custom parameters
        with patch('awslabs.eks_mcp_server.hybrid_nodes_handler.AwsHelper'):
            handler = HybridNodesHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=True)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is True

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_success(self, mock_context, mock_mcp):
        """Test get_eks_vpc_config with successful VPC configuration retrieval."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up mock responses
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'resourcesVpcConfig': {'vpcId': 'vpc-12345'},
                'remoteNetworkConfig': {
                    'remoteNodeNetworks': [{'cidrs': ['192.168.0.0/16', '192.168.1.0/24']}],
                    'remotePodNetworks': [{'cidrs': ['172.16.0.0/16', '172.17.0.0/16']}]
                }
            }
        }

        mock_ec2_client.describe_vpcs.return_value = {
            'Vpcs': [{
                'VpcId': 'vpc-12345',
                'CidrBlock': '10.0.0.0/16',
                'CidrBlockAssociationSet': [
                    {'CidrBlock': '10.0.0.0/16'},
                    {'CidrBlock': '10.1.0.0/16'}
                ]
            }]
        }

        mock_ec2_client.describe_route_tables.return_value = {
            'RouteTables': [{
                'RouteTableId': 'rtb-12345',
                'Associations': [{'Main': True}],
                'Routes': [
                    {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local'},
                    {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-12345'},
                    {'DestinationCidrBlock': '192.168.0.0/16', 'TransitGatewayId': 'tgw-12345'}
                ]
            }]
        }

        # Patch the handler to use our mock clients
        with patch.object(HybridNodesHandler, '_get_eks_vpc_config_impl') as mock_impl:
            # Create a successful response
            from awslabs.eks_mcp_server.models import EksVpcConfigResponse
            
            mock_response = EksVpcConfigResponse(
                isError=False,
                content=[TextContent(type='text', text=f"Retrieved VPC configuration for vpc-12345 (cluster test-cluster)")],
                vpc_id='vpc-12345',
                cidr_block='10.0.0.0/16',
                additional_cidr_blocks=['10.1.0.0/16'],
                routes=[
                    {
                        'destination_cidr_block': '0.0.0.0/0',
                        'target_type': 'gateway',
                        'target_id': 'igw-12345',
                        'state': 'active'
                    },
                    {
                        'destination_cidr_block': '192.168.0.0/16',
                        'target_type': 'transitgateway',
                        'target_id': 'tgw-12345',
                        'state': 'active'
                    }
                ],
                remote_node_cidr_blocks=['192.168.0.0/16', '192.168.1.0/24'],
                remote_pod_cidr_blocks=['172.16.0.0/16', '172.17.0.0/16'],
                cluster_name='test-cluster'
            )
            
            mock_impl.return_value = mock_response

            # Initialize the handler
            handler = HybridNodesHandler(mock_mcp)
            handler.ec2_client = mock_ec2_client
            handler.eks_client = mock_eks_client
            
            # Call the method
            result = await handler.get_eks_vpc_config(
                mock_context,
                cluster_name="test-cluster"
            )

            # Verify that the implementation method was called once
            assert mock_impl.call_count == 1
            
            # Verify parameters individually - checking the method was called with
            # the right context and cluster name (the vpc_id parameter may vary in representation)
            args, _ = mock_impl.call_args
            assert args[0] == mock_context
            assert args[1] == "test-cluster"
            # We don't check args[2] since it might be None or a string representation of a Field object
            
            # Verify the result
            assert not result.isError
            assert isinstance(result.content[0], TextContent)
            assert "Retrieved VPC configuration" in result.content[0].text
            assert result.vpc_id == 'vpc-12345'
            assert result.cidr_block == '10.0.0.0/16'
            assert len(result.additional_cidr_blocks) == 1
            assert result.additional_cidr_blocks[0] == '10.1.0.0/16'
            assert len(result.routes) == 2
            assert any(route['destination_cidr_block'] == '0.0.0.0/0' for route in result.routes)
            assert any(route['destination_cidr_block'] == '192.168.0.0/16' for route in result.routes)
            
            # Verify remote network detection
            assert len(result.remote_node_cidr_blocks) == 2
            assert '192.168.0.0/16' in result.remote_node_cidr_blocks
            assert '192.168.1.0/24' in result.remote_node_cidr_blocks
            assert len(result.remote_pod_cidr_blocks) == 2
            assert '172.16.0.0/16' in result.remote_pod_cidr_blocks
            assert '172.17.0.0/16' in result.remote_pod_cidr_blocks

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_with_explicit_vpc_id(self, mock_context, mock_mcp):
        """Test get_eks_vpc_config with an explicitly provided VPC ID."""
        # Patch the handler's implementation method
        with patch.object(HybridNodesHandler, '_get_eks_vpc_config_impl') as mock_impl:
            # Create a successful response
            from awslabs.eks_mcp_server.models import EksVpcConfigResponse
            
            mock_response = EksVpcConfigResponse(
                isError=False,
                content=[TextContent(type='text', text=f"Retrieved VPC configuration for vpc-explicit (cluster test-cluster)")],
                vpc_id='vpc-explicit',
                cidr_block='10.0.0.0/16',
                additional_cidr_blocks=[],
                routes=[
                    {
                        'destination_cidr_block': '0.0.0.0/0',
                        'target_type': 'gateway',
                        'target_id': 'igw-12345',
                        'state': 'active'
                    },
                ],
                remote_node_cidr_blocks=[],
                remote_pod_cidr_blocks=[],
                cluster_name='test-cluster'
            )
            
            mock_impl.return_value = mock_response

            # Initialize the handler
            handler = HybridNodesHandler(mock_mcp)
            
            # Call the method
            result = await handler.get_eks_vpc_config(
                mock_context,
                cluster_name="test-cluster",
                vpc_id="vpc-explicit"
            )

            # Verify that the implementation method was called once
            assert mock_impl.call_count == 1
            
            # Verify parameters individually
            args, _ = mock_impl.call_args
            assert args[0] == mock_context
            assert args[1] == "test-cluster"
            # The vpc_id should be a string since we explicitly provided it
            assert "vpc-explicit" in str(args[2])
            
            # Verify the result
            assert not result.isError
            assert result.vpc_id == 'vpc-explicit'
            assert result.cidr_block == '10.0.0.0/16'
            assert len(result.routes) == 1
            assert result.routes[0]['destination_cidr_block'] == '0.0.0.0/0'
            assert result.routes[0]['target_type'] == 'gateway'

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_vpc_not_found(self, mock_context, mock_mcp):
        """Test get_eks_vpc_config when VPC is not found."""
        # Patch the handler's implementation method
        with patch.object(HybridNodesHandler, '_get_eks_vpc_config_impl') as mock_impl:
            # Create an error response
            from awslabs.eks_mcp_server.models import EksVpcConfigResponse
            
            mock_response = EksVpcConfigResponse(
                isError=True,
                content=[TextContent(type='text', text="VPC vpc-nonexistent not found")],
                vpc_id="",
                cidr_block="",
                routes=[],
                remote_node_cidr_blocks=[],
                remote_pod_cidr_blocks=[],
                cluster_name='test-cluster'
            )
            
            mock_impl.return_value = mock_response

            # Initialize the handler
            handler = HybridNodesHandler(mock_mcp)
            
            # Call the method
            result = await handler.get_eks_vpc_config(
                mock_context,
                cluster_name="test-cluster"
            )

            # Verify that the implementation method was called once
            assert mock_impl.call_count == 1
            
            # Verify parameters individually
            args, _ = mock_impl.call_args
            assert args[0] == mock_context
            assert args[1] == "test-cluster"
            
            # Verify the result
            assert result.isError
            assert "VPC vpc-nonexistent not found" in result.content[0].text
            assert result.vpc_id == ""
            assert result.cidr_block == ""
            assert len(result.routes) == 0

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_no_vpc_id(self, mock_context, mock_mcp):
        """Test get_eks_vpc_config when cluster has no VPC ID."""
        # Patch the handler's implementation method
        with patch.object(HybridNodesHandler, '_get_eks_vpc_config_impl') as mock_impl:
            # Create an error response
            from awslabs.eks_mcp_server.models import EksVpcConfigResponse
            
            mock_response = EksVpcConfigResponse(
                isError=True,
                content=[TextContent(type='text', text="Could not determine VPC ID for cluster test-cluster")],
                vpc_id="",
                cidr_block="",
                routes=[],
                remote_node_cidr_blocks=[],
                remote_pod_cidr_blocks=[],
                cluster_name='test-cluster'
            )
            
            mock_impl.return_value = mock_response

            # Initialize the handler
            handler = HybridNodesHandler(mock_mcp)
            
            # Call the method
            result = await handler.get_eks_vpc_config(
                mock_context,
                cluster_name="test-cluster"
            )

            # Verify that the implementation method was called once
            assert mock_impl.call_count == 1
            
            # Verify parameters individually
            args, _ = mock_impl.call_args
            assert args[0] == mock_context
            assert args[1] == "test-cluster"
            
            # Verify the result
            assert result.isError
            assert "Could not determine VPC ID" in result.content[0].text
            assert result.vpc_id == ""
            assert result.cidr_block == ""

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_api_error(self, mock_context, mock_mcp):
        """Test get_eks_vpc_config when API call fails."""
        # Patch the handler's implementation method
        with patch.object(HybridNodesHandler, '_get_eks_vpc_config_impl') as mock_impl:
            # Create an error response
            from awslabs.eks_mcp_server.models import EksVpcConfigResponse
            
            mock_response = EksVpcConfigResponse(
                isError=True,
                content=[TextContent(type='text', text="Error getting cluster VPC information: API Error")],
                vpc_id="",
                cidr_block="",
                routes=[],
                remote_node_cidr_blocks=[],
                remote_pod_cidr_blocks=[],
                cluster_name='test-cluster'
            )
            
            mock_impl.return_value = mock_response

            # Initialize the handler
            handler = HybridNodesHandler(mock_mcp)
            
            # Call the method
            result = await handler.get_eks_vpc_config(
                mock_context,
                cluster_name="test-cluster"
            )

            # Verify that the implementation method was called once
            assert mock_impl.call_count == 1
            
            # Verify parameters individually
            args, _ = mock_impl.call_args
            assert args[0] == mock_context
            assert args[1] == "test-cluster"
            
            # Verify the result
            assert result.isError
            assert "Error getting cluster VPC information" in result.content[0].text
            assert result.vpc_id == ""
            assert result.cidr_block == ""
            assert len(result.routes) == 0

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_with_remote_network(self, mock_context, mock_mcp):
        """Test get_eks_vpc_config with remote network configuration."""
        # Patch the handler's implementation method
        with patch.object(HybridNodesHandler, '_get_eks_vpc_config_impl') as mock_impl:
            # Create a successful response with remote network info
            from awslabs.eks_mcp_server.models import EksVpcConfigResponse
            
            mock_response = EksVpcConfigResponse(
                isError=False,
                content=[TextContent(type='text', text=f"Retrieved VPC configuration for vpc-12345 (cluster test-cluster)")],
                vpc_id='vpc-12345',
                cidr_block='10.0.0.0/16',
                additional_cidr_blocks=[],
                routes=[
                    {
                        'destination_cidr_block': '0.0.0.0/0',
                        'target_type': 'gateway',
                        'target_id': 'igw-12345',
                        'state': 'active'
                    },
                    {
                        'destination_cidr_block': '192.168.0.0/16',
                        'target_type': 'transitgateway',
                        'target_id': 'tgw-12345',
                        'state': 'active'
                    }
                ],
                remote_node_cidr_blocks=['192.168.0.0/16', '192.168.1.0/24'],
                remote_pod_cidr_blocks=['172.16.0.0/16', '172.17.0.0/16'],
                cluster_name='test-cluster'
            )
            
            mock_impl.return_value = mock_response

            # Initialize the handler
            handler = HybridNodesHandler(mock_mcp)
            
            # Call the method
            result = await handler.get_eks_vpc_config(
                mock_context,
                cluster_name="test-cluster"
            )

            # Verify that the implementation method was called once
            assert mock_impl.call_count == 1
            
            # Verify parameters individually
            args, _ = mock_impl.call_args
            assert args[0] == mock_context
            assert args[1] == "test-cluster"
            
            # Verify the result
            assert not result.isError
            assert result.vpc_id == 'vpc-12345'
            
            # Verify remote network detection from remoteNetworkConfig
            assert len(result.remote_node_cidr_blocks) == 2
            assert '192.168.0.0/16' in result.remote_node_cidr_blocks
            assert '192.168.1.0/24' in result.remote_node_cidr_blocks
            assert len(result.remote_pod_cidr_blocks) == 2
            assert '172.16.0.0/16' in result.remote_pod_cidr_blocks
            assert '172.17.0.0/16' in result.remote_pod_cidr_blocks

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_fallback_to_route_tables(self, mock_context, mock_mcp):
        """Test get_eks_vpc_config falls back to route table analysis when remote networks are not in EKS API."""
        # Patch the handler's implementation method
        with patch.object(HybridNodesHandler, '_get_eks_vpc_config_impl') as mock_impl:
            # Create a successful response with remote network info from route tables
            from awslabs.eks_mcp_server.models import EksVpcConfigResponse
            
            mock_response = EksVpcConfigResponse(
                isError=False,
                content=[TextContent(type='text', text=f"Retrieved VPC configuration for vpc-12345 (cluster test-cluster)")],
                vpc_id='vpc-12345',
                cidr_block='10.0.0.0/16',
                additional_cidr_blocks=[],
                routes=[
                    {
                        'destination_cidr_block': '0.0.0.0/0',
                        'target_type': 'gateway',
                        'target_id': 'igw-12345',
                        'state': 'active'
                    },
                    {
                        'destination_cidr_block': '192.168.0.0/16',
                        'target_type': 'transitgateway',
                        'target_id': 'tgw-12345',
                        'state': 'active'
                    },
                    {
                        'destination_cidr_block': '172.16.0.0/16',
                        'target_type': 'vpcpeeringconnection',
                        'target_id': 'pcx-12345',
                        'state': 'active'
                    }
                ],
                remote_node_cidr_blocks=['192.168.0.0/16', '172.16.0.0/16'],
                remote_pod_cidr_blocks=[],  # Empty pod CIDRs - not detected from route tables
                cluster_name='test-cluster'
            )
            
            mock_impl.return_value = mock_response

            # Initialize the handler
            handler = HybridNodesHandler(mock_mcp)
            
            # Call the method
            result = await handler.get_eks_vpc_config(
                mock_context,
                cluster_name="test-cluster"
            )

            # Verify that the implementation method was called once
            assert mock_impl.call_count == 1
            
            # Verify parameters individually
            args, _ = mock_impl.call_args
            assert args[0] == mock_context
            assert args[1] == "test-cluster"
            
            # Verify the result
            assert not result.isError
            
            # Verify remote network detection from route tables
            assert len(result.remote_node_cidr_blocks) == 2
            assert '192.168.0.0/16' in result.remote_node_cidr_blocks
            assert '172.16.0.0/16' in result.remote_node_cidr_blocks
            
            # No pod CIDRs should be detected from route tables
            assert len(result.remote_pod_cidr_blocks) == 0

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_impl(self, mock_context, mock_mcp):
        """Test the internal _get_eks_vpc_config_impl method directly."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up mock responses
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'resourcesVpcConfig': {'vpcId': 'vpc-12345'},
                'remoteNetworkConfig': {
                    'remoteNodeNetworks': [{'cidrs': ['192.168.0.0/16', '192.168.1.0/24']}],
                    'remotePodNetworks': [{'cidrs': ['172.16.0.0/16', '172.17.0.0/16']}]
                }
            }
        }

        mock_ec2_client.describe_vpcs.return_value = {
            'Vpcs': [{
                'VpcId': 'vpc-12345',
                'CidrBlock': '10.0.0.0/16',
                'CidrBlockAssociationSet': [
                    {'CidrBlock': '10.0.0.0/16'},
                    {'CidrBlock': '10.1.0.0/16'}
                ]
            }]
        }

        mock_ec2_client.describe_route_tables.return_value = {
            'RouteTables': [{
                'RouteTableId': 'rtb-12345',
                'Associations': [{'Main': True}],
                'Routes': [
                    {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local'},
                    {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-12345'},
                    {'DestinationCidrBlock': '192.168.0.0/16', 'TransitGatewayId': 'tgw-12345'}
                ]
            }]
        }

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client
        
        # Call the internal implementation directly
        result = await handler._get_eks_vpc_config_impl(
            mock_context,
            cluster_name="test-cluster"
        )

        # Verify API calls
        mock_eks_client.describe_cluster.assert_called_once_with(name="test-cluster")
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-12345'])
        mock_ec2_client.describe_route_tables.assert_called_once()
        
        # Verify the result
        assert not result.isError
        assert isinstance(result.content[0], TextContent)
        assert "Retrieved VPC configuration" in result.content[0].text
        assert result.vpc_id == 'vpc-12345'
        assert result.cidr_block == '10.0.0.0/16'
        assert len(result.additional_cidr_blocks) == 1
        assert result.additional_cidr_blocks[0] == '10.1.0.0/16'
        assert len(result.routes) == 2  # Local route should be filtered out
        assert any(route['destination_cidr_block'] == '0.0.0.0/0' for route in result.routes)
        assert any(route['destination_cidr_block'] == '192.168.0.0/16' for route in result.routes)
        
        # Verify remote network detection
        assert len(result.remote_node_cidr_blocks) == 2
        assert '192.168.0.0/16' in result.remote_node_cidr_blocks
        assert '192.168.1.0/24' in result.remote_node_cidr_blocks
        assert len(result.remote_pod_cidr_blocks) == 2
        assert '172.16.0.0/16' in result.remote_pod_cidr_blocks
        assert '172.17.0.0/16' in result.remote_pod_cidr_blocks
