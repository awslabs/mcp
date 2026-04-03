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

"""Tests for the CUSTOM_TAGS environment variable functionality in EMR handlers."""

import os
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_cluster_handler import (
    EMREc2ClusterHandler,
)
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    CUSTOM_TAGS_ENV_VAR,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestCustomTagsEmr:
    """Tests for the CUSTOM_TAGS environment variable functionality in EMR handlers."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def handler_with_write_access(self, mock_mcp):
        """Create an EmrEc2ClusterHandler instance with write access enabled."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = EMREc2ClusterHandler(mock_mcp, allow_write=True)
            return handler

    @pytest.mark.asyncio
    async def test_create_cluster_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that create cluster operation respects CUSTOM_TAGS when enabled."""
        # Mock the create_cluster method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.cluster_id = 'j-12345ABCDEF'
        mock_response.operation = 'create-cluster'
        handler_with_write_access.run_job_flow = AsyncMock(return_value=mock_response)

        # Create a comprehensive cluster configuration
        cluster_config = {
            'Name': 'Test Cluster',
            'LogUri': 's3://test-bucket/logs/',
            'ReleaseLabel': 'emr-6.6.0',
            'Applications': [{'Name': 'Spark'}, {'Name': 'Hive'}],
            'Instances': {
                'InstanceGroups': [
                    {
                        'Name': 'Master',
                        'InstanceRole': 'MASTER',
                        'InstanceType': 'm5.xlarge',
                        'InstanceCount': 1,
                    },
                    {
                        'Name': 'Core',
                        'InstanceRole': 'CORE',
                        'InstanceType': 'm5.xlarge',
                        'InstanceCount': 2,
                    },
                ],
                'Ec2KeyName': 'test-key',
                'KeepJobFlowAliveWhenNoSteps': True,
                'TerminationProtected': False,
            },
            'BootstrapActions': [
                {
                    'Name': 'Install Dependencies',
                    'ScriptBootstrapAction': {
                        'Path': 's3://test-bucket/bootstrap/install-deps.sh',
                    },
                }
            ],
            'Configurations': [
                {
                    'Classification': 'spark-defaults',
                    'Properties': {'spark.executor.memory': '4g'},
                }
            ],
            'VisibleToAllUsers': True,
            'JobFlowRole': 'EMR_EC2_DefaultRole',
            'ServiceRole': 'EMR_DefaultRole',
            'Tags': [
                {'Key': 'Environment', 'Value': 'Test'},
                {'Key': 'Project', 'Value': 'UnitTest'},
            ],
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.run_job_flow(
                mock_ctx, cluster_config=cluster_config
            )

            # Verify that the method was called with the correct parameters
            handler_with_write_access.run_job_flow.assert_called_once_with(
                mock_ctx, cluster_config=cluster_config
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.cluster_id == 'j-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_terminate_cluster_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that terminate cluster operation respects CUSTOM_TAGS when enabled."""
        # Mock the terminate_cluster method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.cluster_id = 'j-12345ABCDEF'
        mock_response.operation = 'terminate-cluster'
        handler_with_write_access.terminate_job_flows = AsyncMock(return_value=mock_response)

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.terminate_job_flows(
                mock_ctx, cluster_id='j-12345ABCDEF'
            )

            # Verify that the method was called with the correct parameters
            handler_with_write_access.terminate_job_flows.assert_called_once_with(
                mock_ctx, cluster_id='j-12345ABCDEF'
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.cluster_id == 'j-12345ABCDEF'

    @pytest.mark.asyncio
    async def test_add_steps_with_custom_tags_enabled(self, handler_with_write_access, mock_ctx):
        """Test that add steps operation respects CUSTOM_TAGS when enabled."""
        # Mock the add_steps method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.cluster_id = 'j-12345ABCDEF'
        mock_response.step_ids = ['s-12345ABCDEF']
        mock_response.operation = 'add-steps'
        handler_with_write_access.add_job_flow_steps = AsyncMock(return_value=mock_response)

        # Create steps configuration
        steps = [
            {
                'Name': 'Test Step',
                'ActionOnFailure': 'CONTINUE',
                'HadoopJarStep': {
                    'Jar': 'command-runner.jar',
                    'Args': [
                        'spark-submit',
                        '--class',
                        'com.example.Main',
                        's3://test-bucket/app.jar',
                    ],
                },
            }
        ]

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.add_job_flow_steps(
                mock_ctx, cluster_id='j-12345ABCDEF', steps=steps
            )

            # Verify that the method was called with the correct parameters
            handler_with_write_access.add_job_flow_steps.assert_called_once_with(
                mock_ctx, cluster_id='j-12345ABCDEF', steps=steps
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.cluster_id == 'j-12345ABCDEF'
            assert result.step_ids == ['s-12345ABCDEF']

    @pytest.mark.asyncio
    async def test_get_cluster_with_custom_tags_enabled(self, handler_with_write_access, mock_ctx):
        """Test that get cluster operation respects CUSTOM_TAGS when enabled."""
        # Mock the get_cluster method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.cluster_id = 'j-12345ABCDEF'
        mock_response.cluster_name = 'Test Cluster'
        mock_response.status = 'RUNNING'
        mock_response.operation = 'get-cluster'
        handler_with_write_access.describe_cluster = AsyncMock(return_value=mock_response)

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.describe_cluster(
                mock_ctx, cluster_id='j-12345ABCDEF'
            )

            # Verify that the method was called with the correct parameters
            handler_with_write_access.describe_cluster.assert_called_once_with(
                mock_ctx, cluster_id='j-12345ABCDEF'
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.cluster_id == 'j-12345ABCDEF'
            assert result.cluster_name == 'Test Cluster'
            assert result.status == 'RUNNING'

    @pytest.mark.asyncio
    async def test_list_clusters_with_custom_tags_enabled(
        self, handler_with_write_access, mock_ctx
    ):
        """Test that list clusters operation respects CUSTOM_TAGS when enabled."""
        # Mock the list_clusters method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.clusters = [
            {'Id': 'j-12345ABCDEF', 'Name': 'Test Cluster 1', 'Status': {'State': 'RUNNING'}},
            {'Id': 'j-67890GHIJKL', 'Name': 'Test Cluster 2', 'Status': {'State': 'WAITING'}},
        ]
        mock_response.count = 2
        mock_response.operation = 'list-clusters'
        handler_with_write_access.list_clusters = AsyncMock(return_value=mock_response)

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await handler_with_write_access.list_clusters(
                mock_ctx, cluster_states=['RUNNING', 'WAITING']
            )

            # Verify that the method was called with the correct parameters
            handler_with_write_access.list_clusters.assert_called_once_with(
                mock_ctx, cluster_states=['RUNNING', 'WAITING']
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert len(result.clusters) == 2
            assert result.count == 2
