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
from awslabs.eks_mcp_server.hybrid_nodes_handler import HybridNodesHandler
from datetime import datetime
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
        assert mock_mcp.tool.call_count == 2
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        assert 'get_eks_vpc_config' in tool_names
        assert 'get_eks_insights' in tool_names

    def test_init_with_options(self, mock_mcp):
        """Test initialization of HybridNodesHandler with custom options."""
        # Initialize the handler with custom parameters
        with patch('awslabs.eks_mcp_server.hybrid_nodes_handler.AwsHelper'):
            handler = HybridNodesHandler(
                mock_mcp, allow_write=True, allow_sensitive_data_access=True
            )

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is True

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_with_explicit_vpc_id(self, mock_context, mock_mcp):
        """Test _get_eks_vpc_config_impl with an explicitly provided VPC ID."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up EC2 mock response for the explicit VPC ID
        mock_ec2_client.describe_vpcs.return_value = {
            'Vpcs': [
                {
                    'VpcId': 'vpc-explicit',
                    'CidrBlock': '10.0.0.0/16',
                    'CidrBlockAssociationSet': [{'CidrBlock': '10.0.0.0/16'}],
                }
            ]
        }

        # Set up mock response for route tables
        mock_ec2_client.describe_route_tables.return_value = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-explicit',
                    'Associations': [{'Main': True}],
                    'Routes': [
                        {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local'},
                        {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-explicit'},
                    ],
                }
            ]
        }

        # Set up mock response for subnets
        mock_ec2_client.describe_subnets.return_value = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-explicit',
                    'CidrBlock': '10.0.1.0/24',
                    'AvailabilityZone': 'us-west-2a',
                    'AvailabilityZoneId': 'usw2-az1',
                    'AvailableIpAddressCount': 150,
                    'MapPublicIpOnLaunch': True,
                    'AssignIpv6AddressOnCreation': False,
                }
            ]
        }

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method directly with explicit VPC ID
        result = await handler._get_eks_vpc_config_impl(
            mock_context,
            cluster_name='test-cluster',
            vpc_id='vpc-explicit',  # Pass explicit VPC ID
        )

        # Verify the explicit VPC was used
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-explicit'])

        # Verify EKS client was NOT called to look up VPC ID
        mock_eks_client.describe_cluster.assert_not_called()

        # Verify the result
        assert not result.isError
        assert result.vpc_id == 'vpc-explicit'
        assert result.cidr_block == '10.0.0.0/16'
        assert result.cluster_name == 'test-cluster'
        assert len(result.subnets) == 1
        assert result.subnets[0]['subnet_id'] == 'subnet-explicit'

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_vpc_not_found(self, mock_context, mock_mcp):
        """Test _get_eks_vpc_config_impl when VPC is not found."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up EKS mock response with valid VPC ID
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {'resourcesVpcConfig': {'vpcId': 'vpc-nonexistent'}}
        }

        # Set up EC2 mock to return a ClientError (VPC not found)
        error_response = {
            'Error': {'Code': 'InvalidVpcID.NotFound', 'Message': 'VPC vpc-nonexistent not found'}
        }
        mock_ec2_client.describe_vpcs.side_effect = mock_ec2_client.exceptions.ClientError(
            error_response, 'DescribeVpcs'
        )

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify calls
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-nonexistent'])

        # Verify error response
        assert result.isError
        # We're just checking that this is an error response, the specific error message may vary
        # because we're using real exceptions from boto in the handler
        assert 'Error' in result.content[0].text
        assert result.vpc_id == ''
        assert result.cluster_name == 'test-cluster'

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_no_vpc_id(self, mock_context, mock_mcp):
        """Test _get_eks_vpc_config_impl when cluster has no VPC ID."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up EKS mock response with missing VPC ID
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'resourcesVpcConfig': {}  # No VPC ID in response
            }
        }

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method directly
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify EKS client was called
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

        # Verify EC2 client was not called (should fail before this point)
        mock_ec2_client.describe_vpcs.assert_not_called()

        # Verify error response
        assert result.isError
        assert 'Could not determine VPC ID for cluster' in result.content[0].text
        assert result.vpc_id == ''
        assert result.cluster_name == 'test-cluster'

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_api_error(self, mock_context, mock_mcp):
        """Test _get_eks_vpc_config_impl when API call fails."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up EKS client to raise an exception
        mock_eks_client.describe_cluster.side_effect = Exception('API Error')

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method directly
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify EKS client was called
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

        # Verify error response
        assert result.isError
        assert 'Error getting cluster VPC information' in result.content[0].text
        assert 'API Error' in result.content[0].text
        assert result.vpc_id == ''
        assert result.cluster_name == 'test-cluster'

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_with_remote_network(self, mock_context, mock_mcp):
        """Test _get_eks_vpc_config_impl with remote network configuration."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up EKS mock response with remote network config
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'resourcesVpcConfig': {'vpcId': 'vpc-remote'},
                'remoteNetworkConfig': {
                    'remoteNodeNetworks': [{'cidrs': ['192.168.0.0/16', '192.168.1.0/24']}],
                    'remotePodNetworks': [{'cidrs': ['172.16.0.0/16', '172.17.0.0/16']}],
                },
            }
        }

        # Set up EC2 mock responses
        mock_ec2_client.describe_vpcs.return_value = {
            'Vpcs': [
                {
                    'VpcId': 'vpc-remote',
                    'CidrBlock': '10.0.0.0/16',
                    'CidrBlockAssociationSet': [{'CidrBlock': '10.0.0.0/16'}],
                }
            ]
        }

        mock_ec2_client.describe_route_tables.return_value = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-remote',
                    'Associations': [{'Main': True}],
                    'Routes': [
                        {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local'},
                        {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-remote'},
                        {
                            'DestinationCidrBlock': '192.168.0.0/16',
                            'TransitGatewayId': 'tgw-remote',
                        },
                    ],
                }
            ]
        }

        mock_ec2_client.describe_subnets.return_value = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-remote1',
                    'CidrBlock': '10.0.1.0/24',
                    'AvailabilityZone': 'us-west-2a',
                    'AvailabilityZoneId': 'usw2-az1',
                    'AvailableIpAddressCount': 100,
                    'MapPublicIpOnLaunch': False,
                    'AssignIpv6AddressOnCreation': False,
                },
                {
                    'SubnetId': 'subnet-remote2',
                    'CidrBlock': '10.0.2.0/24',
                    'AvailabilityZone': 'us-west-2b',
                    'AvailabilityZoneId': 'usw2-az2',
                    'AvailableIpAddressCount': 5,
                    'MapPublicIpOnLaunch': True,
                    'AssignIpv6AddressOnCreation': False,
                },
            ]
        }

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method directly
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify calls
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-remote'])

        # Verify the result
        assert not result.isError
        assert result.vpc_id == 'vpc-remote'

        # Verify remote network detection
        assert len(result.remote_node_cidr_blocks) == 2
        assert '192.168.0.0/16' in result.remote_node_cidr_blocks
        assert '192.168.1.0/24' in result.remote_node_cidr_blocks
        assert len(result.remote_pod_cidr_blocks) == 2
        assert '172.16.0.0/16' in result.remote_pod_cidr_blocks
        assert '172.17.0.0/16' in result.remote_pod_cidr_blocks

        # Verify subnet information
        assert len(result.subnets) == 2
        assert any(s['subnet_id'] == 'subnet-remote1' for s in result.subnets)
        assert any(s['subnet_id'] == 'subnet-remote2' for s in result.subnets)

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_with_no_pod_networks(self, mock_context, mock_mcp):
        """Test _get_eks_vpc_config_impl when the cluster has node networks but no pod networks."""
        # Create mock AWS clients
        mock_eks_client = MagicMock()
        mock_ec2_client = MagicMock()

        # Set up EKS mock response with node networks but no pod networks
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'resourcesVpcConfig': {'vpcId': 'vpc-nopod'},
                'remoteNetworkConfig': {
                    'remoteNodeNetworks': [{'cidrs': ['192.168.0.0/16', '172.16.0.0/16']}]
                    # No remotePodNetworks field
                },
            }
        }

        # Set up EC2 mock responses
        mock_ec2_client.describe_vpcs.return_value = {
            'Vpcs': [
                {
                    'VpcId': 'vpc-nopod',
                    'CidrBlock': '10.0.0.0/16',
                    'CidrBlockAssociationSet': [{'CidrBlock': '10.0.0.0/16'}],
                }
            ]
        }

        mock_ec2_client.describe_route_tables.return_value = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-nopod',
                    'Associations': [{'Main': True}],
                    'Routes': [
                        {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local'},
                        {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-nopod'},
                        {
                            'DestinationCidrBlock': '192.168.0.0/16',
                            'TransitGatewayId': 'tgw-nopod',
                        },
                        {
                            'DestinationCidrBlock': '172.16.0.0/16',
                            'VpcPeeringConnectionId': 'pcx-nopod',
                        },
                    ],
                }
            ]
        }

        mock_ec2_client.describe_subnets.return_value = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-nopod',
                    'CidrBlock': '10.0.5.0/24',
                    'AvailabilityZone': 'us-west-2a',
                    'AvailabilityZoneId': 'usw2-az1',
                    'AvailableIpAddressCount': 200,
                    'MapPublicIpOnLaunch': False,
                    'AssignIpv6AddressOnCreation': False,
                }
            ]
        }

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method directly
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify calls
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-nopod'])

        # Verify the result
        assert not result.isError
        assert result.vpc_id == 'vpc-nopod'

        # Verify node CIDRs but no pod CIDRs
        assert len(result.remote_node_cidr_blocks) == 2
        assert '192.168.0.0/16' in result.remote_node_cidr_blocks
        assert '172.16.0.0/16' in result.remote_node_cidr_blocks
        assert len(result.remote_pod_cidr_blocks) == 0  # Key test assertion

        # Verify routes for remote connectivity
        assert any(
            r['destination_cidr_block'] == '192.168.0.0/16'
            and r['target_type'] == 'transitgateway'
            for r in result.routes
        )
        assert any(
            r['destination_cidr_block'] == '172.16.0.0/16'
            and r['target_type'] == 'vpcpeeringconnection'
            for r in result.routes
        )

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
                    'remotePodNetworks': [{'cidrs': ['172.16.0.0/16', '172.17.0.0/16']}],
                },
            }
        }

        mock_ec2_client.describe_vpcs.return_value = {
            'Vpcs': [
                {
                    'VpcId': 'vpc-12345',
                    'CidrBlock': '10.0.0.0/16',
                    'CidrBlockAssociationSet': [
                        {'CidrBlock': '10.0.0.0/16'},
                        {'CidrBlock': '10.1.0.0/16'},
                    ],
                }
            ]
        }

        # Mock subnets response
        mock_ec2_client.describe_subnets.return_value = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-12345',
                    'CidrBlock': '10.0.1.0/24',
                    'AvailabilityZone': 'us-west-2a',
                    'AvailabilityZoneId': 'usw2-az1',
                    'AvailableIpAddressCount': 250,
                    'MapPublicIpOnLaunch': False,
                    'AssignIpv6AddressOnCreation': False,
                },
                {
                    'SubnetId': 'subnet-67890',
                    'CidrBlock': '10.0.2.0/24',
                    'AvailabilityZone': 'us-west-2b',
                    'AvailabilityZoneId': 'usw2-az2',
                    'AvailableIpAddressCount': 10,
                    'MapPublicIpOnLaunch': True,
                    'AssignIpv6AddressOnCreation': False,
                },
            ]
        }

        mock_ec2_client.describe_route_tables.return_value = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-12345',
                    'Associations': [{'Main': True}],
                    'Routes': [
                        {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local'},
                        {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-12345'},
                        {
                            'DestinationCidrBlock': '192.168.0.0/16',
                            'TransitGatewayId': 'tgw-12345',
                        },
                    ],
                }
            ]
        }

        # Initialize the handler with our mock clients
        handler = HybridNodesHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the internal implementation method
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify API calls
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-12345'])
        mock_ec2_client.describe_subnets.assert_called_once()
        mock_ec2_client.describe_route_tables.assert_called_once()

        # Verify the result
        assert not result.isError
        assert isinstance(result.content[0], TextContent)
        assert 'Retrieved VPC configuration' in result.content[0].text
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

        # Verify subnet information
        assert len(result.subnets) == 2

        # Check first subnet
        subnet1 = next((s for s in result.subnets if s['subnet_id'] == 'subnet-12345'), None)
        assert subnet1 is not None
        assert subnet1['cidr_block'] == '10.0.1.0/24'
        assert subnet1['az_name'] == 'us-west-2a'
        assert subnet1['available_ips'] == 250
        assert subnet1['is_public'] is False
        assert subnet1['has_sufficient_ips'] is True

        # Check second subnet
        subnet2 = next((s for s in result.subnets if s['subnet_id'] == 'subnet-67890'), None)
        assert subnet2 is not None
        assert subnet2['cidr_block'] == '10.0.2.0/24'
        assert subnet2['az_name'] == 'us-west-2b'
        assert subnet2['available_ips'] == 10
        assert subnet2['is_public'] is True
        assert subnet2['has_sufficient_ips'] is False  # Only 10 IPs, needs 16

    # Tests for get_eks_insights tool
    @staticmethod
    def _create_mock_insight_item(insight_id='test-insight-id', category='CONFIGURATION'):
        """Helper to create a mock insight item for testing."""
        return {
            'id': insight_id,
            'name': f'Test Insight {insight_id}',
            'category': category,
            'kubernetesVersion': '1.27',
            'lastRefreshTime': datetime(2025, 7, 19, 12, 0, 0),
            'lastTransitionTime': datetime(2025, 7, 19, 11, 0, 0),
            'description': 'Test insight description',
            'insightStatus': {'status': 'PASSING', 'reason': 'All conditions are met'},
        }

    @pytest.mark.asyncio
    async def test_get_eks_insights_list_mode(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl in list mode (without an insight_id)."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses for list mode
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(insight_id='insight-1', category='CONFIGURATION'),
                self._create_mock_insight_item(
                    insight_id='insight-2', category='UPGRADE_READINESS'
                ),
            ]
        }

        # Initialize the handler with our mock client
        handler = HybridNodesHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method directly
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify API calls
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify the result
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 2
        assert result.detail_mode is False

        # Verify insight items were properly constructed
        assert result.insights[0].id == 'insight-1'
        assert result.insights[0].category == 'CONFIGURATION'
        assert result.insights[1].id == 'insight-2'
        assert result.insights[1].category == 'UPGRADE_READINESS'

        # Verify success message in content
        assert isinstance(result.content[0], TextContent)
        assert f'Successfully retrieved {len(result.insights)} insights' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_eks_insights_detail_mode(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl in detail mode (with an insight_id)."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses for detail mode
        insight_data = self._create_mock_insight_item(
            insight_id='detail-insight', category='CONFIGURATION'
        )
        insight_data['recommendation'] = 'This is a test recommendation'
        insight_data['additionalInfo'] = {'link': 'https://example.com'}
        insight_data['resources'] = ['resource-1', 'resource-2']
        insight_data['categorySpecificSummary'] = {'detail': 'Some specific details'}

        mock_eks_client.describe_insight.return_value = {'insight': insight_data}

        # Initialize the handler with our mock client
        handler = HybridNodesHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method directly with insight_id
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', insight_id='detail-insight'
        )

        # Verify API calls
        mock_eks_client.describe_insight.assert_called_once_with(
            id='detail-insight', clusterName='test-cluster'
        )

        # Verify the result
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 1
        assert result.detail_mode is True

        # Verify detailed insight properties
        insight = result.insights[0]
        assert insight.id == 'detail-insight'
        assert insight.category == 'CONFIGURATION'
        assert insight.recommendation == 'This is a test recommendation'
        assert insight.additional_info == {'link': 'https://example.com'}
        assert insight.resources == ['resource-1', 'resource-2']
        assert insight.category_specific_summary == {'detail': 'Some specific details'}

        # Verify success message in content
        assert (
            'Successfully retrieved details for insight detail-insight' in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_get_eks_insights_with_category_filter(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl with category filter."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(
                    insight_id='config-insight-1', category='CONFIGURATION'
                ),
                self._create_mock_insight_item(
                    insight_id='config-insight-2', category='CONFIGURATION'
                ),
            ]
        }

        # Initialize the handler with our mock client
        handler = HybridNodesHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method with category filter
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', category='CONFIGURATION'
        )

        # Verify API calls with category filter parameter
        mock_eks_client.list_insights.assert_called_once_with(
            clusterName='test-cluster',
            categories=['CONFIGURATION'],  # Verify category passed to API
        )

        # Verify the result
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 2
        assert all(insight.category == 'CONFIGURATION' for insight in result.insights)

        # Verify success message mentions insights
        assert isinstance(result.content[0], TextContent)
        assert f'Successfully retrieved {len(result.insights)} insights' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_eks_insights_with_region(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl with region parameter."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Setup mock response
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(
                    insight_id='region-insight', category='CONFIGURATION'
                ),
            ]
        }

        # Mock the AWS helper to check region parameter
        with patch('awslabs.eks_mcp_server.hybrid_nodes_handler.AwsHelper') as mock_aws_helper:
            # Set up AwsHelper to return our mock EKS client
            mock_aws_helper.create_boto3_client.return_value = mock_eks_client

            # Initialize the handler without setting eks_client directly
            handler = HybridNodesHandler(mock_mcp)

            # Call the implementation method with region
            result = await handler._get_eks_insights_impl(
                mock_context, cluster_name='test-cluster', region='us-west-2'
            )

            # Verify client was created with region
            mock_aws_helper.create_boto3_client.assert_called_with('eks', region_name='us-west-2')

            # Verify API call was made with our mock client
            mock_eks_client.list_insights.assert_called_once()

            # Verify the result
            assert not result.isError
            assert result.cluster_name == 'test-cluster'
            assert len(result.insights) == 1
            assert result.insights[0].id == 'region-insight'

    @pytest.mark.asyncio
    async def test_get_eks_insights_error_handling(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl when API call fails."""
        # Create mock AWS client that raises an exception
        mock_eks_client = MagicMock()
        mock_eks_client.list_insights.side_effect = Exception('Test API error')

        # Initialize the handler with our mock client
        handler = HybridNodesHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify API call was attempted
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify error response
        assert result.isError
        assert isinstance(result.content[0], TextContent)
        assert 'Error listing insights' in result.content[0].text
        assert 'Test API error' in result.content[0].text
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0

    @pytest.mark.asyncio
    async def test_get_eks_insights_no_insights_found(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl when no insights are found."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock response with no insights
        mock_eks_client.list_insights.return_value = {
            'insights': []  # Empty list
        }

        # Initialize the handler with our mock client
        handler = HybridNodesHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify API call was made
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify appropriate empty response (not an error)
        assert not result.isError
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0
        assert 'Successfully retrieved 0 insights' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_eks_insights_insight_not_found(self, mock_context, mock_mcp):
        """Test _get_eks_insights_impl when a specific insight ID can't be found."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Mock error for non-existent insight
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Insight nonexistent-id not found',
            }
        }
        mock_eks_client.describe_insight.side_effect = (
            mock_eks_client.exceptions.ResourceNotFoundException(error_response, 'DescribeInsight')
        )

        # Initialize the handler with our mock client
        handler = HybridNodesHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method with non-existent ID
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', insight_id='nonexistent-id'
        )

        # Verify API call was attempted
        mock_eks_client.describe_insight.assert_called_once_with(
            id='nonexistent-id', clusterName='test-cluster'
        )

        # Verify error response
        assert result.isError
        assert 'No insight details found for ID nonexistent-id' in result.content[0].text
        assert result.cluster_name == 'test-cluster'
        assert len(result.insights) == 0

    @pytest.mark.asyncio
    async def test_get_eks_insights_impl_direct(self, mock_context, mock_mcp):
        """Test the internal _get_eks_insights_impl method directly."""
        # Create mock AWS client
        mock_eks_client = MagicMock()

        # Set up mock responses for list mode
        mock_eks_client.list_insights.return_value = {
            'insights': [
                self._create_mock_insight_item(insight_id='impl-insight-1'),
                self._create_mock_insight_item(insight_id='impl-insight-2'),
            ]
        }

        # Initialize the handler with our mock client
        handler = HybridNodesHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the implementation method directly in list mode
        result = await handler._get_eks_insights_impl(mock_context, cluster_name='test-cluster')

        # Verify list_insights was called with correct parameters
        mock_eks_client.list_insights.assert_called_once_with(clusterName='test-cluster')

        # Verify the result
        assert not result.isError
        assert len(result.insights) == 2
        assert result.cluster_name == 'test-cluster'
        assert not result.detail_mode

        # Now test with detail mode
        mock_eks_client.describe_insight.return_value = {
            'insight': self._create_mock_insight_item(insight_id='impl-detail-insight')
        }

        # Call the implementation method directly in detail mode
        result = await handler._get_eks_insights_impl(
            mock_context, cluster_name='test-cluster', insight_id='impl-detail-insight'
        )

        # Verify describe_insight was called with correct parameters
        mock_eks_client.describe_insight.assert_called_once_with(
            id='impl-detail-insight', clusterName='test-cluster'
        )

        # Verify the result
        assert not result.isError
        assert len(result.insights) == 1
        assert result.insights[0].id == 'impl-detail-insight'
        assert result.cluster_name == 'test-cluster'
        assert result.detail_mode
