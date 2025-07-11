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

"""Tests for the main function in server.py."""

from awslabs.aws_msk_mcp_server.server import main
from unittest.mock import MagicMock, patch


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.aws_msk_mcp_server.server.run')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_calls_run(self, mock_parse_args, mock_run):
        """Test that main calls the run function."""
        # Arrange
        mock_args = MagicMock()
        mock_args.allow_writes = False
        mock_parse_args.return_value = mock_args

        # Act
        main()

        # Assert
        mock_run.assert_called_once()
