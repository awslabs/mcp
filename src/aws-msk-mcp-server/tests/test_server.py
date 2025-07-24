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

"""Unit tests for the server.py module."""

import pytest
import signal
import unittest
from awslabs.aws_msk_mcp_server.server import (
    main,
    run_server,
    signal_handler,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestServer:
    """Tests for the server.py module."""

    @pytest.mark.asyncio
    async def test_signal_handler_behavior(self):
        """Test the behavior of the signal_handler function.

        This test mocks the open_signal_receiver and os._exit functions to verify
        that the signal_handler function behaves as expected when signals are received.
        """
        # Create a mock CancelScope
        mock_scope = MagicMock()

        # Create a mock signal receiver that yields a signal when iterated
        class MockSignalReceiver:
            def __init__(self):
                self.entered = False
                self.signals_yielded = 0

            def __enter__(self):
                self.entered = True
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.signals_yielded == 0:
                    self.signals_yielded += 1
                    return signal.SIGINT
                raise StopAsyncIteration()

        mock_signals = MockSignalReceiver()

        # Mock the open_signal_receiver to return our custom mock
        mock_open_signal_receiver = MagicMock(return_value=mock_signals)

        # Mock the print function and os._exit
        with (
            patch(
                'awslabs.aws_msk_mcp_server.server.open_signal_receiver', mock_open_signal_receiver
            ),
            patch('awslabs.aws_msk_mcp_server.server.print') as mock_print,
            patch('awslabs.aws_msk_mcp_server.server.os._exit') as mock_exit,
        ):
            # Call the signal_handler function
            await signal_handler(mock_scope)

            # Verify that the shutdown message was printed
            mock_print.assert_called_once_with('Shutting down MCP server...')

            # Verify that os._exit was called with the expected argument
            mock_exit.assert_called_once_with(0)

    async def test_run_server_read_only_mode(self):
        """Test the run_server function in read-only mode."""
        # Mock the FastMCP class
        mock_mcp = MagicMock()
        mock_mcp.run_stdio_async = AsyncMock()

        # Mock the create_task_group context manager
        mock_task_group = MagicMock()
        mock_task_group.__aenter__ = AsyncMock(return_value=mock_task_group)
        mock_task_group.__aexit__ = AsyncMock()

        # Set read_only to True
        with (
            patch('awslabs.aws_msk_mcp_server.server.FastMCP', return_value=mock_mcp),
            patch(
                'awslabs.aws_msk_mcp_server.server.create_task_group', return_value=mock_task_group
            ),
            patch('awslabs.aws_msk_mcp_server.server.read_only', True),
            patch(
                'awslabs.aws_msk_mcp_server.server.read_cluster.register_module'
            ) as mock_read_cluster,
            patch(
                'awslabs.aws_msk_mcp_server.server.read_global.register_module'
            ) as mock_read_global,
            patch('awslabs.aws_msk_mcp_server.server.read_vpc.register_module') as mock_read_vpc,
            patch(
                'awslabs.aws_msk_mcp_server.server.read_config.register_module'
            ) as mock_read_config,
            patch(
                'awslabs.aws_msk_mcp_server.server.logs_and_telemetry.register_module'
            ) as mock_logs_and_telemetry,
            patch(
                'awslabs.aws_msk_mcp_server.server.mutate_cluster.register_module'
            ) as mock_mutate_cluster,
            patch(
                'awslabs.aws_msk_mcp_server.server.mutate_config.register_module'
            ) as mock_mutate_config,
            patch(
                'awslabs.aws_msk_mcp_server.server.mutate_vpc.register_module'
            ) as mock_mutate_vpc,
            patch(
                'awslabs.aws_msk_mcp_server.server.replicator.register_module'
            ) as mock_replicator,
            patch(
                'awslabs.aws_msk_mcp_server.server.register_resources', new_callable=AsyncMock
            ) as mock_register_resources,
            patch('awslabs.aws_msk_mcp_server.server.logger') as mock_logger,
        ):
            # Call the function under test
            await run_server()

            # Verify that the read modules were registered
            mock_read_cluster.assert_called_once_with(mock_mcp)
            mock_read_global.assert_called_once_with(mock_mcp)
            mock_read_vpc.assert_called_once_with(mock_mcp)
            mock_read_config.assert_called_once_with(mock_mcp)
            mock_logs_and_telemetry.assert_called_once_with(mock_mcp)

            # Verify that the mutate modules were not registered
            mock_mutate_cluster.assert_not_called()
            mock_mutate_config.assert_not_called()
            mock_mutate_vpc.assert_not_called()
            mock_replicator.assert_not_called()

            # Verify that the resources were registered
            mock_register_resources.assert_called_once_with(mock_mcp)

            # Verify that the task group was started
            mock_task_group.start_soon.assert_called_once()

            # Verify that the MCP server was run
            mock_mcp.run_stdio_async.assert_called_once()

            # Verify that the read-only mode message was logged
            mock_logger.info.assert_any_call(
                'Server running in read-only mode. Write operations are disabled.'
            )

    async def test_run_server_write_mode(self):
        """Test the run_server function in write mode."""
        # Mock the FastMCP class
        mock_mcp = MagicMock()
        mock_mcp.run_stdio_async = AsyncMock()

        # Mock the create_task_group context manager
        mock_task_group = MagicMock()
        mock_task_group.__aenter__ = AsyncMock(return_value=mock_task_group)
        mock_task_group.__aexit__ = AsyncMock()

        # Set read_only to False
        with (
            patch('awslabs.aws_msk_mcp_server.server.FastMCP', return_value=mock_mcp),
            patch(
                'awslabs.aws_msk_mcp_server.server.create_task_group', return_value=mock_task_group
            ),
            patch('awslabs.aws_msk_mcp_server.server.read_only', False),
            patch(
                'awslabs.aws_msk_mcp_server.server.read_cluster.register_module'
            ) as mock_read_cluster,
            patch(
                'awslabs.aws_msk_mcp_server.server.read_global.register_module'
            ) as mock_read_global,
            patch('awslabs.aws_msk_mcp_server.server.read_vpc.register_module') as mock_read_vpc,
            patch(
                'awslabs.aws_msk_mcp_server.server.read_config.register_module'
            ) as mock_read_config,
            patch(
                'awslabs.aws_msk_mcp_server.server.logs_and_telemetry.register_module'
            ) as mock_logs_and_telemetry,
            patch(
                'awslabs.aws_msk_mcp_server.server.mutate_cluster.register_module'
            ) as mock_mutate_cluster,
            patch(
                'awslabs.aws_msk_mcp_server.server.mutate_config.register_module'
            ) as mock_mutate_config,
            patch(
                'awslabs.aws_msk_mcp_server.server.mutate_vpc.register_module'
            ) as mock_mutate_vpc,
            patch(
                'awslabs.aws_msk_mcp_server.server.replicator.register_module'
            ) as mock_replicator,
            patch(
                'awslabs.aws_msk_mcp_server.server.register_resources', new_callable=AsyncMock
            ) as mock_register_resources,
            patch('awslabs.aws_msk_mcp_server.server.logger') as mock_logger,
        ):
            # Call the function under test
            await run_server()

            # Verify that the read modules were registered
            mock_read_cluster.assert_called_once_with(mock_mcp)
            mock_read_global.assert_called_once_with(mock_mcp)
            mock_read_vpc.assert_called_once_with(mock_mcp)
            mock_read_config.assert_called_once_with(mock_mcp)
            mock_logs_and_telemetry.assert_called_once_with(mock_mcp)

            # Verify that the mutate modules were registered
            mock_mutate_cluster.assert_called_once_with(mock_mcp)
            mock_mutate_config.assert_called_once_with(mock_mcp)
            mock_mutate_vpc.assert_called_once_with(mock_mcp)
            mock_replicator.assert_called_once_with(mock_mcp)

            # Verify that the resources were registered
            mock_register_resources.assert_called_once_with(mock_mcp)

            # Verify that the task group was started
            mock_task_group.start_soon.assert_called_once()

            # Verify that the MCP server was run
            mock_mcp.run_stdio_async.assert_called_once()

            # Verify that the write mode message was logged
            mock_logger.info.assert_any_call('Write operations are enabled')

    @pytest.mark.asyncio
    def test_main_read_only_mode(self):
        """Test the main function in read-only mode."""
        # Mock the argparse.ArgumentParser
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.allow_writes = False
        mock_parser.parse_args.return_value = mock_args

        # Mock the run function
        with (
            patch(
                'awslabs.aws_msk_mcp_server.server.argparse.ArgumentParser',
                return_value=mock_parser,
            ),
            patch('awslabs.aws_msk_mcp_server.server.run') as mock_run,
            patch('awslabs.aws_msk_mcp_server.server.logger') as mock_logger,
            patch('awslabs.aws_msk_mcp_server.server.read_only', True, create=True),
        ):
            # Call the function under test
            main()

            # Verify that the --allow-writes argument was added
            mock_parser.add_argument.assert_called_once_with(
                '--allow-writes',
                action='store_true',
                help='Allow use of tools that may perform write operations',
            )

            # Verify that the arguments were parsed
            mock_parser.parse_args.assert_called_once()

            # Verify that the run function was called with run_server
            mock_run.assert_called_once()

            # Verify that the initialization message was logged
            mock_logger.info.assert_called_once_with(
                'AWS MSK MCP server initialized with ALLOW-WRITES:{}', False
            )

    @pytest.mark.asyncio
    def test_main_write_mode(self):
        """Test the main function in write mode."""
        # Mock the argparse.ArgumentParser
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.allow_writes = True
        mock_parser.parse_args.return_value = mock_args

        # Mock the run function
        with (
            patch(
                'awslabs.aws_msk_mcp_server.server.argparse.ArgumentParser',
                return_value=mock_parser,
            ),
            patch('awslabs.aws_msk_mcp_server.server.run') as mock_run,
            patch('awslabs.aws_msk_mcp_server.server.logger') as mock_logger,
            patch('awslabs.aws_msk_mcp_server.server.read_only', False, create=True),
        ):
            # Call the function under test
            main()

            # Verify that the --allow-writes argument was added
            mock_parser.add_argument.assert_called_once_with(
                '--allow-writes',
                action='store_true',
                help='Allow use of tools that may perform write operations',
            )

            # Verify that the arguments were parsed
            mock_parser.parse_args.assert_called_once()

            # Verify that the run function was called with run_server
            mock_run.assert_called_once()

            # Verify that the initialization message was logged
            mock_logger.info.assert_called_once_with(
                'AWS MSK MCP server initialized with ALLOW-WRITES:{}', True
            )


if __name__ == '__main__':
    unittest.main()
