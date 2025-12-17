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

"""Tests for main module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestMain:
    """Tests for main entry point."""

    @pytest.mark.asyncio
    @patch('awslabs.healthimaging_mcp_server.main.create_healthimaging_server')
    @patch('awslabs.healthimaging_mcp_server.main.stdio_server')
    async def test_main_success(self, mock_stdio, mock_create_server):
        """Test main function runs successfully."""
        from awslabs.healthimaging_mcp_server.main import main

        mock_server = MagicMock()
        mock_server.run = AsyncMock()
        mock_server.create_initialization_options.return_value = {}
        mock_create_server.return_value = mock_server

        mock_read_stream = MagicMock()
        mock_write_stream = MagicMock()

        async def mock_context_manager():
            return (mock_read_stream, mock_write_stream)

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=(mock_read_stream, mock_write_stream))
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_stdio.return_value = mock_cm

        await main()

        mock_create_server.assert_called_once()
        mock_server.run.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.healthimaging_mcp_server.main.create_healthimaging_server')
    @patch('awslabs.healthimaging_mcp_server.main.stdio_server')
    async def test_main_error_handling(self, mock_stdio, mock_create_server):
        """Test main function handles errors."""
        from awslabs.healthimaging_mcp_server.main import main

        mock_create_server.side_effect = Exception('Test error')

        with pytest.raises(Exception, match='Test error'):
            await main()

    @patch('awslabs.healthimaging_mcp_server.main.asyncio.run')
    def test_sync_main(self, mock_run):
        """Test sync_main wrapper."""
        from awslabs.healthimaging_mcp_server.main import sync_main

        sync_main()
        mock_run.assert_called_once()
