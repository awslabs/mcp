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
"""Tests for the HyperPod Stack Handler."""

import json
import pytest
import yaml  # type: ignore
from awslabs.sagemaker_ai_mcp_server.aws_helper import AwsHelper
from awslabs.sagemaker_ai_mcp_server.consts import (
    CAPABILITY_AUTO_EXPAND,
    CFN_CAPABILITY_IAM,
    CFN_CAPABILITY_NAMED_IAM,
    CFN_ON_FAILURE_DELETE,
    CFN_STACK_TAG_KEY,
    CFN_STACK_TAG_VALUE,
)
from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_stack_handler import (
    HyperPodStackHandler,
)
from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.models import (
    DeleteStackResponse,
    DeployStackResponse,
    DescribeStackResponse,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, mock_open, patch


class TestHyperPodStackHandler:
    """Tests for the HyperPodStackHandler class."""

    TEST_REGION = 'us-east-1'
    TEST_STACK_NAME = 'hyperpod-test-cluster-stack'

    def test_init_default(self):
        """Test that the handler is initialized correctly and registers its tools with default allow_write=False."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server
        handler = HyperPodStackHandler(mock_mcp)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_write is False

        # Verify that the manage_hyperpod_stacks tool was registered
        mock_mcp.tool.assert_called_once()
        args, kwargs = mock_mcp.tool.call_args
        assert kwargs['name'] == 'manage_hyperpod_stacks'

    def test_init_write_access_enabled(self):
        """Test that the handler is initialized correctly with allow_write=True."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_write is True

        # Verify that the manage_hyperpod_stacks tool was registered
        mock_mcp.tool.assert_called_once()
        args, kwargs = mock_mcp.tool.call_args
        assert kwargs['name'] == 'manage_hyperpod_stacks'

    @pytest.mark.asyncio
    async def test_deploy_stack_success(self):
        """Test that _deploy_stack deploys a stack successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.create_stack.return_value = {'StackId': 'test-stack-id'}

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_cfn_client
        ) as mock_create_client:
            # Mock the _ensure_stack_ownership method to simulate stack not existing
            with patch.object(
                handler,
                '_ensure_stack_ownership',
                return_value=(False, None, 'Stack does not exist'),
            ):
                # Mock the open function to return a mock file
                mock_template_content = 'test template content'
                with patch('builtins.open', mock_open(read_data=mock_template_content)):
                    # Call the _deploy_stack method
                    result = await handler._deploy_stack(
                        ctx=mock_ctx,
                        template_params=[],
                        region_name=self.TEST_REGION,
                        stack_name=self.TEST_STACK_NAME,
                        cluster_orchestrator='eks',
                    )

                # Verify that AwsHelper.create_boto3_client was called with the correct parameters
                # Since we're mocking _ensure_stack_ownership, it's only called once in _deploy_stack
                assert mock_create_client.call_count == 1
                args, kwargs = mock_create_client.call_args
                assert args[0] == 'cloudformation'

                # Verify that create_stack was called with the correct parameters
                mock_cfn_client.create_stack.assert_called_once()
                args, kwargs = mock_cfn_client.create_stack.call_args
                assert kwargs['StackName'] == self.TEST_STACK_NAME
                assert 'TemplateURL' in kwargs
                assert kwargs['Parameters'] == []
                assert kwargs['Capabilities'] == [
                    CFN_CAPABILITY_IAM,
                    CFN_CAPABILITY_NAMED_IAM,
                    CAPABILITY_AUTO_EXPAND,
                ]
                assert kwargs['OnFailure'] == CFN_ON_FAILURE_DELETE
                assert kwargs['Tags'] == [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}]

                # Verify the result
                assert not result.isError
                assert result.stack_name == self.TEST_STACK_NAME
                assert result.stack_arn == 'test-stack-id'
                assert len(result.content) == 1
                assert result.content[0].type == 'text'
                assert 'CloudFormation stack creation initiated' in result.content[0].text

    def test_ensure_stack_ownership_owned_stack(self):
        """Test that _ensure_stack_ownership correctly identifies a stack owned by our tool."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server
        handler = HyperPodStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                }
            ]
        }

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_cfn_client
        ) as mock_create_client:
            # Call the _ensure_stack_ownership method
            success, stack, error_message = handler._ensure_stack_ownership(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                operation='update',
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            assert mock_create_client.call_count == 1
            args, kwargs = mock_create_client.call_args
            assert args[0] == 'cloudformation'

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(StackName=self.TEST_STACK_NAME)

            # Verify the result
            assert success is True
            assert stack == mock_cfn_client.describe_stacks.return_value['Stacks'][0]
            assert error_message is None

    def test_ensure_stack_ownership_not_owned_stack(self):
        """Test that _ensure_stack_ownership correctly identifies a stack not owned by our tool."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server
        handler = HyperPodStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'Tags': [{'Key': 'SomeOtherTag', 'Value': 'SomeOtherValue'}],
                }
            ]
        }

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_cfn_client
        ) as mock_create_client:
            # Call the _ensure_stack_ownership method
            success, stack, error_message = handler._ensure_stack_ownership(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                operation='update',
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('cloudformation', self.TEST_REGION)

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(StackName=self.TEST_STACK_NAME)

            # Verify the result
            assert success is False
            assert stack == mock_cfn_client.describe_stacks.return_value['Stacks'][0]
            assert error_message is not None
            assert 'not created by' in error_message

    def test_ensure_stack_ownership_stack_not_found(self):
        """Test that _ensure_stack_ownership correctly handles a stack that doesn't exist."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server
        handler = HyperPodStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.side_effect = Exception('Stack does not exist')

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_cfn_client
        ) as mock_create_client:
            # Call the _ensure_stack_ownership method
            success, stack, error_message = handler._ensure_stack_ownership(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                operation='update',
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('cloudformation', self.TEST_REGION)

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(StackName=self.TEST_STACK_NAME)

            # Verify the result
            assert success is False
            assert stack is None
            assert error_message is not None
            assert 'not found' in error_message

    @pytest.mark.asyncio
    async def test_deploy_stack_update_existing(self):
        """Test that _deploy_stack updates an existing stack."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                }
            ]
        }
        mock_cfn_client.update_stack.return_value = {'StackId': 'test-stack-id'}

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_cfn_client
        ) as mock_aws_helper:
            # Mock the open function to return a mock file
            mock_template_content = 'test template content'
            with patch('builtins.open', mock_open(read_data=mock_template_content)):
                # Call the _deploy_stack method
                result = await handler._deploy_stack(
                    ctx=mock_ctx,
                    template_params=[],
                    region_name=self.TEST_REGION,
                    stack_name=self.TEST_STACK_NAME,
                    cluster_orchestrator='eks',
                )

                # Verify that AwsHelper.create_boto3_client was called with the correct parameters
                # Note: It's called twice now - once for _ensure_stack_ownership and once for _deploy_stack
                assert mock_aws_helper.call_count == 2
                mock_aws_helper.assert_any_call('cloudformation', self.TEST_REGION)

                # Verify that update_stack was called with the correct parameters
                mock_cfn_client.update_stack.assert_called_once()
                args, kwargs = mock_cfn_client.update_stack.call_args
                assert kwargs['StackName'] == self.TEST_STACK_NAME
                assert 'TemplateURL' in kwargs
                assert kwargs['Parameters'] == []
                assert kwargs['Capabilities'] == [
                    CFN_CAPABILITY_IAM,
                    CFN_CAPABILITY_NAMED_IAM,
                    CAPABILITY_AUTO_EXPAND,
                ]
                assert kwargs['Tags'] == [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}]

                # Verify the result
                assert not result.isError
                assert result.stack_name == self.TEST_STACK_NAME
                assert result.stack_arn == 'test-stack-id'
                assert len(result.content) == 1
                assert result.content[0].type == 'text'
                assert 'CloudFormation stack update initiated' in result.content[0].text

    @pytest.mark.asyncio
    async def test_describe_stack_success(self):
        """Test that _describe_stack returns stack details successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server
        handler = HyperPodStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'StackName': self.TEST_STACK_NAME,
                    'CreationTime': '2023-01-01T00:00:00Z',
                    'StackStatus': 'CREATE_COMPLETE',
                    'Description': 'Test stack',
                    'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                    'Outputs': [
                        {
                            'OutputKey': 'ClusterEndpoint',
                            'OutputValue': 'https://test-endpoint.hyperpod.amazonaws.com',
                        },
                        {
                            'OutputKey': 'ClusterArn',
                            'OutputValue': 'arn:aws:hyperpod:us-west-2:123456789012:cluster/test-cluster',
                        },
                    ],
                    'Parameters': [
                        {'ParameterKey': 'HyperPodClusterName', 'ParameterValue': 'test-cluster'},
                        {'ParameterKey': 'KubernetesVersion', 'ParameterValue': '1.31'},
                    ],
                }
            ]
        }

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(
            AwsHelper, 'create_boto3_client', return_value=mock_cfn_client
        ) as mock_create_client:
            # Call the _describe_stack method
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('cloudformation', self.TEST_REGION)

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(StackName=self.TEST_STACK_NAME)

            # Verify the result
            assert not result.isError
            assert result.stack_name == self.TEST_STACK_NAME
            assert result.stack_id == 'test-stack-id'
            assert result.creation_time == '2023-01-01T00:00:00Z'
            assert result.stack_status == 'CREATE_COMPLETE'
            assert result.outputs == {
                'ClusterEndpoint': 'https://test-endpoint.hyperpod.amazonaws.com',
                'ClusterArn': 'arn:aws:hyperpod:us-west-2:123456789012:cluster/test-cluster',
            }
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Successfully described CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_stack_success(self):
        """Test that _delete_stack deletes a stack successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'StackName': self.TEST_STACK_NAME,
                    'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                }
            ]
        }

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client):
            # Call the _delete_stack method
            result = await handler._delete_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )

            # Verify that delete_stack was called with the correct parameters
            mock_cfn_client.delete_stack.assert_called_once_with(StackName=self.TEST_STACK_NAME)

            # Verify the result
            assert not result.isError
            assert result.stack_name == self.TEST_STACK_NAME
            assert result.stack_id == 'test-stack-id'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Initiated deletion of CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_stack_not_owned(self):
        """Test that _delete_stack fails when the stack is not owned by our tool."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'StackName': self.TEST_STACK_NAME,
                    'Tags': [{'Key': 'SomeOtherTag', 'Value': 'SomeOtherValue'}],
                }
            ]
        }

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client):
            # Call the _delete_stack method
            result = await handler._delete_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )

            # Verify that delete_stack was not called
            mock_cfn_client.delete_stack.assert_not_called()

            # Verify the result
            assert result.isError
            assert result.stack_name == self.TEST_STACK_NAME
            assert result.stack_id == 'test-stack-id'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'not created by' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_hyperpod_stacks_deploy(self):
        """Test that manage_hyperpod_stacks handles the deploy operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _deploy_stack method
        mock_result = DeployStackResponse(
            isError=False,
            content=[TextContent(type='text', text='CloudFormation stack creation initiated')],
            stack_name=self.TEST_STACK_NAME,
            stack_arn='test-stack-id',
        )

        # Mock the JSON data
        mock_params_data = [
            {'ParameterKey': 'HyperPodClusterName', 'ParameterValue': 'test-cluster'},
        ]

        with (
            patch('builtins.open', mock_open(read_data=json.dumps(mock_params_data))),
            patch.object(handler, '_deploy_stack', return_value=mock_result) as mock_handler,
        ):
            # Call the manage_hyperpod_stacks method with deploy operation
            result = await handler.manage_hyperpod_stacks(
                ctx=mock_ctx,
                operation='deploy',
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                params_file='/path/to/template.json',
            )

            # Verify that _deploy_stack was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['template_params'] == mock_params_data
            assert call_args['stack_name'] == self.TEST_STACK_NAME
            assert (
                getattr(call_args['region_name'], 'default', call_args['region_name'])
                == self.TEST_REGION
            )

            # Verify the result
            assert not result.isError
            # Check specific attributes for DeployStackResponse
            assert isinstance(result, DeployStackResponse)
            assert result.stack_name == self.TEST_STACK_NAME
            assert result.stack_arn == 'test-stack-id'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'CloudFormation stack creation initiated' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_hyperpod_stacks_describe(self):
        """Test that manage_hyperpod_stacks handles the describe operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server
        handler = HyperPodStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _describe_stack method
        mock_result = DescribeStackResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully described CloudFormation stack')],
            stack_name=self.TEST_STACK_NAME,
            stack_id='test-stack-id',
            creation_time='2023-01-01T00:00:00Z',
            stack_status='CREATE_COMPLETE',
            outputs={},
        )
        with patch.object(handler, '_describe_stack', return_value=mock_result) as mock_handler:
            # Call the manage_hyperpod_stacks method with describe operation
            result = await handler.manage_hyperpod_stacks(
                ctx=mock_ctx,
                operation='describe',
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )

            # Verify that _describe_stack was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['stack_name'] == self.TEST_STACK_NAME
            assert (
                getattr(call_args['region_name'], 'default', call_args['region_name'])
                == self.TEST_REGION
            )
            assert (
                call_args['profile_name'] is None
                or getattr(call_args['profile_name'], 'default', None) is None
            )

            # Verify the result
            assert not result.isError
            # Check specific attributes for DescribeStackResponse
            assert isinstance(result, DescribeStackResponse)
            assert result.stack_name == self.TEST_STACK_NAME
            assert result.stack_id == 'test-stack-id'
            assert result.creation_time == '2023-01-01T00:00:00Z'
            assert result.stack_status == 'CREATE_COMPLETE'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Successfully described CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_hyperpod_stacks_delete(self):
        """Test that manage_hyperpod_stacks handles the delete operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _delete_stack method
        mock_result = DeleteStackResponse(
            isError=False,
            content=[TextContent(type='text', text='Initiated deletion of CloudFormation stack')],
            stack_name=self.TEST_STACK_NAME,
            stack_id='test-stack-id',
        )
        with patch.object(handler, '_delete_stack', return_value=mock_result) as mock_handler:
            # Call the manage_hyperpod_stacks method with delete operation
            result = await handler.manage_hyperpod_stacks(
                ctx=mock_ctx,
                operation='delete',
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )

            # Verify that _delete_stack was called with the correct parameters
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[1]
            assert call_args['ctx'] == mock_ctx
            assert call_args['stack_name'] == self.TEST_STACK_NAME
            assert (
                getattr(call_args['region_name'], 'default', call_args['region_name'])
                == self.TEST_REGION
            )
            assert (
                call_args['profile_name'] is None
                or getattr(call_args['profile_name'], 'default', None) is None
            )

            # Verify the result
            assert not result.isError
            # Check specific attributes for DeleteStackResponse
            assert isinstance(result, DeleteStackResponse)
            assert result.stack_name == self.TEST_STACK_NAME
            assert result.stack_id == 'test-stack-id'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Initiated deletion of CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_hyperpod_stacks_invalid_operation(self):
        """Test that manage_hyperpod_stacks handles invalid operations correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server
        handler = HyperPodStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call the manage_hyperpod_stacks method with an invalid operation
        with pytest.raises(ValueError, match='validation error'):
            await handler.manage_hyperpod_stacks(
                ctx=mock_ctx,
                operation='invalid',  # pyright: ignore[reportArgumentType]
            )

    @pytest.mark.asyncio
    async def test_manage_hyperpod_stacks_write_access_disabled(self):
        """Test that manage_hyperpod_stacks rejects mutating operations when write access is disabled."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=False
        handler = HyperPodStackHandler(mock_mcp, allow_write=False)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Test deploy operation (should be rejected when write access is disabled)
        result = await handler.manage_hyperpod_stacks(
            ctx=mock_ctx,
            operation='deploy',
            region_name=self.TEST_REGION,
            stack_name=self.TEST_STACK_NAME,
            params_file='/path/to/template.yaml',
        )

        # Verify the result
        assert result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert 'not allowed without write access' in result.content[0].text

        # Test delete operation (should be rejected when write access is disabled)
        result = await handler.manage_hyperpod_stacks(
            ctx=mock_ctx,
            region_name=self.TEST_REGION,
            stack_name=self.TEST_STACK_NAME,
            operation='delete',
        )

        # Verify the result
        assert result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert 'not allowed without write access' in result.content[0].text

        # Test describe operation (should be allowed even when write access is disabled)
        mock_result = DescribeStackResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully described CloudFormation stack')],
            stack_name=self.TEST_STACK_NAME,
            stack_id='test-stack-id',
            creation_time='2023-01-01T00:00:00Z',
            stack_status='CREATE_COMPLETE',
            outputs={},
        )
        with patch.object(handler, '_describe_stack', return_value=mock_result) as mock_handler:
            result = await handler.manage_hyperpod_stacks(
                ctx=mock_ctx,
                operation='describe',
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )

            # Verify that _describe_stack was called (operation allowed even when write access is disabled)
            mock_handler.assert_called_once()

            # Verify the result
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Successfully described CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_hyperpod_stacks_missing_parameters(self):
        """Test that manage_hyperpod_stacks handles missing parameters correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the HyperPod handler with the mock MCP server and allow_write=True
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Test missing params_file for deploy operation
        with pytest.raises(ValueError, match='params_file is required for deploy operation'):
            await handler.manage_hyperpod_stacks(
                ctx=mock_ctx,
                operation='deploy',
                region_name=self.TEST_REGION,
                stack_name=self.TEST_STACK_NAME,
                params_file=None,  # Explicitly pass None
            )

    @pytest.mark.asyncio
    async def test_deploy_stack_error_handling(self):
        """Test error handling in _deploy_stack."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        # Test CloudFormation client creation error
        with patch.object(
            AwsHelper, 'create_boto3_client', side_effect=Exception('Client creation failed')
        ):
            result = await handler._deploy_stack(
                ctx=mock_ctx,
                template_params=[],
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                cluster_orchestrator='eks',
            )
            assert result.isError
            assert 'Failed to deploy stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_describe_stack_error_handling(self):
        """Test error handling in _describe_stack."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        # Test stack ownership failure
        with patch.object(
            handler, '_ensure_stack_ownership', return_value=(False, None, 'Stack not found')
        ):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert result.isError
            assert 'Stack not found' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_stack_error_handling(self):
        """Test error handling in _delete_stack."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        # Test stack ownership failure
        with (
            patch.object(AwsHelper, 'create_boto3_client', return_value=MagicMock()),
            patch.object(
                handler, '_ensure_stack_ownership', return_value=(False, None, 'Stack not owned')
            ),
        ):
            result = await handler._delete_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert result.isError
            assert 'Stack not owned' in result.content[0].text

    def test_ensure_stack_ownership_general_exception(self):
        """Test _ensure_stack_ownership with general exception."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.side_effect = Exception('General error')

        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client):
            success, stack, error_message = handler._ensure_stack_ownership(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                operation='test',
            )
            assert success is False
            assert stack is None
            assert error_message is not None and 'Error verifying stack ownership' in error_message

    @pytest.mark.asyncio
    async def test_manage_hyperpod_stacks_general_exception(self):
        """Test general exception handling in manage_hyperpod_stacks."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        # Mock file opening to raise an exception
        with patch('builtins.open', side_effect=Exception('File error')):
            result = await handler.manage_hyperpod_stacks(
                ctx=mock_ctx,
                operation='deploy',
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                params_file='/path/to/params.json',
            )
            assert result.isError
            assert 'Error in manage_hyperpod_stacks' in result.content[0].text

    @pytest.mark.asyncio
    async def test_describe_stack_with_stack_details(self):
        """Test _describe_stack with stack that has creation time as datetime object."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        from datetime import datetime

        mock_stack = {
            'StackId': 'test-stack-id',
            'CreationTime': datetime(2023, 1, 1),
            'StackStatus': 'CREATE_COMPLETE',
            'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
            'Outputs': [],
        }

        with patch.object(
            handler, '_ensure_stack_ownership', return_value=(True, mock_stack, None)
        ):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert not result.isError
            assert result.creation_time == '2023-01-01T00:00:00'

    @pytest.mark.asyncio
    async def test_describe_stack_missing_creation_time(self):
        """Test _describe_stack with stack missing creation time."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        mock_stack = {
            'StackId': 'test-stack-id',
            'StackStatus': 'CREATE_COMPLETE',
            'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
        }

        with patch.object(
            handler, '_ensure_stack_ownership', return_value=(True, mock_stack, None)
        ):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert not result.isError
            assert result.creation_time == ''

    def test_construct_cfn_tag_mapping_node(self):
        """Test construct_cfn_tag with mapping node."""
        from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_stack_handler import (
            construct_cfn_tag,
        )

        loader = MagicMock()
        loader.construct_mapping.return_value = {'key': 'value'}

        node = yaml.MappingNode('tag', [])

        result = construct_cfn_tag(loader, 'Ref', node)
        assert result == {'Ref': {'key': 'value'}}

    def test_construct_cfn_tag_sequence_node(self):
        """Test construct_cfn_tag with sequence node."""
        from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_stack_handler import (
            construct_cfn_tag,
        )

        loader = MagicMock()
        loader.construct_sequence.return_value = ['item1', 'item2']

        node = yaml.SequenceNode('tag', [])

        result = construct_cfn_tag(loader, 'Ref', node)
        assert result == {'Ref': ['item1', 'item2']}

    def test_construct_cfn_tag_unknown_node(self):
        """Test construct_cfn_tag with unknown node type."""
        from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_stack_handler import (
            construct_cfn_tag,
        )

        loader = MagicMock()
        node = object()  # Unknown node type

        result = construct_cfn_tag(loader, 'Ref', node)
        assert result is None

    @pytest.mark.asyncio
    async def test_deploy_stack_update_exception(self):
        """Test _deploy_stack update path with exception."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        mock_cfn_client = MagicMock()
        mock_cfn_client.update_stack.side_effect = Exception('Update failed')

        # Mock stack exists and is owned
        mock_stack = {
            'StackId': 'test-id',
            'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
        }

        with (
            patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client),
            patch.object(
                handler, '_ensure_stack_ownership', return_value=(True, mock_stack, None)
            ),
        ):
            result = await handler._deploy_stack(
                ctx=mock_ctx,
                template_params=[],
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                cluster_orchestrator='eks',
            )
            assert result.isError
            assert 'Failed to deploy stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_deploy_stack_create_exception(self):
        """Test _deploy_stack create path with exception."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        mock_cfn_client = MagicMock()
        mock_cfn_client.create_stack.side_effect = Exception('Create failed')

        with (
            patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client),
            patch.object(
                handler, '_ensure_stack_ownership', side_effect=Exception('Stack check failed')
            ),
        ):
            result = await handler._deploy_stack(
                ctx=mock_ctx,
                template_params=[],
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
                cluster_orchestrator='eks',
            )
            assert result.isError
            assert 'Failed to deploy stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_describe_stack_exception(self):
        """Test _describe_stack with exception."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        with patch.object(AwsHelper, 'create_boto3_client', side_effect=Exception('Client error')):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert result.isError
            assert 'Error verifying stack ownership' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_stack_exception(self):
        """Test _delete_stack with exception."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        mock_cfn_client = MagicMock()
        mock_cfn_client.delete_stack.side_effect = Exception('Delete failed')

        mock_stack = {
            'StackId': 'test-id',
            'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
        }

        with (
            patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client),
            patch.object(
                handler, '_ensure_stack_ownership', return_value=(True, mock_stack, None)
            ),
        ):
            result = await handler._delete_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert result.isError
            assert 'Failed to delete stack' in result.content[0].text

    def test_construct_cfn_tag_scalar_node(self):
        """Test construct_cfn_tag with scalar node."""
        from awslabs.sagemaker_ai_mcp_server.sagemaker_hyperpod.hyperpod_stack_handler import (
            construct_cfn_tag,
        )

        loader = MagicMock()
        loader.construct_scalar.return_value = 'scalar_value'

        node = yaml.ScalarNode('tag', 'value')

        result = construct_cfn_tag(loader, 'Ref', node)
        assert result == {'Ref': 'scalar_value'}

    @pytest.mark.asyncio
    async def test_describe_stack_no_outputs(self):
        """Test _describe_stack with stack that has no outputs."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        mock_stack = {
            'StackId': 'test-stack-id',
            'StackStatus': 'CREATE_COMPLETE',
            'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
            # No 'Outputs' key
        }

        with patch.object(
            handler, '_ensure_stack_ownership', return_value=(True, mock_stack, None)
        ):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert not result.isError
            assert result.outputs == {}

    @pytest.mark.asyncio
    async def test_describe_stack_outputs_missing_keys(self):
        """Test _describe_stack with outputs missing OutputKey or OutputValue."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        mock_stack = {
            'StackId': 'test-stack-id',
            'StackStatus': 'CREATE_COMPLETE',
            'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
            'Outputs': [
                {'OutputKey': 'ValidKey', 'OutputValue': 'ValidValue'},
                {'OutputKey': 'MissingValue'},  # Missing OutputValue
                {'OutputValue': 'MissingKey'},  # Missing OutputKey
                {},  # Missing both
            ],
        }

        with patch.object(
            handler, '_ensure_stack_ownership', return_value=(True, mock_stack, None)
        ):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert not result.isError
            assert result.outputs == {'ValidKey': 'ValidValue'}

    @pytest.mark.asyncio
    async def test_describe_stack_missing_stack_details(self):
        """Test _describe_stack with missing stack details."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        # Test with None stack
        with patch.object(handler, '_ensure_stack_ownership', return_value=(True, None, None)):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert not result.isError
            assert result.stack_id == ''
            assert result.creation_time == ''
            assert result.stack_status == ''

    @pytest.mark.asyncio
    async def test_deploy_stack_ownership_check_exception(self):
        """Test _deploy_stack when ownership check raises exception but stack exists."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        mock_cfn_client = MagicMock()
        mock_cfn_client.create_stack.return_value = {'StackId': 'test-stack-id'}

        # First call raises exception, second call succeeds for create_stack
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client):
            # Mock ownership check to raise exception (simulating stack doesn't exist)
            with patch.object(
                handler, '_ensure_stack_ownership', side_effect=Exception('Stack check failed')
            ):
                result = await handler._deploy_stack(
                    ctx=mock_ctx,
                    template_params=[],
                    stack_name=self.TEST_STACK_NAME,
                    region_name=self.TEST_REGION,
                    cluster_orchestrator='eks',
                )
                assert not result.isError
                assert result.stack_arn == 'test-stack-id'

    @pytest.mark.asyncio
    async def test_describe_stack_creation_time_exception(self):
        """Test _describe_stack with creation time that raises exception during conversion."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp)
        mock_ctx = MagicMock(spec=Context)

        # Mock datetime object that raises exception on isoformat
        mock_datetime = MagicMock()
        mock_datetime.isoformat.side_effect = Exception('isoformat failed')

        mock_stack = {
            'StackId': 'test-stack-id',
            'CreationTime': mock_datetime,
            'StackStatus': 'CREATE_COMPLETE',
            'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
        }

        with patch.object(
            handler, '_ensure_stack_ownership', return_value=(True, mock_stack, None)
        ):
            result = await handler._describe_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert result.isError
            assert 'Failed to describe stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_deploy_stack_ownership_failure_with_stack(self):
        """Test _deploy_stack when ownership check fails but returns stack details."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        mock_cfn_client = MagicMock()
        mock_stack = {'StackId': 'existing-stack-id'}

        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client):
            # Mock ownership check to fail but return stack details
            with patch.object(
                handler, '_ensure_stack_ownership', return_value=(False, mock_stack, 'Not owned')
            ):
                result = await handler._deploy_stack(
                    ctx=mock_ctx,
                    template_params=[],
                    stack_name=self.TEST_STACK_NAME,
                    region_name=self.TEST_REGION,
                    cluster_orchestrator='eks',
                )
                assert result.isError
                assert 'Not owned' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_stack_general_exception(self):
        """Test _delete_stack with general exception after ownership check."""
        mock_mcp = MagicMock()
        handler = HyperPodStackHandler(mock_mcp, allow_write=True)
        mock_ctx = MagicMock(spec=Context)

        with patch.object(
            AwsHelper, 'create_boto3_client', side_effect=Exception('General error')
        ):
            result = await handler._delete_stack(
                ctx=mock_ctx,
                stack_name=self.TEST_STACK_NAME,
                region_name=self.TEST_REGION,
            )
            assert result.isError
            assert 'Failed to delete stack' in result.content[0].text
