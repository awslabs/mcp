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
"""Tests for the MWAA MCP Server."""

import pytest
from awslabs.mwaa_mcp_server.airflow_tools import AirflowTools
from awslabs.mwaa_mcp_server.environment_tools import EnvironmentTools
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_server_initialization():
    from awslabs.mwaa_mcp_server.server import create_server

    server = create_server()

    assert server.name == 'awslabs.mwaa-mcp-server'
    assert server.instructions is not None and 'MWAA MCP Server' in server.instructions
    assert 'pydantic' in server.dependencies
    assert 'loguru' in server.dependencies
    assert 'boto3' in server.dependencies
    assert 'botocore' in server.dependencies


@pytest.mark.asyncio
async def test_environment_tools_registration():
    mock_mcp = MagicMock()
    EnvironmentTools(mock_mcp)

    assert mock_mcp.tool.call_count == 5

    call_args_list = mock_mcp.tool.call_args_list
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    assert 'list-environments' in tool_names
    assert 'get-environment' in tool_names
    assert 'create-environment' in tool_names
    assert 'update-environment' in tool_names
    assert 'delete-environment' in tool_names


@pytest.mark.asyncio
async def test_environment_tools_registration_with_write():
    mock_mcp = MagicMock()
    EnvironmentTools(mock_mcp, allow_write=True)

    assert mock_mcp.tool.call_count == 5

    call_args_list = mock_mcp.tool.call_args_list
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    assert 'list-environments' in tool_names
    assert 'get-environment' in tool_names
    assert 'create-environment' in tool_names
    assert 'update-environment' in tool_names
    assert 'delete-environment' in tool_names


@pytest.mark.asyncio
async def test_airflow_tools_registration():
    mock_mcp = MagicMock()
    AirflowTools(mock_mcp)

    assert mock_mcp.tool.call_count == 15

    call_args_list = mock_mcp.tool.call_args_list
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    assert 'list-dags' in tool_names
    assert 'get-dag' in tool_names
    assert 'get-dag-source' in tool_names
    assert 'list-dag-runs' in tool_names
    assert 'get-dag-run' in tool_names
    assert 'list-task-instances' in tool_names
    assert 'get-task-instance' in tool_names
    assert 'get-task-logs' in tool_names
    assert 'list-connections' in tool_names
    assert 'list-variables' in tool_names
    assert 'get-import-errors' in tool_names
    assert 'trigger-dag-run' in tool_names
    assert 'pause-dag' in tool_names
    assert 'unpause-dag' in tool_names
    assert 'clear-task-instances' in tool_names


@pytest.mark.asyncio
async def test_airflow_tools_registration_with_write():
    mock_mcp = MagicMock()
    AirflowTools(mock_mcp, allow_write=True)

    assert mock_mcp.tool.call_count == 15

    call_args_list = mock_mcp.tool.call_args_list
    tool_names = [call_args[1]['name'] for call_args in call_args_list]

    assert 'trigger-dag-run' in tool_names
    assert 'pause-dag' in tool_names
    assert 'unpause-dag' in tool_names
    assert 'clear-task-instances' in tool_names


@pytest.mark.asyncio
async def test_total_tool_count():
    mock_mcp = MagicMock()
    EnvironmentTools(mock_mcp)
    AirflowTools(mock_mcp)

    assert mock_mcp.tool.call_count == 20
