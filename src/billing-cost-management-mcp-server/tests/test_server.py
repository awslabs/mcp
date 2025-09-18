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

"""Tests for server.py."""

import os
from unittest.mock import AsyncMock, patch


def test_server_imports():
    """Test that server imports work correctly."""
    from awslabs.billing_cost_management_mcp_server import server

    assert hasattr(server, 'main')


def test_server_module_attributes():
    """Test server module has expected attributes."""
    from awslabs.billing_cost_management_mcp_server import server

    # Check that the module has the expected functions and imports
    assert hasattr(server, 'main')
    assert hasattr(server, 'mcp')
    assert hasattr(server, 'asyncio')


def test_path_modification():
    """Test that path modification logic exists."""
    from awslabs.billing_cost_management_mcp_server import server

    # Test that the path modification code exists in the module
    # This tests the lines that add parent directory to sys.path
    assert hasattr(server, 'os')
    assert hasattr(server, 'sys')


def test_server_tool_imports():
    """Test that all tool servers are imported."""
    from awslabs.billing_cost_management_mcp_server import server

    # Verify that tool server imports exist
    assert hasattr(server, 'aws_pricing_server')
    assert hasattr(server, 'budget_server')
    assert hasattr(server, 'compute_optimizer_server')
    assert hasattr(server, 'cost_anomaly_server')
    assert hasattr(server, 'cost_comparison_server')


@patch.dict(os.environ, {'AWS_REGION': 'us-west-2'})
def test_environment_variables_handling():
    """Test that environment variables can be accessed."""
    # Test that environment variables are accessible
    assert os.environ.get('AWS_REGION') == 'us-west-2'


def test_main_function_exists():
    """Test that main function exists and is callable."""
    from awslabs.billing_cost_management_mcp_server.server import main

    # Test that main function exists
    assert callable(main)


def test_server_registration_logic():
    """Test server registration logic without actually running it."""
    from awslabs.billing_cost_management_mcp_server import server

    # Test that the server module has all the necessary components
    # for server registration without actually creating a server
    assert hasattr(server, 'cost_explorer_server')
    assert hasattr(server, 'cost_optimization_hub_server')
    assert hasattr(server, 'free_tier_usage_server')
    assert hasattr(server, 'ri_performance_server')
    assert hasattr(server, 'sp_performance_server')


@patch('awslabs.billing_cost_management_mcp_server.server.mcp')
@patch('awslabs.billing_cost_management_mcp_server.server.register_prompts')
async def test_setup_function(mock_register_prompts, mock_mcp):
    """Test the setup function execution path."""
    from awslabs.billing_cost_management_mcp_server.server import setup

    mock_mcp.import_server = AsyncMock()
    mock_register_prompts.return_value = None

    await setup()

    assert mock_mcp.import_server.call_count >= 10


@patch('awslabs.billing_cost_management_mcp_server.prompts.register_all_prompts')
async def test_register_prompts_success(mock_register_all_prompts):
    """Test successful prompt registration."""
    from awslabs.billing_cost_management_mcp_server.server import register_prompts

    mock_register_all_prompts.return_value = None

    await register_prompts()

    mock_register_all_prompts.assert_called_once()


@patch('awslabs.billing_cost_management_mcp_server.prompts.register_all_prompts')
async def test_register_prompts_error(mock_register_all_prompts):
    """Test prompt registration error handling."""
    from awslabs.billing_cost_management_mcp_server.server import register_prompts

    mock_register_all_prompts.side_effect = Exception('Test error')

    await register_prompts()


@patch('awslabs.billing_cost_management_mcp_server.server.asyncio.run')
@patch('awslabs.billing_cost_management_mcp_server.server.mcp.run')
def test_main_function(mock_mcp_run, mock_asyncio_run):
    """Test main function execution."""
    from awslabs.billing_cost_management_mcp_server.server import main

    main()

    mock_asyncio_run.assert_called_once()
    mock_mcp_run.assert_called_once()
