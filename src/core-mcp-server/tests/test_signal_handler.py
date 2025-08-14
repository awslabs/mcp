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
"""Tests for the signal handler in server.py."""

import signal
from unittest.mock import patch

from awslabs.core_mcp_server.server import signal_handler


class TestSignalHandler:
    """Tests for the signal_handler function."""

    def test_signal_handler_sigterm(self):
        """Test that signal handler logs and exits properly with SIGTERM."""
        # Mock the logger and sys.exit
        with patch('awslabs.core_mcp_server.server.logger') as mock_logger, \
             patch('sys.exit') as mock_exit:
            
            # Test the signal handler with SIGTERM
            signal_handler(signal.SIGTERM, None)
            
            # Verify logger was called with correct message
            mock_logger.info.assert_called_once_with("Received signal 15, shutting down server...")
            
            # Verify sys.exit was called with 0
            mock_exit.assert_called_once_with(0)

    def test_signal_handler_sigint(self):
        """Test signal handler with SIGINT."""
        with patch('awslabs.core_mcp_server.server.logger') as mock_logger, \
             patch('sys.exit') as mock_exit:
            
            # Test with SIGINT
            signal_handler(signal.SIGINT, None)
            
            # Verify logger was called with correct message
            mock_logger.info.assert_called_once_with("Received signal 2, shutting down server...")
            
            # Verify sys.exit was called with 0
            mock_exit.assert_called_once_with(0)
