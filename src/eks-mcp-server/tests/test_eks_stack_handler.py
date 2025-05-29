# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
# ruff: noqa: D101, D102, D103
"""Tests for the EKS Stack Handler."""

import pytest
import yaml
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.consts import (
    CFN_CAPABILITY_IAM,
    CFN_ON_FAILURE_DELETE,
    CFN_STACK_TAG_KEY,
    CFN_STACK_TAG_VALUE,
)
from awslabs.eks_mcp_server.eks_stack_handler import EksStackHandler
from awslabs.eks_mcp_server.models import (
    DeleteStackResponse,
    DeployStackResponse,
    DescribeStackResponse,
    GenerateTemplateResponse,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, mock_open, patch


class TestEksStackHandler:
    """Tests for the EksStackHandler class."""

    def test_init_default(self):
        """Test that the handler is initialized correctly and registers its tools with default allow_write=False."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_write is False

        # Verify that the manage_eks_stacks tool was registered
        mock_mcp.tool.assert_called_once()
        args, kwargs = mock_mcp.tool.call_args
        assert kwargs['name'] == 'manage_eks_stacks'

    def test_init_write_access_disabled(self):
        """Test that the handler is initialized correctly with allow_write=False."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server and allow_write=False
        handler = EksStackHandler(mock_mcp, allow_write=False)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_write is False

        # Verify that the manage_eks_stacks tool was registered
        mock_mcp.tool.assert_called_once()
        args, kwargs = mock_mcp.tool.call_args
        assert kwargs['name'] == 'manage_eks_stacks'

    @pytest.mark.asyncio
    async def test_deploy_stack_success(self):
        """Test that _deploy_stack deploys a stack successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

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
                        template_file='/path/to/template.yaml',
                        stack_name='eks-test-cluster-stack',
                        cluster_name='test-cluster',
                    )

                # Verify that AwsHelper.create_boto3_client was called with the correct parameters
                # Since we're mocking _ensure_stack_ownership, it's only called once in _deploy_stack
                assert mock_create_client.call_count == 1
                args, kwargs = mock_create_client.call_args
                assert args[0] == 'cloudformation'

                # Verify that create_stack was called with the correct parameters
                mock_cfn_client.create_stack.assert_called_once()
                args, kwargs = mock_cfn_client.create_stack.call_args
                assert kwargs['StackName'] == 'eks-test-cluster-stack'
                assert kwargs['TemplateBody'] == mock_template_content
                assert kwargs['Capabilities'] == [CFN_CAPABILITY_IAM]
                assert kwargs['OnFailure'] == CFN_ON_FAILURE_DELETE
                assert kwargs['Tags'] == [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}]

                # Verify the result
                assert not result.isError
                assert result.stack_name == 'eks-test-cluster-stack'
                assert result.stack_arn == 'test-stack-id'
                assert result.cluster_name == 'test-cluster'
                assert len(result.content) == 1
                assert result.content[0].type == 'text'
                assert 'CloudFormation stack creation initiated' in result.content[0].text

    def test_ensure_stack_ownership_owned_stack(self):
        """Test that _ensure_stack_ownership correctly identifies a stack owned by our tool."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

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
                ctx=mock_ctx, stack_name='eks-test-cluster-stack', operation='update'
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            assert mock_create_client.call_count == 1
            args, kwargs = mock_create_client.call_args
            assert args[0] == 'cloudformation'

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(
                StackName='eks-test-cluster-stack'
            )

            # Verify the result
            assert success is True
            assert stack == mock_cfn_client.describe_stacks.return_value['Stacks'][0]
            assert error_message is None

    def test_ensure_stack_ownership_not_owned_stack(self):
        """Test that _ensure_stack_ownership correctly identifies a stack not owned by our tool."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

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
                ctx=mock_ctx, stack_name='eks-test-cluster-stack', operation='update'
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('cloudformation')

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(
                StackName='eks-test-cluster-stack'
            )

            # Verify the result
            assert success is False
            assert stack == mock_cfn_client.describe_stacks.return_value['Stacks'][0]
            assert error_message is not None
            assert 'not created by' in error_message

    def test_ensure_stack_ownership_stack_not_found(self):
        """Test that _ensure_stack_ownership correctly handles a stack that doesn't exist."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

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
                ctx=mock_ctx, stack_name='eks-test-cluster-stack', operation='update'
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('cloudformation')

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(
                StackName='eks-test-cluster-stack'
            )

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

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

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
                    template_file='/path/to/template.yaml',
                    stack_name='eks-test-cluster-stack',
                    cluster_name='test-cluster',
                )

                # Verify that AwsHelper.create_boto3_client was called with the correct parameters
                # Note: It's called twice now - once for _ensure_stack_ownership and once for _deploy_stack
                assert mock_aws_helper.call_count == 2
                mock_aws_helper.assert_any_call('cloudformation')

                # Verify that update_stack was called with the correct parameters
                mock_cfn_client.update_stack.assert_called_once()
                args, kwargs = mock_cfn_client.update_stack.call_args
                assert kwargs['StackName'] == 'eks-test-cluster-stack'
                assert kwargs['TemplateBody'] == mock_template_content
                assert kwargs['Capabilities'] == [CFN_CAPABILITY_IAM]
                assert kwargs['Tags'] == [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}]

                # Verify the result
                assert not result.isError
                assert result.stack_name == 'eks-test-cluster-stack'
                assert result.stack_arn == 'test-stack-id'
                assert result.cluster_name == 'test-cluster'
                assert len(result.content) == 1
                assert result.content[0].type == 'text'
                assert 'CloudFormation stack update initiated' in result.content[0].text

    @pytest.mark.asyncio
    async def test_describe_stack_success(self):
        """Test that _describe_stack returns stack details successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'StackName': 'eks-test-cluster-stack',
                    'CreationTime': '2023-01-01T00:00:00Z',
                    'StackStatus': 'CREATE_COMPLETE',
                    'Description': 'Test stack',
                    'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                    'Outputs': [
                        {
                            'OutputKey': 'ClusterEndpoint',
                            'OutputValue': 'https://test-endpoint.eks.amazonaws.com',
                        },
                        {
                            'OutputKey': 'ClusterArn',
                            'OutputValue': 'arn:aws:eks:us-west-2:123456789012:cluster/test-cluster',
                        },
                    ],
                    'Parameters': [
                        {'ParameterKey': 'ClusterName', 'ParameterValue': 'test-cluster'},
                        {'ParameterKey': 'KubernetesVersion', 'ParameterValue': '1.32'},
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
                stack_name='eks-test-cluster-stack',
                cluster_name='test-cluster',
            )

            # Verify that AwsHelper.create_boto3_client was called with the correct parameters
            mock_create_client.assert_called_once_with('cloudformation')

            # Verify that describe_stacks was called with the correct parameters
            mock_cfn_client.describe_stacks.assert_called_once_with(
                StackName='eks-test-cluster-stack'
            )

            # Verify the result
            assert not result.isError
            assert result.stack_name == 'eks-test-cluster-stack'
            assert result.stack_id == 'test-stack-id'
            assert result.cluster_name == 'test-cluster'
            assert result.creation_time == '2023-01-01T00:00:00Z'
            assert result.stack_status == 'CREATE_COMPLETE'
            assert result.outputs == {
                'ClusterEndpoint': 'https://test-endpoint.eks.amazonaws.com',
                'ClusterArn': 'arn:aws:eks:us-west-2:123456789012:cluster/test-cluster',
            }
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Successfully described CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_stack_success(self):
        """Test that _delete_stack deletes a stack successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'StackName': 'eks-test-cluster-stack',
                    'Tags': [{'Key': CFN_STACK_TAG_KEY, 'Value': CFN_STACK_TAG_VALUE}],
                }
            ]
        }

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client):
            # Call the _delete_stack method
            result = await handler._delete_stack(
                ctx=mock_ctx,
                stack_name='eks-test-cluster-stack',
                cluster_name='test-cluster',
            )

            # Verify that delete_stack was called with the correct parameters
            mock_cfn_client.delete_stack.assert_called_once_with(
                StackName='eks-test-cluster-stack'
            )

            # Verify the result
            assert not result.isError
            assert result.stack_name == 'eks-test-cluster-stack'
            assert result.stack_id == 'test-stack-id'
            assert result.cluster_name == 'test-cluster'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Initiated deletion of CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_stack_not_owned(self):
        """Test that _delete_stack fails when the stack is not owned by our tool."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Create a mock CloudFormation client
        mock_cfn_client = MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            'Stacks': [
                {
                    'StackId': 'test-stack-id',
                    'StackName': 'eks-test-cluster-stack',
                    'Tags': [{'Key': 'SomeOtherTag', 'Value': 'SomeOtherValue'}],
                }
            ]
        }

        # Mock the AwsHelper.create_boto3_client method to return our mock client
        with patch.object(AwsHelper, 'create_boto3_client', return_value=mock_cfn_client):
            # Call the _delete_stack method
            result = await handler._delete_stack(
                ctx=mock_ctx,
                stack_name='eks-test-cluster-stack',
                cluster_name='test-cluster',
            )

            # Verify that delete_stack was not called
            mock_cfn_client.delete_stack.assert_not_called()

            # Verify the result
            assert result.isError
            assert result.stack_name == 'eks-test-cluster-stack'
            assert result.stack_id == 'test-stack-id'
            assert result.cluster_name == 'test-cluster'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'not created by' in result.content[0].text

    @pytest.mark.asyncio
    async def test_generate_template_success(self):
        """Test that _generate_template generates a template successfully."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the open function to return a mock file
        mock_template_content = """
        Parameters:
          ClusterName:
            Type: String
            Default: my-cluster
        """
        mock_yaml_content = yaml.safe_load(mock_template_content)

        # Mock the necessary functions
        with (
            patch('builtins.open', mock_open(read_data=mock_template_content)),
            patch('os.path.dirname', return_value='/mock/path'),
            patch('os.path.join', return_value='/mock/path/template.yaml'),
            patch('os.makedirs', return_value=None),
            patch('yaml.safe_load', return_value=mock_yaml_content),
            patch('yaml.dump', return_value=mock_template_content),
        ):
            # Call the _generate_template method
            result = await handler._generate_template(
                ctx=mock_ctx,
                template_path='/path/to/output/template.yaml',
                cluster_name='test-cluster',
            )

            # Verify the result
            assert not result.isError
            assert result.template_path == '/path/to/output/template.yaml'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'template generated' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_eks_stacks_generate(self):
        """Test that manage_eks_stacks handles the generate operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _generate_template method
        mock_result = GenerateTemplateResponse(
            isError=False,
            content=[TextContent(type='text', text='Generated CloudFormation template')],
            template_path='/path/to/output/template.yaml',
        )
        with patch.object(handler, '_generate_template', return_value=mock_result) as mock_handler:
            # Call the manage_eks_stacks method with generate operation
            result = await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='generate',
                template_file='/path/to/output/template.yaml',
                cluster_name='test-cluster',
            )

            # Verify that _generate_template was called with the correct parameters
            mock_handler.assert_called_once_with(
                ctx=mock_ctx,
                template_path='/path/to/output/template.yaml',
                cluster_name='test-cluster',
            )

            # Verify the result is the same as the mock result
            assert result is mock_result
            assert not result.isError
            # Check specific attributes for GenerateTemplateResponse
            assert isinstance(result, GenerateTemplateResponse)
            assert result.template_path == '/path/to/output/template.yaml'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Generated CloudFormation template' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_eks_stacks_deploy(self):
        """Test that manage_eks_stacks handles the deploy operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _deploy_stack method
        mock_result = DeployStackResponse(
            isError=False,
            content=[TextContent(type='text', text='CloudFormation stack creation initiated')],
            stack_name='eks-test-cluster-stack',
            stack_arn='test-stack-id',
            cluster_name='test-cluster',
        )
        with patch.object(handler, '_deploy_stack', return_value=mock_result) as mock_handler:
            # Call the manage_eks_stacks method with deploy operation
            result = await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='deploy',
                template_file='/path/to/template.yaml',
                cluster_name='test-cluster',
            )

            # Verify that _deploy_stack was called with the correct parameters
            mock_handler.assert_called_once_with(
                ctx=mock_ctx,
                template_file='/path/to/template.yaml',
                stack_name='eks-test-cluster-stack',
                cluster_name='test-cluster',
            )

            # Verify the result
            assert not result.isError
            # Check specific attributes for DeployStackResponse
            assert isinstance(result, DeployStackResponse)
            assert result.stack_name == 'eks-test-cluster-stack'
            assert result.stack_arn == 'test-stack-id'
            assert result.cluster_name == 'test-cluster'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'CloudFormation stack creation initiated' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_eks_stacks_describe(self):
        """Test that manage_eks_stacks handles the describe operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _describe_stack method
        mock_result = DescribeStackResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully described CloudFormation stack')],
            stack_name='eks-test-cluster-stack',
            stack_id='test-stack-id',
            cluster_name='test-cluster',
            creation_time='2023-01-01T00:00:00Z',
            stack_status='CREATE_COMPLETE',
            outputs={},
        )
        with patch.object(handler, '_describe_stack', return_value=mock_result) as mock_handler:
            # Call the manage_eks_stacks method with describe operation
            result = await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='describe',
                cluster_name='test-cluster',
            )

            # Verify that _describe_stack was called with the correct parameters
            mock_handler.assert_called_once_with(
                ctx=mock_ctx, stack_name='eks-test-cluster-stack', cluster_name='test-cluster'
            )

            # Verify the result
            assert not result.isError
            # Check specific attributes for DescribeStackResponse
            assert isinstance(result, DescribeStackResponse)
            assert result.stack_name == 'eks-test-cluster-stack'
            assert result.stack_id == 'test-stack-id'
            assert result.cluster_name == 'test-cluster'
            assert result.creation_time == '2023-01-01T00:00:00Z'
            assert result.stack_status == 'CREATE_COMPLETE'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Successfully described CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_eks_stacks_delete(self):
        """Test that manage_eks_stacks handles the delete operation correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Mock the _delete_stack method
        mock_result = DeleteStackResponse(
            isError=False,
            content=[TextContent(type='text', text='Initiated deletion of CloudFormation stack')],
            stack_name='eks-test-cluster-stack',
            stack_id='test-stack-id',
            cluster_name='test-cluster',
        )
        with patch.object(handler, '_delete_stack', return_value=mock_result) as mock_handler:
            # Call the manage_eks_stacks method with delete operation
            result = await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='delete',
                cluster_name='test-cluster',
            )

            # Verify that _delete_stack was called with the correct parameters
            mock_handler.assert_called_once_with(
                ctx=mock_ctx, stack_name='eks-test-cluster-stack', cluster_name='test-cluster'
            )

            # Verify the result
            assert not result.isError
            # Check specific attributes for DeleteStackResponse
            assert isinstance(result, DeleteStackResponse)
            assert result.stack_name == 'eks-test-cluster-stack'
            assert result.stack_id == 'test-stack-id'
            assert result.cluster_name == 'test-cluster'
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Initiated deletion of CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_eks_stacks_invalid_operation(self):
        """Test that manage_eks_stacks handles invalid operations correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call the manage_eks_stacks method with an invalid operation
        result = await handler.manage_eks_stacks(
            ctx=mock_ctx,
            operation='invalid',
            cluster_name='test-cluster',
        )

        # Verify the result
        assert result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert 'not allowed without write access' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_eks_stacks_write_access_disabled(self):
        """Test that manage_eks_stacks rejects mutating operations when write access is disabled."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server and allow_write=False
        handler = EksStackHandler(mock_mcp, allow_write=False)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Test generate operation (should be rejected when write access is disabled)
        result = await handler.manage_eks_stacks(
            ctx=mock_ctx,
            operation='generate',
            template_file='/path/to/template.yaml',
            cluster_name='test-cluster',
        )

        # Verify the result
        assert result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert 'not allowed without write access' in result.content[0].text

        # Test deploy operation (should be rejected when write access is disabled)
        result = await handler.manage_eks_stacks(
            ctx=mock_ctx,
            operation='deploy',
            template_file='/path/to/template.yaml',
            cluster_name='test-cluster',
        )

        # Verify the result
        assert result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert 'not allowed without write access' in result.content[0].text

        # Test delete operation (should be rejected when write access is disabled)
        result = await handler.manage_eks_stacks(
            ctx=mock_ctx,
            operation='delete',
            cluster_name='test-cluster',
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
            stack_name='eks-test-cluster-stack',
            stack_id='test-stack-id',
            cluster_name='test-cluster',
            creation_time='2023-01-01T00:00:00Z',
            stack_status='CREATE_COMPLETE',
            outputs={},
        )
        with patch.object(handler, '_describe_stack', return_value=mock_result) as mock_handler:
            result = await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='describe',
                cluster_name='test-cluster',
            )

            # Verify that _describe_stack was called (operation allowed even when write access is disabled)
            mock_handler.assert_called_once()

            # Verify the result
            assert not result.isError
            assert len(result.content) == 1
            assert result.content[0].type == 'text'
            assert 'Successfully described CloudFormation stack' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_eks_stacks_missing_parameters(self):
        """Test that manage_eks_stacks handles missing parameters correctly."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS handler with the mock MCP server
        handler = EksStackHandler(mock_mcp, allow_write=True)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Test missing template_file for generate operation
        with pytest.raises(ValueError, match='template_file is required for generate operation'):
            await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='generate',
                cluster_name='test-cluster',
                template_file=None,  # Explicitly pass None
            )

        # Test missing cluster_name for generate operation
        with pytest.raises(ValueError, match='cluster_name is required for generate operation'):
            await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='generate',
                template_file='/path/to/template.yaml',
                cluster_name=None,  # Explicitly pass None
            )

        # Test missing template_file for deploy operation
        with pytest.raises(ValueError, match='template_file is required for deploy operation'):
            await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='deploy',
                cluster_name='test-cluster',
                template_file=None,  # Explicitly pass None
            )

        # Test missing cluster_name for deploy operation
        with pytest.raises(ValueError, match='cluster_name is required for deploy operation'):
            await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='deploy',
                template_file='/path/to/template.yaml',
                cluster_name=None,  # Explicitly pass None
            )

        # Test missing cluster_name for describe operation
        with pytest.raises(ValueError, match='cluster_name is required for describe operation'):
            await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='describe',
                cluster_name=None,  # Explicitly pass None
            )

        # Test missing cluster_name for delete operation
        with pytest.raises(ValueError, match='cluster_name is required for delete operation'):
            await handler.manage_eks_stacks(
                ctx=mock_ctx,
                operation='delete',
                cluster_name=None,  # Explicitly pass None
            )
