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
# ruff: noqa: D101, D102, D103, E402
"""Tests for the HyperPod MCP Server."""

# Mock the imports that might cause issues
import pytest
import sys
from awslabs.sagemaker_hyperpod_mcp_server.hyperpod_cluster_node_handler import (
    HyperPodClusterNodeHandler,
)
from awslabs.sagemaker_hyperpod_mcp_server.hyperpod_stack_handler import HyperPodStackHandler
from unittest.mock import MagicMock, patch


# Mock modules that might not be installed
sys.modules['requests_auth_aws_sigv4'] = MagicMock()
sys.modules['requests'] = MagicMock()


@pytest.mark.asyncio
async def test_server_initialization():
    # Test the server initialization by creating a server instance
    from awslabs.sagemaker_hyperpod_mcp_server.server import create_server

    # Create a server instance
    server = create_server()

    # Test that the server is initialized with the correct name
    assert server.name == 'awslabs.sagemaker-hyperpod-mcp-server'
    # Test that the server has the correct instructions
    assert (
        server.instructions is not None
        and 'Amazon SageMaker HyperPod MCP Server' in server.instructions
    )
    # Test that the server has the correct dependencies
    assert 'pydantic' in server.dependencies
    assert 'loguru' in server.dependencies
    assert 'boto3' in server.dependencies
    assert 'requests' in server.dependencies
    assert 'pyyaml' in server.dependencies
    assert 'cachetools' in server.dependencies


@pytest.mark.asyncio
async def test_command_line_args():
    """Test that the command-line arguments are parsed correctly."""
    import argparse
    from awslabs.sagemaker_hyperpod_mcp_server.server import main

    # Mock the ArgumentParser.parse_args method to return known args
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        # Test with default args (read-only mode by default)
        mock_parse_args.return_value = argparse.Namespace(
            allow_write=False, allow_sensitive_data_access=False
        )

        # Mock create_server to return a mock server
        mock_server = MagicMock()
        with patch(
            'awslabs.sagemaker_hyperpod_mcp_server.server.create_server', return_value=mock_server
        ):
            # Mock the handler initialization to verify allow_write is passed
            with patch(
                'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler'
            ) as mock_hyperpod_cluster_node_handler:
                with patch(
                    'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler'
                ) as mock_hyperpod_stack_handler:
                    # Call the main function
                    main()

                    # Verify that parse_args was called
                    mock_parse_args.assert_called_once()

                    # Verify that the handlers were initialized with correct parameters
                    mock_hyperpod_cluster_node_handler.assert_called_once_with(
                        mock_server, False, False
                    )
                    mock_hyperpod_stack_handler.assert_called_once_with(mock_server, False)

                    # Verify that run was called
                    mock_server.run.assert_called_once()

    # Test with write access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            allow_write=True, allow_sensitive_data_access=False
        )

        # Mock create_server to return a mock server
        mock_server = MagicMock()
        with patch(
            'awslabs.sagemaker_hyperpod_mcp_server.server.create_server', return_value=mock_server
        ):
            # Mock the handler initialization to verify allow_write is passed
            with patch(
                'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler'
            ) as mock_hyperpod_cluster_node_handler:
                with patch(
                    'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler'
                ) as mock_hyperpod_stack_handler:
                    # Call the main function
                    main()

                    # Verify that parse_args was called
                    mock_parse_args.assert_called_once()

                    # Verify that the handlers were initialized with correct parameters
                    mock_hyperpod_cluster_node_handler.assert_called_once_with(
                        mock_server, True, False
                    )
                    mock_hyperpod_stack_handler.assert_called_once_with(mock_server, True)

                    # Verify that run was called
                    mock_server.run.assert_called_once()

    # Test with sensitive data access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            allow_write=False, allow_sensitive_data_access=True
        )

        # Mock create_server to return a mock server
        mock_server = MagicMock()
        with patch(
            'awslabs.sagemaker_hyperpod_mcp_server.server.create_server', return_value=mock_server
        ):
            # Mock the handler initialization to verify allow_sensitive_data_access is passed
            with patch(
                'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler'
            ) as mock_hyperpod_cluster_node_handler:
                with patch(
                    'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler'
                ) as mock_hyperpod_stack_handler:
                    # Call the main function
                    main()

                    # Verify that parse_args was called
                    mock_parse_args.assert_called_once()

                    # Verify that the handlers were initialized with correct parameters
                    mock_hyperpod_cluster_node_handler.assert_called_once_with(
                        mock_server, False, True
                    )
                    mock_hyperpod_stack_handler.assert_called_once_with(mock_server, False)

                    # Verify that run was called
                    mock_server.run.assert_called_once()

    # Test with both write access and sensitive data access enabled
    with patch.object(argparse.ArgumentParser, 'parse_args') as mock_parse_args:
        mock_parse_args.return_value = argparse.Namespace(
            allow_write=True, allow_sensitive_data_access=True
        )

        # Mock create_server to return a mock server
        mock_server = MagicMock()
        with patch(
            'awslabs.sagemaker_hyperpod_mcp_server.server.create_server', return_value=mock_server
        ):
            # Mock the handler initialization to verify both flags are passed
            with patch(
                'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodClusterNodeHandler'
            ) as mock_hyperpod_cluster_node_handler:
                with patch(
                    'awslabs.sagemaker_hyperpod_mcp_server.server.HyperPodStackHandler'
                ) as mock_hyperpod_stack_handler:
                    # Call the main function
                    main()

                    # Verify that parse_args was called
                    mock_parse_args.assert_called_once()

                    # Verify that the handlers were initialized with both flags
                    mock_hyperpod_cluster_node_handler.assert_called_once_with(
                        mock_server, True, True
                    )
                    mock_hyperpod_stack_handler.assert_called_once_with(mock_server, True)

                    # Verify that run was called
                    mock_server.run.assert_called_once()


@pytest.mark.asyncio
async def test_hyperpod_cluster_node_handler_initialization():
    """Test the initialization of the HyperPodClusterNodeHandler."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    HyperPodClusterNodeHandler(mock_mcp)

    # Verify that the tools were registered
    assert mock_mcp.tool.call_count == 3

    # Get all call args
    call_args_list = mock_mcp.tool.call_args_list

    # Get all tool names that were registered
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    # Verify that all tools are registered
    assert 'describe_hp_cluster' in tool_names
    assert 'update_hp_cluster' in tool_names

    assert 'manage_hyperpod_cluster_nodes' in tool_names


@pytest.mark.asyncio
async def test_hyperpod_stack_handler_initialization():
    """Test the initialization of the HyperPodStackHandler."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    HyperPodStackHandler(mock_mcp)

    # Verify that the tool was registered
    mock_mcp.tool.assert_called_once()
    call_args = mock_mcp.tool.call_args
    assert call_args[1]['name'] == 'manage_hyperpod_stacks'
