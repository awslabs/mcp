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

"""Tests for AWS IoT SiteWise MCP Server."""

import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.server import main, run_server
from unittest.mock import AsyncMock, Mock, patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestServer:
    """Test cases for MCP server functionality."""

    @patch.dict(os.environ, {'SITEWISE_MCP_ALLOW_WRITES': 'True'})
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.create_task_group')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.FastMCP')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.__version__', '1.0.0')
    @pytest.mark.asyncio
    async def test_run_server_setup(self, mock_fastmcp, mock_task_group):
        """Test server setup with all tools and prompts."""
        # Version is mocked by the patch decorator

        # Mock FastMCP instance
        mock_mcp_instance = Mock()
        mock_mcp_instance.add_tool = Mock()
        mock_mcp_instance.add_prompt = Mock()
        mock_mcp_instance.run_stdio_async = AsyncMock()
        mock_mcp_instance._mcp_server = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Mock task group
        mock_tg = AsyncMock()
        mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
        mock_tg.__aexit__ = AsyncMock(return_value=None)
        mock_tg.start_soon = Mock()
        mock_tg.cancel_scope = Mock()
        mock_task_group.return_value = mock_tg

        # Call run_server
        await run_server()

        # Verify FastMCP was created with correct parameters
        # In write mode, it should have the write-enabled instructions
        call_args = mock_fastmcp.call_args[1]  # Get keyword arguments
        assert call_args['name'] == 'sitewise'
        assert 'WRITE ENABLED' in call_args['instructions']

        # Verify version was set
        assert mock_mcp_instance._mcp_server.version == '1.0.0'

        # Verify tools were added
        assert mock_mcp_instance.add_tool.call_count > 0

        # Verify prompts were added
        assert mock_mcp_instance.add_prompt.call_count > 0

        # Verify signal handler was started
        mock_tg.start_soon.assert_called_once()

        # Verify server was run
        mock_mcp_instance.run_stdio_async.assert_called_once()

    @patch.dict(os.environ, {'SITEWISE_MCP_ALLOW_WRITES': 'True'})
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.create_task_group')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.FastMCP')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.__version__', '1.0.0')
    @pytest.mark.asyncio
    async def test_run_server_tool_categories(self, mock_fastmcp, mock_task_group):
        """Test that all tool categories are properly included."""
        mock_mcp_instance = Mock()
        mock_mcp_instance.add_tool = Mock()
        mock_mcp_instance.add_prompt = Mock()
        mock_mcp_instance.run_stdio_async = AsyncMock()
        mock_mcp_instance._mcp_server = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        mock_tg = AsyncMock()
        mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
        mock_tg.__aexit__ = AsyncMock(return_value=None)
        mock_tg.start_soon = Mock()
        mock_tg.cancel_scope = Mock()
        mock_task_group.return_value = mock_tg

        await run_server()

        # Verify specific tool names are included by checking the call arguments
        tool_calls = mock_mcp_instance.add_tool.call_args_list
        tool_names = [tool_call[0][1] for tool_call in tool_calls]  # Second argument is tool name

        # Check for representative tools from each category
        assert 'create_asset' in tool_names
        assert 'create_asset_model' in tool_names
        assert 'batch_put_asset_property_value' in tool_names
        assert 'create_gateway' in tool_names
        assert 'put_logging_options' in tool_names
        assert 'create_metadata_transfer_job' in tool_names

    @patch.dict(os.environ, {'SITEWISE_MCP_ALLOW_WRITES': 'True'})
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.create_task_group')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.FastMCP')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.__version__', '1.0.0')
    @pytest.mark.asyncio
    async def test_run_server_prompts(self, mock_fastmcp, mock_task_group):
        """Test that prompts are properly added."""
        mock_mcp_instance = Mock()
        mock_mcp_instance.add_tool = Mock()
        mock_mcp_instance.add_prompt = Mock()
        mock_mcp_instance.run_stdio_async = AsyncMock()
        mock_mcp_instance._mcp_server = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        mock_tg = AsyncMock()
        mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
        mock_tg.__aexit__ = AsyncMock(return_value=None)
        mock_tg.start_soon = Mock()
        mock_tg.cancel_scope = Mock()
        mock_task_group.return_value = mock_tg

        await run_server()

        # Verify prompts were added
        assert mock_mcp_instance.add_prompt.call_count > 0

        # Verify the prompts are from the expected modules
        prompt_calls = mock_mcp_instance.add_prompt.call_args_list
        # Each call should be a Mock call with one argument (the prompt)
        assert len(prompt_calls) > 0

    @patch('awslabs.aws_iot_sitewise_mcp_server.server.run')
    def test_main_function(self, mock_run):
        """Test main function calls run with run_server."""
        main()
        mock_run.assert_called_once_with(run_server)

    @patch('awslabs.aws_iot_sitewise_mcp_server.server.create_task_group')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.FastMCP')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.__version__', '1.0.0')
    @pytest.mark.asyncio
    async def test_run_server_version_setting(self, mock_fastmcp, mock_task_group):
        """Test that server version is properly set."""
        mock_mcp_instance = Mock()
        mock_mcp_instance.add_tool = Mock()
        mock_mcp_instance.add_prompt = Mock()
        mock_mcp_instance.run_stdio_async = AsyncMock()
        mock_mcp_instance._mcp_server = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        mock_tg = AsyncMock()
        mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
        mock_tg.__aexit__ = AsyncMock(return_value=None)
        mock_tg.start_soon = Mock()
        mock_tg.cancel_scope = Mock()
        mock_task_group.return_value = mock_tg

        await run_server()

        # Verify version was set correctly (mocked as '1.0.0')
        assert mock_mcp_instance._mcp_server.version == '1.0.0'

    @patch.dict(os.environ, {'SITEWISE_MCP_ALLOW_WRITES': 'True'})
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.create_task_group')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.FastMCP')
    @patch('awslabs.aws_iot_sitewise_mcp_server.server.__version__', '1.0.0')
    @pytest.mark.asyncio
    async def test_run_server_error_handling(self, mock_fastmcp, mock_task_group):
        """Test server handles errors gracefully."""
        mock_mcp_instance = Mock()
        mock_mcp_instance.add_tool = Mock()
        mock_mcp_instance.add_prompt = Mock()
        # Simulate an error in run_stdio_async
        mock_mcp_instance.run_stdio_async = AsyncMock(side_effect=Exception('Test error'))
        mock_mcp_instance._mcp_server = Mock()
        mock_fastmcp.return_value = mock_mcp_instance

        mock_tg = AsyncMock()
        mock_tg.__aenter__ = AsyncMock(return_value=mock_tg)
        mock_tg.__aexit__ = AsyncMock(return_value=None)
        mock_tg.start_soon = Mock()
        mock_tg.cancel_scope = Mock()
        mock_task_group.return_value = mock_tg

        # Should raise the exception
        with pytest.raises(Exception, match='Test error'):
            await run_server()

        # Verify setup still happened before the error
        mock_fastmcp.assert_called_once()
        assert mock_mcp_instance.add_tool.call_count > 0
        assert mock_mcp_instance.add_prompt.call_count > 0


if __name__ == '__main__':
    pytest.main([__file__])
