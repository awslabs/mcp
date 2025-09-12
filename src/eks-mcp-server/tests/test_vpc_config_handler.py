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
"""Tests for the VpcConfigHandler class."""

import pytest
from awslabs.eks_mcp_server.vpc_config_handler import VpcConfigHandler
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


class TestVpcConfigHandler:
    """Tests for the VpcConfigHandler class."""

    @pytest.fixture(autouse=True)
    def mock_aws_helper(self, monkeypatch, mock_ec2_client, mock_eks_client):
        """Mock AWS Helper to avoid actual AWS client creation."""

        def mock_create_boto3_client(service_name, region_name=None):
            if service_name == 'ec2':
                return mock_ec2_client
            elif service_name == 'eks':
                return mock_eks_client
            else:
                return MagicMock()

        monkeypatch.setattr(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client',
            mock_create_boto3_client,
        )

    def test_init(self, mock_mcp):
        """Test initialization of VpcConfigHandler."""
        # Initialize the handler with default parameters
        with patch('awslabs.eks_mcp_server.vpc_config_handler.AwsHelper') as mock_aws_helper:
            handler = VpcConfigHandler(mock_mcp)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_sensitive_data_access is False

            # Verify that AWS clients were created
            assert mock_aws_helper.create_boto3_client.call_count == 2
            mock_aws_helper.create_boto3_client.assert_any_call('ec2')
            mock_aws_helper.create_boto3_client.assert_any_call('eks')

        # Verify that the tools were registered
        assert mock_mcp.tool.call_count == 1
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        assert 'get_eks_vpc_config' in tool_names

    def test_init_with_options(self, mock_mcp):
        """Test initialization of VpcConfigHandler with custom options."""
        # Initialize the handler with custom parameters
        with patch('awslabs.eks_mcp_server.vpc_config_handler.AwsHelper'):
            handler = VpcConfigHandler(mock_mcp, allow_sensitive_data_access=True)

            # Verify that the handler has the correct attributes
            assert handler.mcp == mock_mcp
            assert handler.allow_sensitive_data_access is True

    @pytest.mark.asyncio
    async def test_get_eks_vpc_config_with_explicit_vpc_id(self, mock_context, mock_mcp):
        """Test _get_eks_vpc_config_impl with an explicitly provided VPC ID.

        When a VPC ID is explicitly provided, we should:
        1. Use the provided VPC ID directly without looking it up from the cluster
        2. Still retrieve remote CIDR information by calling describe_cluster
        """
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

        # Set up mock response for EKS client (for remote CIDR information)
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'resourcesVpcConfig': {'vpcId': 'vpc-explicit'},  # Include VPC ID in response
                # No remote network config in this test
            }
        }

        # Initialize the handler with our mock clients
        handler = VpcConfigHandler(mock_mcp)
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

        # Verify EKS client was called once to get remote CIDR information
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

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
        handler = VpcConfigHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify calls
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-nonexistent'])

        # Verify error response
        assert result.isError
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
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
        handler = VpcConfigHandler(mock_mcp)
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
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
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
        handler = VpcConfigHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client
        handler.eks_client = mock_eks_client

        # Call the implementation method directly
        result = await handler._get_eks_vpc_config_impl(mock_context, cluster_name='test-cluster')

        # Verify EKS client was called
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

        # Verify error response
        assert result.isError
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
        assert 'Error getting cluster information' in result.content[0].text
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
        handler = VpcConfigHandler(mock_mcp)
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
        handler = VpcConfigHandler(mock_mcp)
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
        handler = VpcConfigHandler(mock_mcp)
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
        assert isinstance(
            result.content[0], TextContent
        )  # Ensure it's TextContent before accessing .text
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

    @pytest.mark.asyncio
    async def test_get_vpc_id_for_cluster_success(self, mock_context, mock_mcp):
        """Test _get_vpc_id_for_cluster when successful."""
        # Create mock EKS client
        mock_eks_client = MagicMock()

        # Set up mock response with VPC ID
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {'resourcesVpcConfig': {'vpcId': 'vpc-12345'}}
        }

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the helper method
        vpc_id, cluster_response = await handler._get_vpc_id_for_cluster(
            mock_context, 'test-cluster'
        )

        # Verify EKS client was called
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

        # Verify the result
        assert vpc_id == 'vpc-12345'
        assert cluster_response == mock_eks_client.describe_cluster.return_value

    @pytest.mark.asyncio
    async def test_get_vpc_id_for_cluster_no_vpc_id(self, mock_context, mock_mcp):
        """Test _get_vpc_id_for_cluster when no VPC ID is found."""
        # Create mock EKS client
        mock_eks_client = MagicMock()

        # Set up mock response without VPC ID
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {
                'resourcesVpcConfig': {}  # No VPC ID
            }
        }

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the helper method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await handler._get_vpc_id_for_cluster(mock_context, 'test-cluster')

        # Verify EKS client was called
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

        # Verify the exception message
        assert 'Could not determine VPC ID for cluster' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_vpc_id_for_cluster_api_error(self, mock_context, mock_mcp):
        """Test _get_vpc_id_for_cluster when API call fails."""
        # Create mock EKS client
        mock_eks_client = MagicMock()

        # Set up mock to raise an exception
        mock_eks_client.describe_cluster.side_effect = Exception('API Error')

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the helper method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await handler._get_vpc_id_for_cluster(mock_context, 'test-cluster')

        # Verify EKS client was called
        mock_eks_client.describe_cluster.assert_called_once_with(name='test-cluster')

        # Verify the exception message
        assert 'API Error' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_vpc_details_success(self, mock_context, mock_mcp):
        """Test _get_vpc_details when successful."""
        # Create mock EC2 client
        mock_ec2_client = MagicMock()

        # Set up mock response
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

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client

        # Call the helper method
        cidr_block, additional_cidr_blocks = await handler._get_vpc_details(
            mock_context, 'vpc-12345'
        )

        # Verify EC2 client was called
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-12345'])

        # Verify the result
        assert cidr_block == '10.0.0.0/16'
        assert len(additional_cidr_blocks) == 1
        assert additional_cidr_blocks[0] == '10.1.0.0/16'

    @pytest.mark.asyncio
    async def test_get_vpc_details_vpc_not_found(self, mock_context, mock_mcp):
        """Test _get_vpc_details when VPC is not found."""
        # Create mock EC2 client
        mock_ec2_client = MagicMock()

        # Set up mock response with no VPCs
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client

        # Call the helper method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await handler._get_vpc_details(mock_context, 'vpc-nonexistent')

        # Verify EC2 client was called
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-nonexistent'])

        # Verify the exception message
        assert 'VPC vpc-nonexistent not found' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_vpc_details_api_error(self, mock_context, mock_mcp):
        """Test _get_vpc_details when API call fails."""
        # Create mock EC2 client
        mock_ec2_client = MagicMock()

        # Set up mock to raise an exception
        mock_ec2_client.describe_vpcs.side_effect = Exception('API Error')

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client

        # Call the helper method and expect an exception
        with pytest.raises(Exception) as excinfo:
            await handler._get_vpc_details(mock_context, 'vpc-12345')

        # Verify EC2 client was called
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-12345'])

        # Verify the exception message
        assert 'API Error' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_subnet_information(self, mock_context, mock_mcp):
        """Test _get_subnet_information."""
        # Create mock EC2 client
        mock_ec2_client = MagicMock()

        # Set up mock response
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
                    'AssignIpv6AddressOnCreation': True,
                },
                {
                    'SubnetId': 'subnet-disallowed',
                    'CidrBlock': '10.0.3.0/24',
                    'AvailabilityZone': 'us-east-1c',
                    'AvailabilityZoneId': 'use1-az3',  # Disallowed AZ
                    'AvailableIpAddressCount': 100,
                    'MapPublicIpOnLaunch': False,
                    'AssignIpv6AddressOnCreation': False,
                },
            ]
        }

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client

        # Call the helper method
        subnets = await handler._get_subnet_information(mock_context, 'vpc-12345')

        # Verify EC2 client was called
        mock_ec2_client.describe_subnets.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': ['vpc-12345']}]
        )

        # Verify the result
        assert len(subnets) == 3

        # Check first subnet
        subnet1 = next((s for s in subnets if s['subnet_id'] == 'subnet-12345'), None)
        assert subnet1 is not None
        assert subnet1['cidr_block'] == '10.0.1.0/24'
        assert subnet1['az_name'] == 'us-west-2a'
        assert subnet1['available_ips'] == 250
        assert subnet1['is_public'] is False
        assert subnet1['assign_ipv6'] is False
        assert subnet1['has_sufficient_ips'] is True
        assert subnet1['in_disallowed_az'] is False

        # Check second subnet
        subnet2 = next((s for s in subnets if s['subnet_id'] == 'subnet-67890'), None)
        assert subnet2 is not None
        assert subnet2['cidr_block'] == '10.0.2.0/24'
        assert subnet2['az_name'] == 'us-west-2b'
        assert subnet2['available_ips'] == 10
        assert subnet2['is_public'] is True
        assert subnet2['assign_ipv6'] is True
        assert subnet2['has_sufficient_ips'] is False  # Only 10 IPs, needs 16
        assert subnet2['in_disallowed_az'] is False

        # Check disallowed AZ subnet
        subnet3 = next((s for s in subnets if s['subnet_id'] == 'subnet-disallowed'), None)
        assert subnet3 is not None
        assert subnet3['az_id'] == 'use1-az3'
        assert subnet3['in_disallowed_az'] is True

    @pytest.mark.asyncio
    async def test_get_route_table_information(self, mock_context, mock_mcp):
        """Test _get_route_table_information."""
        # Create mock EC2 client
        mock_ec2_client = MagicMock()

        # Set up mock response
        mock_ec2_client.describe_route_tables.return_value = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-12345',
                    'Associations': [{'Main': True}],  # Main route table
                    'Routes': [
                        {
                            'DestinationCidrBlock': '10.0.0.0/16',
                            'GatewayId': 'local',
                        },  # Local route
                        {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-12345'},
                        {
                            'DestinationCidrBlock': '192.168.0.0/16',
                            'TransitGatewayId': 'tgw-12345',
                        },
                        {'DestinationCidrBlock': '172.16.0.0/16', 'NatGatewayId': 'nat-12345'},
                        {
                            'DestinationCidrBlock': '10.1.0.0/16',
                            'VpcPeeringConnectionId': 'pcx-12345',
                        },
                        {'DestinationCidrBlock': '10.2.0.0/16', 'NetworkInterfaceId': 'eni-12345'},
                        {'DestinationCidrBlock': '10.3.0.0/16'},  # No target
                    ],
                },
                {
                    'RouteTableId': 'rtb-67890',
                    'Associations': [{'Main': False}],  # Not main route table
                    'Routes': [
                        {'DestinationCidrBlock': '10.0.0.0/16', 'GatewayId': 'local'},
                        {'DestinationCidrBlock': '0.0.0.0/0', 'GatewayId': 'igw-67890'},
                    ],
                },
            ]
        }

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.ec2_client = mock_ec2_client

        # Call the helper method
        routes = await handler._get_route_table_information(mock_context, 'vpc-12345')

        # Verify EC2 client was called
        mock_ec2_client.describe_route_tables.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': ['vpc-12345']}]
        )

        # Verify the result
        assert len(routes) == 6  # Local route should be filtered out

        # Check routes
        assert any(
            r['destination_cidr_block'] == '0.0.0.0/0' and r['target_type'] == 'gateway'
            for r in routes
        )
        assert any(
            r['destination_cidr_block'] == '192.168.0.0/16'
            and r['target_type'] == 'transitgateway'
            for r in routes
        )
        assert any(
            r['destination_cidr_block'] == '172.16.0.0/16' and r['target_type'] == 'natgateway'
            for r in routes
        )
        assert any(
            r['destination_cidr_block'] == '10.1.0.0/16'
            and r['target_type'] == 'vpcpeeringconnection'
            for r in routes
        )
        assert any(
            r['destination_cidr_block'] == '10.2.0.0/16' and r['target_type'] == 'networkinterface'
            for r in routes
        )
        assert any(
            r['destination_cidr_block'] == '10.3.0.0/16' and r['target_type'] == 'unknown'
            for r in routes
        )

        # Verify that routes from non-main route table are not included
        assert not any(
            r['destination_cidr_block'] == '0.0.0.0/0' and r['target_id'] == 'igw-67890'
            for r in routes
        )

    @pytest.mark.asyncio
    async def test_get_remote_cidr_blocks_with_cluster_response(self, mock_context, mock_mcp):
        """Test _get_remote_cidr_blocks with a provided cluster response."""
        # Create mock cluster response with remote network config
        cluster_response = {
            'cluster': {
                'remoteNetworkConfig': {
                    'remoteNodeNetworks': [{'cidrs': ['192.168.0.0/16', '192.168.1.0/24']}],
                    'remotePodNetworks': [{'cidrs': ['172.16.0.0/16', '172.17.0.0/16']}],
                },
            }
        }

        # Initialize the handler
        handler = VpcConfigHandler(mock_mcp)

        # Call the helper method
        remote_node_cidr_blocks, remote_pod_cidr_blocks = await handler._get_remote_cidr_blocks(
            mock_context, 'test-cluster', cluster_response
        )

        # Verify the result
        assert len(remote_node_cidr_blocks) == 2
        assert '192.168.0.0/16' in remote_node_cidr_blocks
        assert '192.168.1.0/24' in remote_node_cidr_blocks

        assert len(remote_pod_cidr_blocks) == 2
        assert '172.16.0.0/16' in remote_pod_cidr_blocks
        assert '172.17.0.0/16' in remote_pod_cidr_blocks

    @pytest.mark.asyncio
    async def test_get_remote_cidr_blocks_without_cluster_response(self, mock_context, mock_mcp):
        """Test _get_remote_cidr_blocks without a provided cluster response."""
        # Create mock EKS client
        mock_eks_client = MagicMock()

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the helper method with no cluster response
        remote_node_cidr_blocks, remote_pod_cidr_blocks = await handler._get_remote_cidr_blocks(
            mock_context, 'test-cluster'
        )

        # when cluster_response is None, it just returns empty lists
        mock_eks_client.describe_cluster.assert_not_called()

        # Verify the result (should be empty lists)
        assert len(remote_node_cidr_blocks) == 0
        assert len(remote_pod_cidr_blocks) == 0

    @pytest.mark.asyncio
    async def test_get_remote_cidr_blocks_with_empty_cluster_response(
        self, mock_context, mock_mcp
    ):
        """Test _get_remote_cidr_blocks with a cluster response that has no remote network config."""
        # Create mock cluster response without remote network config
        cluster_response = {
            'cluster': {
                # No remoteNetworkConfig
            }
        }

        # Initialize the handler
        handler = VpcConfigHandler(mock_mcp)

        # Call the helper method
        remote_node_cidr_blocks, remote_pod_cidr_blocks = await handler._get_remote_cidr_blocks(
            mock_context, 'test-cluster', cluster_response
        )

        # Verify the result
        assert len(remote_node_cidr_blocks) == 0
        assert len(remote_pod_cidr_blocks) == 0

    @pytest.mark.asyncio
    async def test_get_remote_cidr_blocks_api_error(self, mock_context, mock_mcp):
        """Test _get_remote_cidr_blocks when API call fails."""
        # Create mock EKS client
        mock_eks_client = MagicMock()

        # Set up mock to raise an exception
        mock_eks_client.describe_cluster.side_effect = Exception('API Error')

        # Initialize the handler with our mock client
        handler = VpcConfigHandler(mock_mcp)
        handler.eks_client = mock_eks_client

        # Call the helper method
        remote_node_cidr_blocks, remote_pod_cidr_blocks = await handler._get_remote_cidr_blocks(
            mock_context, 'test-cluster'
        )

        # when cluster_response is None, it just returns empty lists
        mock_eks_client.describe_cluster.assert_not_called()

        # Verify the result (should be empty lists)
        assert len(remote_node_cidr_blocks) == 0
        assert len(remote_pod_cidr_blocks) == 0
