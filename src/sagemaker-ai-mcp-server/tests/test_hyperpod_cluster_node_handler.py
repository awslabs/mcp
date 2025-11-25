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
"""Tests for the HyperPod cluster node handler."""

import os
import pytest
from awslabs.sagemaker_ai_mcp_server.aws_helper import AwsHelper
from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_cluster_node_handler import (
    HyperPodClusterNodeHandler,
)
from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.models import (
    BatchDeleteClusterNodesResponse,
    ClusterInstanceStatusDetails,
    ClusterNodeDetails,
    ClusterNodeSummary,
    ClusterSummary,
    DescribeClusterNodeResponse,
    ListClusterNodesResponse,
    ListClustersResponse,
    UpdateClusterSoftwareResponse,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import ANY, MagicMock, patch


class TestHyperPodClusterNodeHandler:
    """Tests for the HyperPodClusterNodeHandler class."""

    def test_init_default(self):
        """Test that the handler is initialized correctly and registers its tools with default allow_write=False."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_write is False
        assert handler.allow_sensitive_data_access is False

        # Verify that the tool was registered
        assert mock_mcp.tool.call_count == 3
        tool_names = [call_args[1]['name'] for call_args in mock_mcp.tool.call_args_list]
        assert 'manage_hyperpod_cluster_nodes' in tool_names

    def test_init_write_access_enabled(self):
        """Test that the handler is initialized correctly with allow_write=True."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_write is True
        assert handler.allow_sensitive_data_access is False

    def test_init_sensitive_data_access_enabled(self):
        """Test that the handler is initialized correctly with allow_sensitive_data_access=True."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_sensitive_data_access=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_sensitive_data_access=True)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_write is False
        assert handler.allow_sensitive_data_access is True

    def test_get_sagemaker_client(self):
        """Test that get_sagemaker_client returns a SageMaker client."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock boto3 client
        mock_client = MagicMock()

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_client
        ) as mock_create_client:
            # Call the get_sagemaker_client method
            client = handler.get_sagemaker_client(mock_ctx)

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('sagemaker', region_name=None)

            # Verify that the client is the mock client
            assert client == mock_client

    def test_get_sagemaker_client_with_region(self):
        """Test that get_sagemaker_client returns a SageMaker client with the specified region."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock boto3 client
        mock_client = MagicMock()

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_client
        ) as mock_create_client:
            # Call the get_sagemaker_client method with a region
            client = handler.get_sagemaker_client(mock_ctx, region_name='us-west-2')

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('sagemaker', region_name='us-west-2')

            # Verify that the client is the mock client
            assert client == mock_client

    def test_get_sagemaker_client_with_profile(self):
        """Test that get_sagemaker_client returns a SageMaker client with the specified profile."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock boto3 client
        mock_client = MagicMock()

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_client
        ) as mock_create_client:
            # Call the get_sagemaker_client method with a profile
            client = handler.get_sagemaker_client(mock_ctx, profile_name='test-profile')

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('sagemaker', region_name=None)

            # Verify that the client is the mock client
            assert client == mock_client

            # Verify that the AWS_PROFILE environment variable was set
            assert os.environ.get('AWS_PROFILE') == 'test-profile'

    @pytest.mark.asyncio
    async def test_list_hp_clusters_success(self):
        """Test that _list_hp_clusters returns a list of clusters successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.list_clusters.return_value = {
            'ClusterSummaries': [
                {
                    'ClusterName': 'test-cluster',
                    'ClusterArn': 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
                    'ClusterStatus': 'InService',
                    'CreationTime': '2023-01-01T00:00:00Z',
                    'TrainingPlanArns': [
                        'arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan'
                    ],
                }
            ],
            'NextToken': 'next-token',
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _list_hp_clusters method
            result = await handler._list_hp_clusters(
                ctx=mock_ctx,
                max_results=10,
                next_token='token',
                name_contains='test',
                creation_time_after='2023-01-01T00:00:00Z',
                creation_time_before='2023-01-02T00:00:00Z',
                sort_by='NAME',
                sort_order='Descending',
                training_plan_arn='arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan',
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that list_clusters was called with the correct parameters
            mock_sagemaker_client.list_clusters.assert_called_once_with(
                MaxResults=10,
                NextToken='token',
                NameContains='test',
                CreationTimeAfter='2023-01-01T00:00:00Z',
                CreationTimeBefore='2023-01-02T00:00:00Z',
                SortBy='NAME',
                SortOrder='Descending',
                TrainingPlanArn='arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan',
            )

            # Verify the result
            assert not result.isError
            assert len(result.clusters) == 1
            assert result.clusters[0].cluster_name == 'test-cluster'
            assert (
                result.clusters[0].cluster_arn
                == 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster'
            )
            assert result.clusters[0].cluster_status == 'InService'
            assert result.clusters[0].creation_time == '2023-01-01T00:00:00Z'
            assert result.clusters[0].training_plan_arns == [
                'arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan'
            ]
            assert result.next_token == 'next-token'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Successfully listed 1 SageMaker HyperPod clusters' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_hp_clusters_error(self):
        """Test that _list_hp_clusters handles errors correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod Cluster Node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.list_clusters.side_effect = Exception('Test error')

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _list_hp_clusters method
            result = await handler._list_hp_clusters(
                ctx=mock_ctx,
                region_name='us-west-2',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name=ANY
            )

            # Verify that list_clusters was called
            mock_sagemaker_client.list_clusters.assert_called_once()

            # Verify the result
            assert result.isError
            assert len(result.clusters) == 0
            assert result.next_token is None
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Failed to list SageMaker HyperPod clusters: Test error' in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_describe_hp_cluster_node_success(self):
        """Test that _describe_hp_cluster_node returns node details successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.describe_cluster_node.return_value = {
            'NodeDetails': {
                'InstanceGroupName': 'test-group',
                'InstanceId': 'i-1234567890abcdef0',
                'InstanceStatus': {
                    'Status': 'Running',
                    'Message': 'Node is running',
                },
                'InstanceType': 'ml.g5.8xlarge',
                'LaunchTime': '2023-01-01T00:00:00Z',
                'LastSoftwareUpdateTime': '2023-01-02T00:00:00Z',
                'InstanceStorageConfigs': [
                    {
                        'EbsVolumeConfig': {
                            'VolumeSizeInGb': 500,
                        },
                    },
                ],
                'LifeCycleConfig': {
                    'OnCreate': 'echo "Hello, World!"',
                    'SourceS3Uri': 's3://bucket/path',
                },
                'OverrideVpcConfig': {
                    'SecurityGroupIds': ['sg-1234567890abcdef0'],
                    'Subnets': ['subnet-1234567890abcdef0'],
                },
                'Placement': {
                    'AvailabilityZone': 'us-west-2a',
                    'AvailabilityZoneId': 'usw2-az1',
                },
                'PrivateDnsHostname': 'ip-10-0-0-1.us-west-2.compute.internal',
                'PrivatePrimaryIp': '10.0.0.1',
                'PrivatePrimaryIpv6': '2001:db8::1',
                'ThreadsPerCore': 1,
            },
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _describe_hp_cluster_node method
            result = await handler._describe_hp_cluster_node(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                node_id='i-1234567890abcdef0',
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that describe_cluster_node was called with the correct parameters
            mock_sagemaker_client.describe_cluster_node.assert_called_once_with(
                ClusterName='test-cluster',
                NodeId='i-1234567890abcdef0',
            )

            # Verify the result
            assert not result.isError
            assert result.node_details is not None
            assert result.node_details.instance_group_name == 'test-group'
            assert result.node_details.instance_id == 'i-1234567890abcdef0'
            assert result.node_details.instance_status.status == 'Running'
            assert result.node_details.instance_status.message == 'Node is running'
            assert result.node_details.instance_type == 'ml.g5.8xlarge'
            assert result.node_details.launch_time == '2023-01-01T00:00:00Z'
            assert result.node_details.last_software_update_time == '2023-01-02T00:00:00Z'
            assert result.node_details.instance_storage_configs is not None
            assert len(result.node_details.instance_storage_configs) == 1
            assert result.node_details.instance_storage_configs[0].ebs_volume_config is not None
            assert (
                result.node_details.instance_storage_configs[0].ebs_volume_config.volume_size_in_gb
                == 500
            )
            assert result.node_details.life_cycle_config is not None
            assert result.node_details.life_cycle_config.on_create == 'echo "Hello, World!"'
            assert result.node_details.life_cycle_config.source_s3_uri == 's3://bucket/path'
            assert result.node_details.override_vpc_config is not None
            assert result.node_details.override_vpc_config.security_group_ids == [
                'sg-1234567890abcdef0'
            ]
            assert result.node_details.override_vpc_config.subnets == ['subnet-1234567890abcdef0']
            assert result.node_details.placement is not None
            assert result.node_details.placement.availability_zone == 'us-west-2a'
            assert result.node_details.placement.availability_zone_id == 'usw2-az1'
            assert (
                result.node_details.private_dns_hostname
                == 'ip-10-0-0-1.us-west-2.compute.internal'
            )
            assert result.node_details.private_primary_ip == '10.0.0.1'
            assert result.node_details.private_primary_ipv6 == '2001:db8::1'
            assert result.node_details.threads_per_core == 1
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Successfully described SageMaker HyperPod cluster node: i-1234567890abcdef0'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_describe_hp_cluster_node_error(self):
        """Test that _describe_hp_cluster_node handles errors correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.describe_cluster_node.side_effect = Exception('Test error')

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _describe_hp_cluster_node method
            result = await handler._describe_hp_cluster_node(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                node_id='i-1234567890abcdef0',
                region_name='us-west-2',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name=ANY
            )

            # Verify that describe_cluster_node was called with the correct parameters
            mock_sagemaker_client.describe_cluster_node.assert_called_once_with(
                ClusterName='test-cluster',
                NodeId='i-1234567890abcdef0',
            )

            # Verify the result
            assert result.isError
            assert result.node_details is None
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Failed to describe SageMaker HyperPod cluster node: Test error'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_list_hp_cluster_nodes_success(self):
        """Test that _list_hp_cluster_nodes returns a list of nodes successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.list_cluster_nodes.return_value = {
            'ClusterNodeSummaries': [
                {
                    'InstanceGroupName': 'test-group',
                    'InstanceId': 'i-1234567890abcdef0',
                    'InstanceStatus': {
                        'Status': 'Running',
                        'Message': 'Node is running',
                    },
                    'InstanceType': 'ml.g5.8xlarge',
                    'LaunchTime': '2023-01-01T00:00:00Z',
                    'LastSoftwareUpdateTime': '2023-01-02T00:00:00Z',
                },
            ],
            'NextToken': 'next-token',
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _list_hp_cluster_nodes method
            result = await handler._list_hp_cluster_nodes(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                creation_time_after='2023-01-01T00:00:00Z',
                creation_time_before='2023-01-02T00:00:00Z',
                instance_group_name_contains='test',
                max_results=10,
                next_token='token',
                sort_by='NAME',
                sort_order='Descending',
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that list_cluster_nodes was called with the correct parameters
            mock_sagemaker_client.list_cluster_nodes.assert_called_once_with(
                ClusterName='test-cluster',
                CreationTimeAfter='2023-01-01T00:00:00Z',
                CreationTimeBefore='2023-01-02T00:00:00Z',
                InstanceGroupNameContains='test',
                MaxResults=10,
                NextToken='token',
                SortBy='NAME',
                SortOrder='Descending',
            )

            # Verify the result
            assert not result.isError
            assert len(result.nodes) == 1
            assert result.nodes[0].instance_group_name == 'test-group'
            assert result.nodes[0].instance_id == 'i-1234567890abcdef0'
            assert result.nodes[0].instance_status.status == 'Running'
            assert result.nodes[0].instance_status.message == 'Node is running'
            assert result.nodes[0].instance_type == 'ml.g5.8xlarge'
            assert result.nodes[0].launch_time == '2023-01-01T00:00:00Z'
            assert result.nodes[0].last_software_update_time == '2023-01-02T00:00:00Z'
            assert result.next_token == 'next-token'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Successfully listed 1 SageMaker HyperPod cluster nodes' in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_list_hp_cluster_nodes_error(self):
        """Test that _list_hp_cluster_nodes handles errors correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.list_cluster_nodes.side_effect = Exception('Test error')

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _list_hp_cluster_nodes method
            result = await handler._list_hp_cluster_nodes(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                region_name='us-west-2',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name=ANY
            )

            # Verify that list_cluster_nodes was called with the correct parameters
            # Use ANY for additional parameters that might be added by default
            mock_sagemaker_client.list_cluster_nodes.assert_called_once()
            args, kwargs = mock_sagemaker_client.list_cluster_nodes.call_args
            assert kwargs['ClusterName'] == 'test-cluster'

            # Verify the result
            assert result.isError
            assert len(result.nodes) == 0
            assert result.next_token is None
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Failed to list SageMaker HyperPod cluster nodes: Test error'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_update_hp_cluster_software_success(self):
        """Test that _update_hp_cluster_software updates cluster software successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.update_cluster_software.return_value = {
            'ClusterArn': 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(handler, 'get_sagemaker_client', return_value=mock_sagemaker_client):
            # Mock the deployment_config and instance_groups attributes
            with patch.object(handler, '_update_hp_cluster_software') as mock_update:
                mock_update.return_value = UpdateClusterSoftwareResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully initiated software update for SageMaker HyperPod cluster: test-cluster',
                        )
                    ],
                    cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
                )

                # Call the _update_hp_cluster_software method
                result = await mock_update(
                    ctx=mock_ctx,
                    cluster_name='test-cluster',
                    region_name='us-west-2',
                    profile_name='test-profile',
                )

                # Verify the result
                assert not result.isError
                assert (
                    result.cluster_arn
                    == 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster'
                )
                assert len(result.content) == 1
                assert result.content[0].type == 'text'
                assert (
                    'Successfully initiated software update for SageMaker HyperPod cluster: test-cluster'
                    in result.content[0].text
                )

    @pytest.mark.asyncio
    async def test_update_hp_cluster_software_with_deployment_config(self):
        """Test that _update_hp_cluster_software updates cluster software with deployment config."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.update_cluster_software.return_value = {
            'ClusterArn': 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Create deployment config
            from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.models import (
                AlarmDetails,
                CapacitySizeConfig,
                DeploymentConfiguration,
                RollingDeploymentPolicy,
                UpdateClusterSoftwareInstanceGroupSpecification,
            )

            deployment_config = DeploymentConfiguration(
                auto_rollback_configuration=[AlarmDetails(alarm_name='test-alarm')],
                rolling_update_policy=RollingDeploymentPolicy(
                    maximum_batch_size=CapacitySizeConfig(type='INSTANCE_COUNT', value=1),
                    rollback_maximum_batch_size=CapacitySizeConfig(
                        type='CAPACITY_PERCENTAGE', value=50
                    ),
                ),
                wait_interval_in_seconds=60,
            )

            instance_groups = [
                UpdateClusterSoftwareInstanceGroupSpecification(instance_group_name='test-group')
            ]

            # Call the _update_hp_cluster_software method with deployment config and instance groups
            result = await handler._update_hp_cluster_software(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                deployment_config=deployment_config,
                instance_groups=instance_groups,
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that update_cluster_software was called with the correct parameters
            mock_sagemaker_client.update_cluster_software.assert_called_once()
            args, kwargs = mock_sagemaker_client.update_cluster_software.call_args
            assert kwargs['ClusterName'] == 'test-cluster'

            # Verify deployment config
            assert 'DeploymentConfig' in kwargs
            assert 'AutoRollbackConfiguration' in kwargs['DeploymentConfig']
            assert (
                kwargs['DeploymentConfig']['AutoRollbackConfiguration'][0]['AlarmName']
                == 'test-alarm'
            )
            assert 'RollingUpdatePolicy' in kwargs['DeploymentConfig']
            assert (
                kwargs['DeploymentConfig']['RollingUpdatePolicy']['MaximumBatchSize']['Type']
                == 'INSTANCE_COUNT'
            )
            assert (
                kwargs['DeploymentConfig']['RollingUpdatePolicy']['MaximumBatchSize']['Value'] == 1
            )
            assert (
                kwargs['DeploymentConfig']['RollingUpdatePolicy']['RollbackMaximumBatchSize'][
                    'Type'
                ]
                == 'CAPACITY_PERCENTAGE'
            )
            assert (
                kwargs['DeploymentConfig']['RollingUpdatePolicy']['RollbackMaximumBatchSize'][
                    'Value'
                ]
                == 50
            )
            assert kwargs['DeploymentConfig']['WaitIntervalInSeconds'] == 60

            # Verify instance groups
            assert 'InstanceGroups' in kwargs
            assert len(kwargs['InstanceGroups']) == 1
            assert kwargs['InstanceGroups'][0]['InstanceGroupName'] == 'test-group'

            # Verify the result
            assert not result.isError
            assert (
                result.cluster_arn
                == 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster'
            )
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Successfully initiated software update for SageMaker HyperPod cluster: test-cluster'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_update_hp_cluster_software_error(self):
        """Test that _update_hp_cluster_software handles errors correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.update_cluster_software.side_effect = Exception('Test error')

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _update_hp_cluster_software method
            result = await handler._update_hp_cluster_software(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                region_name='us-west-2',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name=ANY
            )

            # Mock the update_cluster_software method to avoid the actual call
            with patch.object(mock_sagemaker_client, 'update_cluster_software') as mock_update:
                mock_update.side_effect = Exception('Test error')

            # Verify the result
            assert result.isError
            assert result.cluster_arn == ''
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            # The actual error message might be different, just check that it contains the key parts
            assert (
                'Failed to update software for SageMaker HyperPod cluster'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_batch_delete_hp_cluster_nodes_success(self):
        """Test that _batch_delete_hp_cluster_nodes deletes nodes successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.batch_delete_cluster_nodes.return_value = {
            'Successful': ['i-1234567890abcdef0', 'i-0987654321fedcba0'],
            'Failed': [],
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _batch_delete_hp_cluster_nodes method
            result = await handler._batch_delete_hp_cluster_nodes(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                node_ids=['i-1234567890abcdef0', 'i-0987654321fedcba0'],
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that batch_delete_cluster_nodes was called with the correct parameters
            mock_sagemaker_client.batch_delete_cluster_nodes.assert_called_once_with(
                ClusterName='test-cluster',
                NodeIds=['i-1234567890abcdef0', 'i-0987654321fedcba0'],
            )

            # Verify the result
            assert not result.isError
            assert result.cluster_name == 'test-cluster'
            assert result.successful == ['i-1234567890abcdef0', 'i-0987654321fedcba0']
            assert result.failed is None or len(result.failed) == 0
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Successfully deleted 2 nodes from SageMaker HyperPod cluster: test-cluster'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_batch_delete_hp_cluster_nodes_with_failures(self):
        """Test that _batch_delete_hp_cluster_nodes handles partial failures correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.batch_delete_cluster_nodes.return_value = {
            'Successful': ['i-1234567890abcdef0'],
            'Failed': [
                {
                    'NodeId': 'i-0987654321fedcba0',
                    'Code': 'ValidationException',
                    'Message': 'Node is a controller node and cannot be deleted',
                }
            ],
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _batch_delete_hp_cluster_nodes method
            result = await handler._batch_delete_hp_cluster_nodes(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                node_ids=['i-1234567890abcdef0', 'i-0987654321fedcba0'],
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that batch_delete_cluster_nodes was called with the correct parameters
            mock_sagemaker_client.batch_delete_cluster_nodes.assert_called_once_with(
                ClusterName='test-cluster',
                NodeIds=['i-1234567890abcdef0', 'i-0987654321fedcba0'],
            )

            # Verify the result
            assert not result.isError
            assert result.cluster_name == 'test-cluster'
            assert result.successful == ['i-1234567890abcdef0']
            assert result.failed is not None
            assert len(result.failed) == 1
            assert result.failed[0].node_id == 'i-0987654321fedcba0'
            assert result.failed[0].code == 'ValidationException'
            assert result.failed[0].message == 'Node is a controller node and cannot be deleted'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Successfully deleted 1 nodes from SageMaker HyperPod cluster: test-cluster. Failed deletions: 1'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_batch_delete_hp_cluster_nodes_error(self):
        """Test that _batch_delete_hp_cluster_nodes handles errors correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.batch_delete_cluster_nodes.side_effect = Exception('Test error')

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the _batch_delete_hp_cluster_nodes method
            result = await handler._batch_delete_hp_cluster_nodes(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                node_ids=['i-1234567890abcdef0'],
                region_name='us-west-2',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name=ANY
            )

            # Verify that batch_delete_cluster_nodes was called with the correct parameters
            mock_sagemaker_client.batch_delete_cluster_nodes.assert_called_once_with(
                ClusterName='test-cluster',
                NodeIds=['i-1234567890abcdef0'],
            )

            # Verify the result
            assert result.isError
            assert result.cluster_name == 'test-cluster'
            assert result.successful == []
            assert result.failed is None or len(result.failed) == 0
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert (
                'Failed to delete nodes from SageMaker HyperPod cluster: Test error'
                in result.content[0].text
            )

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_list_clusters(self):
        """Test that manage_hyperpod_cluster_nodes handles the list_clusters operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _list_hp_clusters method
        mock_result = ListClustersResponse(
            isError=False,
            content=[
                TextContent(type='text', text='Successfully listed SageMaker HyperPod clusters')
            ],
            clusters=[
                ClusterSummary(
                    cluster_name='test-cluster',
                    cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
                    cluster_status='InService',
                    creation_time='2023-01-01T00:00:00Z',
                    training_plan_arns=[
                        'arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan'
                    ],
                )
            ],
            next_token='next-token',
        )
        with patch.object(handler, '_list_hp_clusters', return_value=mock_result) as mock_handler:
            # Call the manage_hyperpod_cluster_nodes method with list_clusters operation
            result = await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='list_clusters',
                max_results=10,
                next_token='token',
                name_contains='test',
                sort_by='NAME',
                sort_order='Descending',
                training_plan_arn='arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan',
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that _list_hp_clusters was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['max_results'] == 10
            assert call_args['next_token'] == 'token'
            assert call_args['name_contains'] == 'test'
            assert call_args['sort_by'] == 'NAME'
            assert call_args['sort_order'] == 'Descending'
            assert (
                call_args['training_plan_arn']
                == 'arn:aws:sagemaker:us-west-2:123456789012:training-plan/test-plan'
            )
            assert call_args['region_name'] == 'us-west-2'
            assert call_args['profile_name'] == 'test-profile'

            # Verify the result is the same as the mock result
            assert result is mock_result
            assert not result.isError
            # Type assertion to help pyright understand this is ListClustersResponse
            assert isinstance(result, ListClustersResponse)
            assert len(result.clusters) == 1
            assert result.clusters[0].cluster_name == 'test-cluster'
            assert result.next_token == 'next-token'

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_list_nodes(self):
        """Test that manage_hyperpod_cluster_nodes handles the list_nodes operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _list_hp_cluster_nodes method
        mock_result = ListClusterNodesResponse(
            isError=False,
            content=[
                TextContent(
                    type='text', text='Successfully listed SageMaker HyperPod cluster nodes'
                )
            ],
            nodes=[
                ClusterNodeSummary(
                    instance_group_name='test-group',
                    instance_id='i-1234567890abcdef0',
                    instance_status=ClusterInstanceStatusDetails(
                        status='Running',
                        message='Node is running',
                    ),
                    instance_type='ml.g5.8xlarge',
                    launch_time='2023-01-01T00:00:00Z',
                    last_software_update_time='2023-01-02T00:00:00Z',
                )
            ],
            next_token='next-token',
        )
        with patch.object(
            handler, '_list_hp_cluster_nodes', return_value=mock_result
        ) as mock_handler:
            # Call the manage_hyperpod_cluster_nodes method with list_nodes operation
            result = await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='list_nodes',
                cluster_name='test-cluster',
                creation_time_after='2023-01-01T00:00:00Z',
                creation_time_before='2023-01-02T00:00:00Z',
                instance_group_name_contains='test',
                max_results=10,
                next_token='token',
                sort_by='NAME',
                sort_order='Descending',
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that _list_hp_cluster_nodes was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['cluster_name'] == 'test-cluster'
            assert call_args['creation_time_after'] == '2023-01-01T00:00:00Z'
            assert call_args['creation_time_before'] == '2023-01-02T00:00:00Z'
            assert call_args['instance_group_name_contains'] == 'test'
            assert call_args['max_results'] == 10
            assert call_args['next_token'] == 'token'
            assert call_args['sort_by'] == 'NAME'
            assert call_args['sort_order'] == 'Descending'
            assert call_args['region_name'] == 'us-west-2'
            assert call_args['profile_name'] == 'test-profile'

            # Verify the result is the same as the mock result
            assert result is mock_result
            assert not result.isError
            assert isinstance(result, ListClusterNodesResponse)
            assert len(result.nodes) == 1
            assert result.nodes[0].instance_id == 'i-1234567890abcdef0'
            assert result.next_token == 'next-token'

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_describe_node(self):
        """Test that manage_hyperpod_cluster_nodes handles the describe_node operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _describe_hp_cluster_node method
        mock_result = DescribeClusterNodeResponse(
            isError=False,
            content=[
                TextContent(
                    type='text', text='Successfully described SageMaker HyperPod cluster node'
                )
            ],
            node_details=ClusterNodeDetails(
                instance_group_name='test-group',
                instance_id='i-1234567890abcdef0',
                instance_status=ClusterInstanceStatusDetails(
                    status='Running',
                    message='Node is running',
                ),
                instance_type='ml.g5.8xlarge',
                launch_time='2023-01-01T00:00:00Z',
                last_software_update_time='2023-01-02T00:00:00Z',
                instance_storage_configs=None,
                life_cycle_config=None,
                override_vpc_config=None,
                placement=None,
                private_dns_hostname='ip-10-0-0-1.us-west-2.compute.internal',
                private_primary_ip='10.0.0.1',
                private_primary_ipv6='2001:db8::1',
                threads_per_core=1,
            ),
        )
        with patch.object(
            handler, '_describe_hp_cluster_node', return_value=mock_result
        ) as mock_handler:
            # Call the manage_hyperpod_cluster_nodes method with describe_node operation
            result = await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='describe_node',
                cluster_name='test-cluster',
                node_id='i-1234567890abcdef0',
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that _describe_hp_cluster_node was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['cluster_name'] == 'test-cluster'
            assert call_args['node_id'] == 'i-1234567890abcdef0'
            assert call_args['region_name'] == 'us-west-2'
            assert call_args['profile_name'] == 'test-profile'

            # Verify the result is the same as the mock result
            assert result is mock_result
            assert not result.isError
            # Type assertion to help pyright understand this is DescribeClusterNodeResponse
            assert isinstance(result, DescribeClusterNodeResponse)
            assert result.node_details is not None
            assert result.node_details.instance_id == 'i-1234567890abcdef0'
            assert result.node_details.instance_group_name == 'test-group'

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_update_software(self):
        """Test that manage_hyperpod_cluster_nodes handles the update_software operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _update_hp_cluster_software method
        mock_result = UpdateClusterSoftwareResponse(
            isError=False,
            content=[
                TextContent(
                    type='text',
                    text='Successfully initiated software update for SageMaker HyperPod cluster',
                )
            ],
            cluster_arn='arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
        )
        with patch.object(
            handler, '_update_hp_cluster_software', return_value=mock_result
        ) as mock_handler:
            # Create deployment config and instance groups
            from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.models import (
                AlarmDetails,
                CapacitySizeConfig,
                DeploymentConfiguration,
                RollingDeploymentPolicy,
                UpdateClusterSoftwareInstanceGroupSpecification,
            )

            deployment_config = DeploymentConfiguration(
                auto_rollback_configuration=[AlarmDetails(alarm_name='test-alarm')],
                rolling_update_policy=RollingDeploymentPolicy(
                    maximum_batch_size=CapacitySizeConfig(type='INSTANCE_COUNT', value=1),
                    rollback_maximum_batch_size=CapacitySizeConfig(
                        type='CAPACITY_PERCENTAGE', value=50
                    ),
                ),
                wait_interval_in_seconds=60,
            )

            instance_groups = [
                UpdateClusterSoftwareInstanceGroupSpecification(instance_group_name='test-group')
            ]

            # Call the manage_hyperpod_cluster_nodes method with update_software operation
            result = await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='update_software',
                cluster_name='test-cluster',
                deployment_config=deployment_config,
                instance_groups=instance_groups,
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that _update_hp_cluster_software was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['cluster_name'] == 'test-cluster'
            assert call_args['deployment_config'] == deployment_config
            assert call_args['instance_groups'] == instance_groups
            assert call_args['region_name'] == 'us-west-2'
            assert call_args['profile_name'] == 'test-profile'

            # Verify the result is the same as the mock result
            assert result is mock_result
            assert not result.isError
            # Type assertion to help pyright understand this is UpdateClusterSoftwareResponse
            assert isinstance(result, UpdateClusterSoftwareResponse)
            assert (
                result.cluster_arn
                == 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster'
            )

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_batch_delete(self):
        """Test that manage_hyperpod_cluster_nodes handles the batch_delete operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod Cluster Node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _batch_delete_hp_cluster_nodes method
        mock_result = BatchDeleteClusterNodesResponse(
            isError=False,
            content=[
                TextContent(
                    type='text', text='Successfully deleted nodes from SageMaker HyperPod cluster'
                )
            ],
            cluster_name='test-cluster',
            successful=['i-1234567890abcdef0', 'i-0987654321fedcba0'],
            failed=None,
        )
        with patch.object(
            handler, '_batch_delete_hp_cluster_nodes', return_value=mock_result
        ) as mock_handler:
            # Call the manage_hyperpod_cluster_nodes method with batch_delete operation
            result = await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='batch_delete',
                cluster_name='test-cluster',
                node_ids=['i-1234567890abcdef0', 'i-0987654321fedcba0'],
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that _batch_delete_hp_cluster_nodes was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['cluster_name'] == 'test-cluster'
            assert call_args['node_ids'] == ['i-1234567890abcdef0', 'i-0987654321fedcba0']
            assert call_args['region_name'] == 'us-west-2'
            assert call_args['profile_name'] == 'test-profile'

            # Verify the result is the same as the mock result
            assert result is mock_result
            assert not result.isError
            # Type assertion to help pyright understand this is BatchDeleteClusterNodesResponse
            assert isinstance(result, BatchDeleteClusterNodesResponse)
            assert result.cluster_name == 'test-cluster'
            assert result.successful == ['i-1234567890abcdef0', 'i-0987654321fedcba0']
            assert result.failed is None

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_invalid_operation(self):
        """Test that manage_hyperpod_cluster_nodes handles invalid operations correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call the manage_hyperpod_cluster_nodes method with an invalid operation
        with pytest.raises(ValueError, match='validation error'):
            await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='invalid',  # pyright: ignore[reportArgumentType]
                cluster_name='test-cluster',
            )

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_missing_parameters(self):
        """Test that manage_hyperpod_cluster_nodes handles missing parameters correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server
        handler = HyperPodClusterNodeHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Test missing cluster_name for list_nodes operation
        with pytest.raises(
            ValueError, match='cluster_name is required for all operations except list_clusters'
        ):
            await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='list_nodes',
                cluster_name=None,  # Explicitly pass None
            )

        # Test missing node_id for describe_node operation
        with pytest.raises(ValueError, match='node_id is required for describe_node operation'):
            await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='describe_node',
                cluster_name='test-cluster',
                node_id=None,  # Explicitly pass None
            )

        # Test missing node_ids for batch_delete operation
        with pytest.raises(ValueError, match='node_ids is required for batch_delete operation'):
            await handler.manage_hyperpod_cluster_nodes(
                ctx=mock_ctx,
                operation='batch_delete',
                cluster_name='test-cluster',
                node_ids=None,  # Explicitly pass None
            )

    @pytest.mark.asyncio
    async def test_manage_hyperpod_cluster_nodes_write_access_disabled(self):
        """Test that manage_hyperpod_cluster_nodes rejects mutating operations when write access is disabled."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=False
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=False)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Test update_software operation (should be rejected when write access is disabled)
        result = await handler.manage_hyperpod_cluster_nodes(
            ctx=mock_ctx,
            operation='update_software',
            cluster_name='test-cluster',
        )

        # Verify the result
        assert result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert (
            'Operation update_software is not allowed without write access'
            in result.content[0].text
        )

        # Test batch_delete operation (should be rejected when write access is disabled)
        result = await handler.manage_hyperpod_cluster_nodes(
            ctx=mock_ctx,
            operation='batch_delete',
            cluster_name='test-cluster',
            node_ids=['i-1234567890abcdef0'],
        )

        # Verify the result
        assert result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert (
            'Operation batch_delete is not allowed without write access' in result.content[0].text
        )

    @pytest.mark.asyncio
    async def test_update_hp_cluster_write_access_disabled(self):
        """Test that update_hp_cluster returns an error when write access is disabled."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=False
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=False)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call the update_hp_cluster method
        result = await handler.update_hp_cluster(
            ctx=mock_ctx,
            cluster_name='test-cluster',
            instance_groups=[{'InstanceGroupName': 'test-group'}],
            region_name='us-west-2',
            profile_name='test-profile',
        )

        # Verify the result
        assert result['isError'] is True
        assert 'Write access is not enabled for this handler' in result['errorMessage']

    @pytest.mark.asyncio
    async def test_update_hp_cluster_success(self):
        """Test that update_hp_cluster updates a cluster successfully when write access is enabled."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.update_cluster.return_value = {
            'ClusterArn': 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
        }

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the update_hp_cluster method
            result = await handler.update_hp_cluster(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                instance_groups=[{'InstanceGroupName': 'test-group'}],
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that update_cluster was called with the correct parameters
            mock_sagemaker_client.update_cluster.assert_called_once_with(
                ClusterName='test-cluster',
                InstanceGroups=[{'InstanceGroupName': 'test-group'}],
            )

            # Verify the result
            assert result == {
                'ClusterArn': 'arn:aws:sagemaker:us-west-2:123456789012:cluster/test-cluster',
            }

    @pytest.mark.asyncio
    async def test_update_hp_cluster_api_error(self):
        """Test that update_hp_cluster handles API call errors correctly in the sequential try-catch structure."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock SageMaker client
        mock_sagemaker_client = MagicMock()
        mock_sagemaker_client.update_cluster.side_effect = Exception('API call error')

        # Mock the get_sagemaker_client method to return our mock client
        with patch.object(
            handler, 'get_sagemaker_client', return_value=mock_sagemaker_client
        ) as mock_get_client:
            # Call the update_hp_cluster method
            result = await handler.update_hp_cluster(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                instance_groups=[{'InstanceGroupName': 'test-group'}],
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify that update_cluster was called with the correct parameters
            mock_sagemaker_client.update_cluster.assert_called_once_with(
                ClusterName='test-cluster',
                InstanceGroups=[{'InstanceGroupName': 'test-group'}],
            )

            # Verify the result - should have specific error message from the API call try-catch block
            assert result['isError'] is True
            assert 'SageMaker update_cluster API error: API call error' in result['errorMessage']

    @pytest.mark.asyncio
    async def test_update_hp_cluster_client_error(self):
        """Test that update_hp_cluster handles client creation errors correctly in the sequential try-catch structure."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod cluster node handler with the mock MCP server and allow_write=True
        handler = HyperPodClusterNodeHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the get_sagemaker_client method to raise an exception
        with patch.object(
            handler, 'get_sagemaker_client', side_effect=Exception('Client creation error')
        ) as mock_get_client:
            # Call the update_hp_cluster method
            result = await handler.update_hp_cluster(
                ctx=mock_ctx,
                cluster_name='test-cluster',
                instance_groups=[{'InstanceGroupName': 'test-group'}],
                region_name='us-west-2',
                profile_name='test-profile',
            )

            # Verify that get_sagemaker_client was called with the correct parameters
            mock_get_client.assert_called_once_with(
                mock_ctx, region_name='us-west-2', profile_name='test-profile'
            )

            # Verify the result - should have specific error message from the client creation try-catch block
            assert result['isError'] is True
            assert (
                'Failed to prepare SageMaker client or parameters: Client creation error'
                in result['errorMessage']
            )
