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
"""Tests for the EKS MCP Server."""

import pytest
from awslabs.eks_mcp_server.cloudwatch_handler import CloudWatchHandler
from awslabs.eks_mcp_server.eks_kb_handler import EKSKnowledgeBaseHandler
from awslabs.eks_mcp_server.k8s_handler import K8sHandler
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, mock_open, patch


@pytest.mark.asyncio
async def test_server_initialization():
    # Test the server initialization by creating a server instance
    from awslabs.eks_mcp_server.server import create_server

    # Create a server instance
    server = create_server()

    # Test that the server is initialized with the correct name
    assert server.name == 'awslabs.eks-mcp-server'
    # Test that the server has the correct instructions
    assert server.instructions is not None and 'EKS MCP Server' in server.instructions
    # Test that the server has the correct dependencies
    assert 'pydantic' in server.dependencies
    assert 'loguru' in server.dependencies
    assert 'boto3' in server.dependencies
    # These dependencies should be added for K8sHandler and CloudWatchHandler
    assert 'kubernetes' in server.dependencies
    assert 'requests' in server.dependencies
    assert 'pyyaml' in server.dependencies
    assert 'cachetools' in server.dependencies


@pytest.mark.asyncio
async def test_command_line_args():
    """Test that the command-line arguments are parsed correctly."""
    import argparse
    from awslabs.eks_mcp_server.server import main

    # Mock the ArgumentParser.parse_args method to return known args
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        # Test with default args (read-only mode by default)
        mock_parse_args.return_value = argparse.Namespace(
            sse=False, port=6274, allow_write=False, allow_sensitive_data_access=False
        )

        # Mock AWS client creation
        mock_client = MagicMock()
        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_client,
        ):
            # Mock create_server to return a mock server
            mock_server = MagicMock()
            with patch('awslabs.eks_mcp_server.server.create_server', return_value=mock_server):
                # Call the main function
                main()

                # Verify that parse_args was called
                mock_parse_args.assert_called_once()

                # Verify that run was called with the correct parameters
                mock_server.run.assert_called_once()

    # Test with write access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            sse=False, port=6274, allow_write=True, allow_sensitive_data_access=False
        )

        # Mock AWS client creation
        mock_client = MagicMock()
        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_client,
        ):
            # Mock create_server to return a mock server
            mock_server = MagicMock()
            with patch('awslabs.eks_mcp_server.server.create_server', return_value=mock_server):
                # Mock the handler initialization to verify allow_write is passed
                with patch(
                    'awslabs.eks_mcp_server.server.CloudWatchHandler'
                ) as mock_cloudwatch_handler:
                    with patch(
                        'awslabs.eks_mcp_server.server.EksStackHandler'
                    ) as mock_eks_stack_handler:
                        with patch('awslabs.eks_mcp_server.server.K8sHandler') as mock_k8s_handler:
                            with patch(
                                'awslabs.eks_mcp_server.server.IAMHandler'
                            ) as mock_iam_handler:
                                # Call the main function
                                main()

                                # Verify that parse_args was called
                                mock_parse_args.assert_called_once()

                                # Verify that the handlers were initialized with correct parameters
                                mock_cloudwatch_handler.assert_called_once_with(mock_server, False)
                                mock_eks_stack_handler.assert_called_once_with(mock_server, True)
                                mock_k8s_handler.assert_called_once_with(mock_server, True, False)
                                mock_iam_handler.assert_called_once_with(mock_server, True)

                                # Verify that run was called
                                mock_server.run.assert_called_once()

    # Test with sensitive data access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            sse=False, port=6274, allow_write=False, allow_sensitive_data_access=True
        )

        # Mock AWS client creation
        mock_client = MagicMock()
        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_client,
        ):
            # Mock create_server to return a mock server
            mock_server = MagicMock()
            with patch('awslabs.eks_mcp_server.server.create_server', return_value=mock_server):
                # Mock the handler initialization to verify allow_sensitive_data_access is passed
                with patch(
                    'awslabs.eks_mcp_server.server.CloudWatchHandler'
                ) as mock_cloudwatch_handler:
                    with patch(
                        'awslabs.eks_mcp_server.server.EksStackHandler'
                    ) as mock_eks_stack_handler:
                        with patch('awslabs.eks_mcp_server.server.K8sHandler') as mock_k8s_handler:
                            with patch(
                                'awslabs.eks_mcp_server.server.IAMHandler'
                            ) as mock_iam_handler:
                                # Call the main function
                                main()

                                # Verify that parse_args was called
                                mock_parse_args.assert_called_once()

                                # Verify that the handlers were initialized with correct parameters
                                mock_cloudwatch_handler.assert_called_once_with(mock_server, True)
                                mock_eks_stack_handler.assert_called_once_with(mock_server, False)
                                mock_k8s_handler.assert_called_once_with(mock_server, False, True)
                                mock_iam_handler.assert_called_once_with(mock_server, False)

                                # Verify that run was called
                                mock_server.run.assert_called_once()

    # Test with both write access and sensitive data access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            sse=False, port=6274, allow_write=True, allow_sensitive_data_access=True
        )

        # Mock AWS client creation
        mock_client = MagicMock()
        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_client,
        ):
            # Mock create_server to return a mock server
            mock_server = MagicMock()
            with patch('awslabs.eks_mcp_server.server.create_server', return_value=mock_server):
                # Mock the handler initialization to verify both flags are passed
                with patch(
                    'awslabs.eks_mcp_server.server.CloudWatchHandler'
                ) as mock_cloudwatch_handler:
                    with patch(
                        'awslabs.eks_mcp_server.server.EksStackHandler'
                    ) as mock_eks_stack_handler:
                        with patch('awslabs.eks_mcp_server.server.K8sHandler') as mock_k8s_handler:
                            with patch(
                                'awslabs.eks_mcp_server.server.IAMHandler'
                            ) as mock_iam_handler:
                                # Call the main function
                                main()

                                # Verify that parse_args was called
                                mock_parse_args.assert_called_once()

                                # Verify that the handlers were initialized with both flags
                                mock_cloudwatch_handler.assert_called_once_with(mock_server, True)
                                mock_eks_stack_handler.assert_called_once_with(mock_server, True)
                                mock_k8s_handler.assert_called_once_with(mock_server, True, True)
                                mock_iam_handler.assert_called_once_with(mock_server, True)

                                # Verify that run was called
                                mock_server.run.assert_called_once()


@pytest.mark.asyncio
async def test_k8s_handler_initialization_default():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with the mock MCP server (default allow_write=False, allow_sensitive_data_access=False)
    K8sHandler(mock_mcp)

    # Verify that the tools were registered
    assert mock_mcp.tool.call_count == 7

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all tools are registered
    assert 'list_k8s_resources' in tool_names
    assert 'manage_k8s_resource' in tool_names
    assert 'get_pod_logs' in tool_names
    assert 'get_k8s_events' in tool_names
    assert 'apply_yaml' in tool_names
    assert 'generate_app_manifest' in tool_names


@pytest.mark.asyncio
async def test_k8s_handler_initialization_write_access_disabled():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with the mock MCP server with allow_write=False
    K8sHandler(mock_mcp, allow_write=False)

    # Verify that all tools are registered
    assert mock_mcp.tool.call_count == 7

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all tools are registered
    assert 'list_k8s_resources' in tool_names
    assert 'manage_k8s_resource' in tool_names
    assert 'get_pod_logs' in tool_names
    assert 'get_k8s_events' in tool_names
    assert 'list_api_versions' in tool_names
    assert 'apply_yaml' in tool_names
    assert 'generate_app_manifest' in tool_names


@pytest.mark.asyncio
async def test_k8s_handler_initialization_write_access_enabled():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with the mock MCP server with allow_write=True
    K8sHandler(mock_mcp, allow_write=True)

    # Verify that all tools were registered (now includes list_api_versions)
    assert mock_mcp.tool.call_count == 7

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all tools are registered
    assert 'list_k8s_resources' in tool_names
    assert 'manage_k8s_resource' in tool_names
    assert 'get_pod_logs' in tool_names
    assert 'get_k8s_events' in tool_names
    assert 'apply_yaml' in tool_names
    assert 'generate_app_manifest' in tool_names


@pytest.mark.asyncio
async def test_k8s_handler_initialization_sensitive_data_access_enabled():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with the mock MCP server with allow_sensitive_data_access=True
    K8sHandler(mock_mcp, allow_sensitive_data_access=True)

    # Verify that all tools are registered
    assert mock_mcp.tool.call_count == 7

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all tools are registered
    assert 'list_k8s_resources' in tool_names
    assert 'manage_k8s_resource' in tool_names
    assert 'get_pod_logs' in tool_names
    assert 'get_k8s_events' in tool_names
    assert 'apply_yaml' in tool_names
    assert 'generate_app_manifest' in tool_names


@pytest.mark.asyncio
async def test_k8s_handler_initialization_both_flags_enabled():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with the mock MCP server with both flags enabled
    K8sHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=True)

    # Verify that all tools are registered
    assert mock_mcp.tool.call_count == 7

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all tools are registered
    assert 'list_k8s_resources' in tool_names
    assert 'manage_k8s_resource' in tool_names
    assert 'get_pod_logs' in tool_names
    assert 'get_k8s_events' in tool_names
    assert 'apply_yaml' in tool_names
    assert 'generate_app_manifest' in tool_names


@pytest.mark.asyncio
async def test_eks_kb_handler_initialization():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the EKS Knowledge Base handler with the mock MCP server
    EKSKnowledgeBaseHandler(mock_mcp)

    # Verify that the tool was registered
    mock_mcp.tool.assert_called_once()
    call_args = mock_mcp.tool.call_args
    assert call_args[1]['name'] == 'search_eks_troubleshoot_guide'


@pytest.mark.asyncio
async def test_cloudwatch_handler_initialization():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the CloudWatch handler with the mock MCP server (default allow_sensitive_data_access=False)
    CloudWatchHandler(mock_mcp)

    # Verify that all tools are registered
    assert mock_mcp.tool.call_count == 2

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all tools are registered
    assert 'get_cloudwatch_metrics' in tool_names
    assert 'get_cloudwatch_logs' in tool_names


@pytest.mark.asyncio
async def test_cloudwatch_handler_initialization_with_sensitive_data_access():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the CloudWatch handler with the mock MCP server and allow_sensitive_data_access=True
    CloudWatchHandler(mock_mcp, allow_sensitive_data_access=True)

    # Verify that all tools were registered
    assert mock_mcp.tool.call_count == 2

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Verify that get_cloudwatch_logs was registered
    assert call_args_list[0][1]['name'] == 'get_cloudwatch_logs'

    # Verify that get_cloudwatch_metrics was registered
    assert call_args_list[1][1]['name'] == 'get_cloudwatch_metrics'


@pytest.mark.asyncio
async def test_apply_yaml():
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with the mock MCP server with write access enabled
    handler = K8sHandler(mock_mcp, allow_write=True)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Patch the necessary methods
    with (
        patch(
            'builtins.open',
            mock_open(
                read_data="""
    apiVersion: v1
    kind: Namespace
    metadata:
      name: test-namespace
    """
            ),
        ) as mocked_open,
        patch.object(handler, 'get_client') as mock_get_client,
    ):
        # Mock the K8sApis instance and its apply_from_yaml method
        mock_k8s_apis = MagicMock()
        mock_k8s_apis.apply_from_yaml.return_value = (
            [],
            1,
            0,
        )  # (results, created_count, updated_count)
        mock_get_client.return_value = mock_k8s_apis

        # Call the apply_yaml method
        result = await handler.apply_yaml(
            mock_ctx,
            yaml_path='/path/to/manifest.yaml',
            cluster_name='test-cluster',
            namespace='test-namespace',
            force=True,
        )

        # Verify the result
        assert not result.isError
        assert len(result.content) == 1
        assert result.content[0].type == 'text'
        assert 'Successfully applied all resources' in result.content[0].text

        # Verify that open was called with the correct path
        mocked_open.assert_called_once_with('/path/to/manifest.yaml', 'r')

        # Verify that apply_from_yaml was called with the correct parameters
        mock_k8s_apis.apply_from_yaml.assert_called_once()
        args, kwargs = mock_k8s_apis.apply_from_yaml.call_args
        assert (
            kwargs['namespace'] == 'test-namespace'
        )  # Verify namespace parameter is passed correctly
        assert kwargs['force'] is True  # Verify force parameter is passed correctly


@pytest.mark.asyncio
async def test_apply_yaml_with_secret_blocked():
    """Test that apply_yaml blocks Secret resources when sensitive data access is disabled."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with write access but no sensitive data access
    handler = K8sHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=False)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # YAML content with a Secret resource
    yaml_content = """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
data:
  password: dGVzdA==
"""

    # Mock the necessary methods
    with patch('os.path.isabs', return_value=True):
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            # Mock the K8sApis instance
            mock_k8s_apis = MagicMock()
            # Mock apply_from_yaml to check for Secret resources
            mock_k8s_apis.apply_from_yaml.side_effect = Exception(
                'Secret resources require --allow-sensitive-data-access flag'
            )

            with patch.object(handler, 'get_client', return_value=mock_k8s_apis):
                # Call the apply_yaml method
                result = await handler.apply_yaml(
                    mock_ctx,
                    yaml_path='/path/to/secret.yaml',
                    cluster_name='test-cluster',
                    namespace='test-namespace',
                    force=True,
                )

                # Verify the result is an error
                assert result.isError
                assert len(result.content) == 1
                assert result.content[0].type == 'text'
                assert (
                    'Secret resources require --allow-sensitive-data-access flag'
                    in result.content[0].text
                )


@pytest.mark.asyncio
async def test_manage_k8s_resource_secret_blocked():
    """Test that manage_k8s_resource blocks Secret resources when sensitive data access is disabled."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with write access but no sensitive data access
    handler = K8sHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=False)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the manage_k8s_resource method with a Secret
    result = await handler.manage_k8s_resource(
        mock_ctx,
        operation='read',
        cluster_name='test-cluster',
        kind='Secret',
        api_version='v1',
        name='test-secret',
        namespace='default',
    )

    # Verify the result is an error
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert (
        'Access to Kubernetes Secrets requires --allow-sensitive-data-access flag'
        in result.content[0].text
    )


@pytest.mark.asyncio
async def test_get_pod_logs_blocked():
    """Test that get_pod_logs is blocked when sensitive data access is disabled."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with sensitive data access disabled
    handler = K8sHandler(mock_mcp, allow_sensitive_data_access=False)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the get_pod_logs method with explicit parameters to avoid Field object issues
    result = await handler.get_pod_logs(
        mock_ctx,
        cluster_name='test-cluster',
        namespace='default',
        pod_name='test-pod',
        container_name=None,
        since_seconds=None,
        tail_lines=100,
        limit_bytes=10240,
    )

    # Verify the result is an error
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert (
        'Access to pod logs requires --allow-sensitive-data-access flag' in result.content[0].text
    )


@pytest.mark.asyncio
async def test_get_k8s_events_blocked():
    """Test that get_k8s_events is blocked when sensitive data access is disabled."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the K8s handler with sensitive data access disabled
    handler = K8sHandler(mock_mcp, allow_sensitive_data_access=False)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the get_k8s_events method
    result = await handler.get_k8s_events(
        mock_ctx,
        cluster_name='test-cluster',
        kind='Pod',
        name='test-pod',
        namespace='default',
    )

    # Verify the result is an error
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert (
        'Access to Kubernetes events requires --allow-sensitive-data-access flag'
        in result.content[0].text
    )


@pytest.mark.asyncio
async def test_get_cloudwatch_logs_blocked():
    """Test that get_cloudwatch_logs is blocked when sensitive data access is disabled."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Initialize the CloudWatch handler with sensitive data access disabled
    handler = CloudWatchHandler(mock_mcp, allow_sensitive_data_access=False)

    # Create a mock context
    mock_ctx = MagicMock(spec=Context)

    # Call the get_cloudwatch_logs method
    result = await handler.get_cloudwatch_logs(
        mock_ctx,
        resource_type='pod',
        resource_name='test-pod',
        cluster_name='test-cluster',
        log_type='application',
    )

    # Verify the result is an error
    assert result.isError
    assert len(result.content) == 1
    assert result.content[0].type == 'text'
    assert (
        'Access to CloudWatch logs requires --allow-sensitive-data-access flag'
        in result.content[0].text
    )
