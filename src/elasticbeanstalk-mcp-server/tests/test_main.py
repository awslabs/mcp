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

"""Tests for the main entry point of the elasticbeanstalk MCP Server."""

from unittest.mock import MagicMock, patch


class TestMain:
    """Test class for the main entry point of the server."""

    def test_main_initializes_context(self):
        """Test that the main function initializes the context correctly."""
        # Arrange
        mock_mcp = MagicMock()
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.readonly = True
        mock_parser.parse_args.return_value = mock_args
        mock_context = MagicMock()

        # Act
        with (
            patch('awslabs.elasticbeanstalk_mcp_server.server.mcp', mock_mcp),
            patch(
                'awslabs.elasticbeanstalk_mcp_server.server.argparse.ArgumentParser',
                return_value=mock_parser,
            ),
            patch('awslabs.elasticbeanstalk_mcp_server.server.Context', mock_context),
        ):
            # Import main function here to avoid module-level errors
            from awslabs.elasticbeanstalk_mcp_server.server import main

            main()

            # Assert
            mock_parser.parse_args.assert_called_once()
            mock_context.initialize.assert_called_once_with(readonly_mode=True)
            mock_mcp.run.assert_called_once()

    def test_main_with_default_args(self):
        """Test that the main function works with default arguments."""
        # Arrange
        mock_mcp = MagicMock()
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.readonly = False
        mock_parser.parse_args.return_value = mock_args
        mock_context = MagicMock()

        # Act
        with (
            patch('awslabs.elasticbeanstalk_mcp_server.server.mcp', mock_mcp),
            patch(
                'awslabs.elasticbeanstalk_mcp_server.server.argparse.ArgumentParser',
                return_value=mock_parser,
            ),
            patch('awslabs.elasticbeanstalk_mcp_server.server.Context', mock_context),
        ):
            # Import main function here to avoid module-level errors
            from awslabs.elasticbeanstalk_mcp_server.server import main

            main()

            # Assert
            mock_parser.parse_args.assert_called_once()
            mock_context.initialize.assert_called_once_with(readonly_mode=False)
            mock_mcp.run.assert_called_once()
